#!/usr/bin/env python3
"""Amplía la biblioteca Branka desde RSS públicos de podcasts.

Localiza los canales de las recomendaciones existentes mediante el catálogo
de Apple Podcasts. Solo acepta coincidencias suficientemente específicas y
episodios con enlace real. Nunca inventa episodios ni modifica la selección manual.
"""
import datetime as dt
import email.utils
import html
import json
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
OUTPUT = ROOT / "contenido" / "podcasts.json"

def simplify(text):
    normalized = unicodedata.normalize("NFKD", str(text or "").casefold())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in normalized if not unicodedata.combining(c))).strip()

def plain(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", value or ""))).strip()

def json_request(url):
    req = urllib.request.Request(url,headers={"User-Agent":"BrankaPodcastCatalogue/1.0 (+https://branka.es)"})
    with urllib.request.urlopen(req,timeout=18) as response:
        return json.loads(response.read(1_500_000))

def find_feed(show):
    params = urllib.parse.urlencode({"term":show["name"],"media":"podcast","entity":"podcast","country":"es","limit":12})
    data = json_request("https://itunes.apple.com/search?"+params)
    expected = simplify(show["name"])
    for result in data.get("results",[]):
        actual = simplify(result.get("collectionName",""))
        # No confundir con podcasts distintos por coincidencia de palabras.
        if expected != actual and not (len(expected)>15 and (actual.startswith(expected+" ") or expected.startswith(actual+" "))):
            continue
        feed = result.get("feedUrl","")
        if feed.startswith("https://") and result.get("collectionViewUrl","").startswith("https://"):
            return feed, result.get("collectionViewUrl")
    return None,None

def read_episodes(feed,collection,show):
    req = urllib.request.Request(feed, headers={"User-Agent":"BrankaPodcastCatalogue/1.0 (+https://branka.es)"})
    with urllib.request.urlopen(req,timeout=20) as response:
        root = ET.fromstring(response.read(2_500_000))
    episodes = []
    now = dt.datetime.now(dt.timezone.utc)
    for item in root.findall(".//channel/item")[:55]:
        title = plain(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        if not link.startswith("https://"):
            link = collection
        date_text = item.findtext("pubDate") or ""
        try:
            published = email.utils.parsedate_to_datetime(date_text).astimezone(dt.timezone.utc)
        except (ValueError, TypeError, IndexError):
            continue
        if not title or not (0 <= (now-published).days <= 730):
            continue
        summary = plain(item.findtext("description"))[:260]
        episodes.append({
            "show":show["name"],"title":title[:180],
            "why": summary or "Nuevo episodio del podcast. Consulta la descripción original y escucha la conversación.",
            "url":link,"lang":show.get("lang","ES"),"tool":"",
            "published":published.isoformat(),"source":"Podcast RSS",
        })
        if len(episodes)>=15:
            break
    return episodes

def main():
    raw = INDEX.read_text(encoding="utf-8")
    match = re.search(r'<script id="learn-data" type="application/json">(.*?)</script>',raw,re.S)
    if not match:
        raise SystemExit("Falta learn-data")
    shows = json.loads(match.group(1)).get("podcasts",[])
    previous = {"episodes":[]}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    fetched = []
    for show in shows:
        try:
            feed,collection = find_feed(show)
            if not feed:
                print("Sin coincidencia segura en Apple:",show["name"])
                continue
            episodes = read_episodes(feed,collection,show)
            fetched.extend(episodes)
            print(show["name"],len(episodes))
        except Exception as exc:
            print("RSS no disponible:",show["name"],str(exc)[:180])
    unique = {}
    for ep in fetched+previous.get("episodes",[]):
        key = simplify(ep.get("show"))+"|"+simplify(ep.get("title"))
        if ep.get("url","").startswith("https://") and ep.get("title"):
            unique.setdefault(key,ep)
    result = sorted(unique.values(),key=lambda x:x.get("published",""),reverse=True)[:500]
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps({"episodes":result,"updated":dt.datetime.now(dt.timezone.utc).isoformat()},ensure_ascii=False,indent=2)+"\n"
    if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8")!=content:
        OUTPUT.write_text(content,encoding="utf-8")
    print("Catálogo de episodios:",len(result))

if __name__=="__main__":
    main()
