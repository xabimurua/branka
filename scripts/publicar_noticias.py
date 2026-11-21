#!/usr/bin/env python3
"""Actualiza la sección Noticias de Branka con titulares de fuentes RSS verificables.

No genera afirmaciones sobre noticias mediante IA; enlaza la fuente primaria.
Solo sustituye noticias cuando encuentra artículos recientes y aptos.
"""
import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"
SOURCES = [
    ("EU-Startups", "https://www.eu-startups.com/feed/", "www.eu-startups.com"),
    ("TechCrunch", "https://techcrunch.com/category/startups/feed/", "techcrunch.com"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/", "techcrunch.com"),
    ("TechCrunch", "https://techcrunch.com/category/venture/feed/", "techcrunch.com"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "www.technologyreview.com"),
]
RULES = [
    ("Impacto social", "30_teoria_del_cambio", ("social enterprise", "social impact", "social innovation", "impact investing", "circular economy", "climate tech", "sustainability", "social startup"), "¿Qué cambio social se propone y cómo se mediría? Define indicadores y comprueba resultados."),
    ("Financiación", "21_estrategia_de_ronda_de_inversion", ("funding", "raises", "raised", "investment", "seed round", "series a", "series b", "venture capital", "investor", "acquisition", "grant", "financing", "fintech"), "Antes de captar fondos, relaciona el dinero solicitado con hitos medibles y necesidades reales de caja."),
    ("Inteligencia artificial", "33_canvas_de_caso_de_uso_de_ia", ("artificial intelligence", "ai agent", "agents", " generative ai", " ai ", "llm", "openai", "anthropic", "machine learning"), "Identifica un caso de uso concreto y prueba su utilidad, coste y riesgos antes de escalar."),
    ("Emprendimiento", "09_business_model_canvas", ("startup", "founder", "entrepreneur", "launches", "scaleup", "business model", "product", "marketplace"), "Analiza quién es el cliente, cómo se crea valor y qué modelo de ingresos sostiene el proyecto."),
    ("Innovación", "03_tecnologia_disruptiva", ("technology", "innovation", "research", "software", "platform", "robotics", "battery"), "Valora qué necesidad resuelve esta innovación y si es viable aplicarla a tu proyecto."),
]
MAX_STORIES = 5
MAX_AGE_HOURS = 96

def simple_text(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())

def parse_date(raw):
    try:
        result = email.utils.parsedate_to_datetime(raw)
        return result.astimezone(dt.timezone.utc)
    except (ValueError, TypeError, IndexError):
        pass
    try:
        result = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return result.astimezone(dt.timezone.utc)
    except (ValueError, AttributeError):
        return None

def fetch_items(name, feed_url, domain):
    req = urllib.request.Request(feed_url, headers={"User-Agent": "BrankaNewsBot/1.0 (+https://github.com/xabimurua/branka)", "Accept": "application/rss+xml, application/atom+xml, application/xml"})
    with urllib.request.urlopen(req, timeout=16) as response:
        raw = response.read(2_000_000)
    root = ET.fromstring(raw)
    rss = root.findall(".//item")
    atom = "{http://www.w3.org/2005/Atom}"
    entries = rss if rss else root.findall(f".//{atom}entry")
    result = []
    for node in entries:
        if rss:
            title = simple_text(node.findtext("title"))
            link = (node.findtext("link") or "").strip()
            description = simple_text(node.findtext("description"))
            date = parse_date(node.findtext("pubDate"))
        else:
            title = simple_text(node.findtext(f"{atom}title"))
            candidates = node.findall(f"{atom}link")
            link = next((x.attrib.get("href", "") for x in candidates if x.attrib.get("rel", "alternate") == "alternate"), "")
            description = simple_text(node.findtext(f"{atom}summary") or node.findtext(f"{atom}content"))
            date = parse_date(node.findtext(f"{atom}published") or node.findtext(f"{atom}updated"))
        parsed = urllib.parse.urlparse(link)
        host = (parsed.hostname or "").lower()
        if not title or not link.startswith("https://") or not (host == domain or host == domain.removeprefix("www.")) or not date:
            continue
        # No enlaces de agregadores ni artículos sin fecha contrastable.
        result.append({"title": title[:180], "link": link.split("#")[0], "desc": description[:250], "date": date, "source": name})
    return result

def classify(item):
    text = " " + (item["title"] + " " + item["desc"]).lower() + " "
    for tag, tool, terms, lesson in RULES:
        if any(term in text for term in terms):
            return tag, tool, lesson
    return None

def main():
    now = dt.datetime.now(dt.timezone.utc)
    stories = []
    for name, url, domain in SOURCES:
        try:
            found = fetch_items(name, url, domain)
            print(f"{name}: {len(found)} artículos leídos de {url}")
            stories.extend(found)
        except Exception as ex:
            print(f"Advertencia: no se pudo consultar {url}: {ex}", file=sys.stderr)
    dedup = {}
    for item in stories:
        age = (now - item["date"]).total_seconds() / 3600
        if not -2 <= age <= MAX_AGE_HOURS:
            continue
        topic = classify(item)
        if not topic:
            continue
        item["topic"] = topic
        dedup.setdefault(item["link"].split("?")[0], item)
    # Prioriza diversidad temática y artículos recientes.
    ranked = sorted(dedup.values(), key=lambda x: x["date"], reverse=True)
    selected, taken = [], set()
    for item in ranked:
        if item["topic"][0] not in taken:
            selected.append(item)
            taken.add(item["topic"][0])
        if len(selected) >= MAX_STORIES:
            break
    for item in ranked:
        if len(selected) >= MAX_STORIES:
            break
        if item not in selected:
            selected.append(item)
    if not selected:
        print("Sin nuevas noticias comprobables: no se cambia la web.")
        return 0
    news = []
    for item in selected:
        tag, tool, lesson = item["topic"]
        local = item["date"].astimezone(ZoneInfo("Europe/Madrid"))
        body = f"{item['source']} publicó esta noticia el {local:%d/%m/%Y}. Consulta la información original para conocer los detalles y los datos."
        news.append({"tag": tag, "title": item["title"], "body": body, "lesson": lesson, "tool": tool, "sources": [[item["source"], item["link"]]], "published": item["date"].isoformat()})
    page = PAGE.read_text(encoding="utf-8")
    pattern = r'(<script id="news-data" type="application/json">)(.*?)(</script>)'
    current = re.search(pattern, page, flags=re.S)
    if not current:
        raise RuntimeError("No se encuentra news-data en index.html")
    old = json.loads(current.group(2))
    # No hacer commits si no hay titulares distintos.
    old_urls = [i["sources"][0][1] for i in old.get("items", []) if i.get("sources")]
    new_urls = [i["sources"][0][1] for i in news]
    if old_urls == new_urls:
        print("Los titulares no han cambiado; se omite la publicación.")
        return 0
    local_now = now.astimezone(ZoneInfo("Europe/Madrid"))
    updated = {**old, "week": "Actualizado el " + local_now.strftime("%d/%m/%Y"), "items": news, "auto": True}
    encoded = json.dumps(updated, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    page = page[:current.start(2)] + encoded + page[current.end(2):]
    PAGE.write_text(page, encoding="utf-8")
    print(f"Listas para publicar {len(news)} noticias, todas con fuente y fecha.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
