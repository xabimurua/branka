#!/usr/bin/env python3
"""Publica en la web las noticias y episodios del día preparados por la tarea diaria de Claude.

Uso:
    python3 scripts/publicar_diario.py ruta/a/hoy.json
    SITE_URL=https://branka.es python3 scripts/generar_paginas_seo.py

Formato de hoy.json (ver scripts/ACTUALIZACION_DIARIA.md):
{
  "noticias": [{"tag","title","dek","insight","action","tool","sources":[[medio,url],...],"paragraphs":[...]}],
  "episodios": [{"title","show","lang","why","tool","url","published"}]
}
El script valida todo y no publica nada si algo no cumple las reglas.
"""
import datetime as dt
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"
NEWS_ARCHIVE = ROOT / "contenido" / "noticias.json"
PODCASTS = ROOT / "contenido" / "podcasts.json"
MAX_HOME_NEWS = 9
MAX_HOME_EPISODES = 12
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")


def block(raw, name):
    m = re.search(r'(<script id="%s" type="application/json">)(.*?)(</script>)' % name, raw, re.S)
    if not m:
        raise SystemExit(f"Falta {name} en index.html")
    return m, json.loads(m.group(2))


def put(raw, m, data):
    enc = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return raw[:m.start(2)] + enc + raw[m.end(2):]


def article_path(title, sources):
    n = unicodedata.normalize("NFKD", title.lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    short = re.sub(r"[^a-z0-9]+", "-", n).strip("-")[:66] or "noticia"
    digest = hashlib.sha256("|".join(u for _, u in sources).encode()).hexdigest()[:8]
    return "noticias/" + short + "-" + digest + ".html"


def fail(msg):
    raise SystemExit("NO SE PUBLICA: " + msg)


def check_text(label, value, lo, hi):
    if not isinstance(value, str) or not lo <= len(value.strip()) <= hi or "<" in value:
        fail(f"{label} debe tener entre {lo} y {hi} caracteres y sin HTML")
    if EMAIL.search(value):
        fail(f"{label} contiene un correo electrónico")


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    today = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    raw = PAGE.read_text(encoding="utf-8")
    _, tools = block(raw, "tools-data")
    slugs = {t["slug"] for t in (tools["tools"] if isinstance(tools, dict) else tools)}
    now = dt.datetime.now(dt.timezone.utc)

    # ---- Noticias
    mnews, feed = block(raw, "news-data")
    known_titles = {i.get("title", "").lower() for i in feed.get("items", [])}
    used = list(feed.get("used_source_urls", []))
    created = []
    for n in today.get("noticias", []):
        for k, lo, hi in (("tag", 3, 40), ("title", 10, 150), ("dek", 40, 300), ("insight", 40, 400), ("action", 20, 300)):
            check_text(k, n.get(k), lo, hi)
        if n["tool"] not in slugs:
            fail(f"herramienta desconocida: {n['tool']}")
        src = n.get("sources")
        if not isinstance(src, list) or len(src) < 2 or not all(isinstance(s, list) and len(s) == 2 and str(s[1]).startswith("https://") for s in src):
            fail(f"'{n['title']}' necesita al menos 2 fuentes https")
        if len({s[1] for s in src}) < 2:
            fail("las fuentes deben ser distintas")
        pars = n.get("paragraphs")
        if not isinstance(pars, list) or not 4 <= len(pars) <= 6:
            fail("cada noticia necesita entre 4 y 6 párrafos")
        for p in pars:
            check_text("párrafo", p, 80, 700)
        if n["title"].lower() in known_titles or any(s[1] in used for s in src):
            print("Ya publicada, se omite:", n["title"])
            continue
        created.append({
            "url": "/" + article_path(n["title"].strip(), src),
            "tag": n["tag"].strip(), "title": n["title"].strip(), "body": n["dek"].strip(),
            "lesson": n["insight"].strip(), "action": n["action"].strip(), "tool": n["tool"],
            "sources": src, "paragraphs": [p.strip() for p in pars],
            "published": now.isoformat(), "generated_with_ai": True,
        })
    if created:
        archive = []
        if NEWS_ARCHIVE.exists():
            archive = json.loads(NEWS_ARCHIVE.read_text(encoding="utf-8")).get("items", [])
        seen, acc = set(), []
        for item in created + feed.get("items", []) + archive:
            key = item.get("url") or item.get("title")
            if key and key not in seen:
                acc.append(item)
                seen.add(key)
        NEWS_ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
        NEWS_ARCHIVE.write_text(json.dumps({"items": acc[:1500]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        used = list(dict.fromkeys(used + [s[1] for c in created for s in c["sources"]]))[-500:]
        feed = {**feed,
                "week": "Branka Insights · actualizado el " + dt.datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y"),
                "items": (created + feed.get("items", []))[:MAX_HOME_NEWS],
                "auto": True, "used_source_urls": used}
        raw = put(raw, mnews, feed)

    # ---- Aprende
    mlearn, learn = block(raw, "learn-data")
    cat = json.loads(PODCASTS.read_text(encoding="utf-8")) if PODCASTS.exists() else {"episodes": [], "podcasts": []}
    known_urls = {e.get("url") for e in learn.get("episodes", []) + cat.get("episodes", [])}
    new_eps = []
    for e in today.get("episodios", []):
        for k, lo, hi in (("title", 3, 180), ("show", 2, 80), ("why", 30, 300)):
            check_text(k, e.get(k), lo, hi)
        if e.get("lang") not in ("ES", "EN"):
            fail("lang debe ser ES o EN")
        if e.get("tool") not in slugs:
            fail(f"herramienta desconocida: {e.get('tool')}")
        if not str(e.get("url", "")).startswith("https://"):
            fail("el episodio necesita una url https")
        if e["url"] in known_urls:
            print("Episodio ya publicado, se omite:", e["title"])
            continue
        ep = {k: e[k] for k in ("title", "show", "lang", "why", "tool", "url")}
        ep["published"] = e.get("published") or now.isoformat()
        ep["added"] = now.date().isoformat()
        new_eps.append(ep)
    if new_eps:
        learn = {**learn, "episodes": (new_eps + learn.get("episodes", []))[:MAX_HOME_EPISODES]}
        raw = put(raw, mlearn, learn)
        cat["episodes"] = new_eps + [x for x in cat.get("episodes", []) if x.get("url") not in {n["url"] for n in new_eps}]
        cat["updated"] = now.isoformat()
        PODCASTS.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not created and not new_eps:
        print("Nada nuevo que publicar.")
        return 0
    PAGE.write_text(raw, encoding="utf-8")
    print(f"Publicadas {len(created)} noticias y {len(new_eps)} episodios.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
