#!/usr/bin/env python3
"""Redacta análisis propios de Branka combinando noticias RSS verificables.

Necesita OPENAI_API_KEY en GitHub Actions. Sin clave, o sin dos fuentes independientes,
no se publica nada. No se presenta la síntesis automática como periodismo investigado.
"""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"
SOURCES = [
    ("EU-Startups", "https://www.eu-startups.com/feed/", "eu-startups.com"),
    ("TechCrunch", "https://techcrunch.com/category/startups/feed/", "techcrunch.com"),
    ("TechCrunch", "https://techcrunch.com/category/venture/feed/", "techcrunch.com"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/", "techcrunch.com"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "technologyreview.com"),
    ("Sifted", "https://sifted.eu/feed", "sifted.eu"),
]
# Los identificadores tienen que coincidir con los de tools-data en index.html.
TOPICS = [
    ("Financiación", "21_estrategia_de_ronda_de_inversion", ("funding", "raises", "raised", "venture capital", "investment", "investor", "seed", "series a", "series b", "financing", "fundraising", "round", "grant")),
    ("Inteligencia artificial", "33_canvas_de_caso_de_uso_de_ia", ("artificial intelligence", "ai agents", "ai agent", "generative ai", "machine learning", "llm", "openai", "anthropic", "gemini", "ai startup")),
    ("Impacto social", "30_teoria_del_cambio", ("social enterprise", "social impact", "impact investing", "social innovation", "climate tech", "sustainability", "circular economy", "clean energy")),
    ("Emprendimiento", "09_business_model_canvas", ("startup", "founder", "entrepreneur", "business model", "scaleup", "marketplace", "early-stage")),
    ("Innovación", "03_tecnologia_disruptiva", ("innovation", "technology", "robotics", "software", "research", "platform")),
]
MAX_HOURS = 120
MAX_ARTICLES = 2
MODEL = os.getenv("BRANKA_NEWS_MODEL", "gpt-4.1-mini")

def compact(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())

def date_from(value):
    if not value:
        return None
    try:
        return email.utils.parsedate_to_datetime(value).astimezone(dt.timezone.utc)
    except (ValueError, TypeError, IndexError):
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        except (ValueError, TypeError):
            return None

def get_feed(name, url, domain):
    request = urllib.request.Request(url, headers={
        "User-Agent": "BrankaInsights/1.0 (+https://branka.es)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        document = response.read(2_000_000)
    root = ET.fromstring(document)
    atom = "{http://www.w3.org/2005/Atom}"
    nodes = root.findall(".//item")
    rss = bool(nodes)
    if not rss:
        nodes = root.findall(f".//{atom}entry")
    result = []
    for node in nodes:
        if rss:
            title = compact(node.findtext("title"))
            description = compact(node.findtext("description"))
            url = (node.findtext("link") or "").strip()
            published = date_from(node.findtext("pubDate"))
        else:
            title = compact(node.findtext(f"{atom}title"))
            description = compact(node.findtext(f"{atom}summary") or node.findtext(f"{atom}content"))
            links = node.findall(f"{atom}link")
            url = next((l.attrib.get("href", "") for l in links if l.attrib.get("rel", "alternate") == "alternate"), "")
            published = date_from(node.findtext(f"{atom}published") or node.findtext(f"{atom}updated"))
        host = (urllib.parse.urlparse(url).hostname or "").lower().removeprefix("www.")
        if host != domain or not url.startswith("https://") or not title or not description or not published:
            continue
        result.append({"title": title[:180], "summary": description[:520],
                       "url": url.split("#")[0], "date": published, "source": name, "domain": host})
    return result

def topic_for(item):
    body = " " + (item["title"] + " " + item["summary"]).lower() + " "
    for label, tool, words in TOPICS:
        if any(term in body for term in words):
            return label, tool
    return None

def groups_for(items, previous_sources):
    by_topic = {}
    now = dt.datetime.now(dt.timezone.utc)
    for item in items:
        hours = (now - item["date"]).total_seconds() / 3600
        if not -2 <= hours <= MAX_HOURS or item["url"] in previous_sources:
            continue
        topic = topic_for(item)
        if topic:
            by_topic.setdefault(topic, []).append(item)
    result = []
    for topic, candidates in by_topic.items():
        candidates.sort(key=lambda x: x["date"], reverse=True)
        selected = []
        domains = set()
        for article in candidates:
            if article["domain"] not in domains:
                selected.append(article)
                domains.add(article["domain"])
            if len(selected) == 3:
                break
        if len(selected) >= 2:
            result.append((topic, selected))
    result.sort(key=lambda g: max(i["date"] for i in g[1]), reverse=True)
    return result[:MAX_ARTICLES]

def request_article(topic, sources):
    # La API recibe extractos, no acceso a textos íntegros. No debe inventar datos.
    evidence = [{"id":i+1, "medio":s["source"], "titular":s["title"],
                 "extracto":s["summary"], "fecha":s["date"].date().isoformat()}
                for i,s in enumerate(sources)]
    instructions = """Eres un editor especializado en emprendimiento de Branka.
Redacta en español de España un ARTÍCULO ORIGINAL de análisis útil, NO un copiado ni
un agregado de titulares. Combina 2-3 noticias distintas únicamente como señales
de una tendencia del sector. No afirmes que tratan del mismo hecho si no es cierto.
Los únicos hechos comprobados a tu disposición son los títulos, fechas y fragmentos RSS.
No añadas números, valoraciones, citas, cronologías, declaraciones, legislación o
nombres nuevos que no aparezcan en estos datos. No presentes interpretaciones como hechos.
Si no hay sustancia para escribir con rigor, responde publish=false.
Escribe con voz propia, sin lenguaje publicitario ni sensacionalismo, y sin repetir
literalmente frases extensas de los extractos.
Devuelve SOLO un objeto JSON:
{"publish":true|false,"title":"titular propio, claro y específico, sin clickbait",
"dek":"entradilla breve","paragraphs":["4-6 párrafos, cada uno de 35-80 palabras"],
"insight":"conclusión propia explícita, como recomendación o hipótesis",
"action":"una pregunta o acción concreta para un emprendedor"}
Cubre qué está cambiando, qué tienen en común las señales, qué matices hay,
qué oportunidad/riesgo ve Branka y cómo aplicarlo. Evita conclusiones infundadas.
No incluyas markdown, HTML, enlaces ni enumeración en los párrafos.
"""
    body = {"model": MODEL, "temperature": 0.25,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": instructions},
                         {"role": "user", "content": json.dumps({"tema":topic, "fuentes":evidence},ensure_ascii=False)}]}
    payload = json.dumps(body).encode()
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=payload,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=75) as response:
        raw = json.load(response)
    result = json.loads(raw["choices"][0]["message"]["content"])
    if not result.get("publish"):
        return None
    pars = result.get("paragraphs")
    if not isinstance(pars, list) or not 4 <= len(pars) <= 6:
        return None
    if not all(isinstance(p,str) and 80 <= len(p) <= 700 and "<" not in p for p in pars):
        return None
    for key in ("title","dek","insight","action"):
        if not isinstance(result.get(key),str) or not result[key].strip():
            return None
    if len(result["title"]) > 150 or len(result["dek"]) > 300:
        return None
    return result

def article_path(title, sources):
    normalized = unicodedata.normalize("NFKD", title.lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    short = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:66] or "noticia"
    link_key = "|".join(src["url"] for src in sources)
    digest = hashlib.sha256(link_key.encode()).hexdigest()[:8]
    return "noticias/" + short + "-" + digest + ".html"

def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY no está configurada; no se generan ni publican artículos.")
        return 0
    raw = PAGE.read_text(encoding="utf-8")
    match = re.search(r'(<script id="news-data" type="application/json">)(.*?)(</script>)', raw, re.S)
    if not match:
        raise RuntimeError("Falta news-data en index.html")
    feed = json.loads(match.group(2))
    previous = set(feed.get("used_source_urls", []))
    previous_titles = {i.get("title","").lower() for i in feed.get("items", [])}
    items = []
    for name,url,domain in SOURCES:
        try:
            result = get_feed(name,url,domain)
            print(f"RSS {name}: {len(result)} entradas")
            items.extend(result)
        except Exception as exc:
            print(f"RSS no accesible: {name} ({str(exc)[:160]})", file=sys.stderr)
    fresh = list({i["url"]:i for i in items}.values())
    selected = groups_for(fresh, previous)
    created = []
    for (topic, tool), sources in selected:
        try:
            article = request_article(topic, sources)
        except Exception as exc:
            print(f"No se pudo redactar {topic}: {str(exc)[:180]}",file=sys.stderr)
            continue
        if not article or article["title"].lower() in previous_titles:
            continue
        now = dt.datetime.now(dt.timezone.utc)
        source_links = [[s["source"],s["url"]] for s in sources]
        paragraphs = article["paragraphs"]
        created.append({
            "url": "/" + article_path(article["title"].strip(), sources),
            "tag":topic, "title":article["title"].strip(), "body":article["dek"].strip(),
            "lesson":article["insight"].strip(), "action":article["action"].strip(),
            "tool":tool,"sources":source_links, "paragraphs":paragraphs,
            "published":now.isoformat(),"generated_with_ai":True,
            "source_facts": [{"title":s["title"],"date":s["date"].date().isoformat(),"url":s["url"]} for s in sources],
        })
    if not created:
        print("No hay suficiente evidencia para publicar artículos nuevos. Se mantienen los existentes.")
        return 0
    new_sources = {url for item in created for _,url in item["sources"]}
    used = list(dict.fromkeys(list(previous) + list(new_sources)))[-500:]
    # Archivo acumulativo para que "Ver más" permita recuperar artículos antiguos.
    archive_path = ROOT / "contenido" / "noticias.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    previous_archive = []
    if archive_path.exists():
        try:
            previous_archive = json.loads(archive_path.read_text(encoding="utf-8")).get("items", [])
        except (OSError, ValueError):
            pass
    seen = set()
    accumulated = []
    for item in created + feed.get("items", []) + previous_archive:
        identifier = item.get("url") or item.get("title")
        if identifier and identifier not in seen:
            accumulated.append(item)
            seen.add(identifier)
    archive_path.write_text(json.dumps({"items": accumulated[:1500]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Lo reciente primero, pero conservar las últimas piezas para que la sección no quede vacía.
    updated = {**feed,
      "week":"Branka Insights · actualizado el "+dt.datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y"),
      "items":created + feed.get("items", [])[:6],
      "auto":True, "used_source_urls":used}
    encoded = json.dumps(updated,ensure_ascii=False,separators=(",",":")).replace("<", "\\u003c")
    PAGE.write_text(raw[:match.start(2)] + encoded + raw[match.end(2):],encoding="utf-8")
    print(f"Redactados {len(created)} artículos originales con {len(new_sources)} fuentes contrastables.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
