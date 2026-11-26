#!/usr/bin/env python3
"""Crea páginas HTML rastreables para noticias y un sitemap si SITE_URL está definido."""
import datetime as dt
import hashlib
import html
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
NEWS_DIR = ROOT / "noticias"
SITE_URL = os.getenv("SITE_URL", "").strip().rstrip("/")
if SITE_URL and (not SITE_URL.startswith("https://") or not urlsplit(SITE_URL).netloc):
    raise SystemExit("SITE_URL debe contener una URL HTTPS de la web pública.")

# Etiqueta de Google (contenedor GTM-N6LTTBFW): una sola vez por página, justo después de <head>.
GOOGLE_TAG = '''<script async src="https://www.googletagmanager.com/gtm.js?id=GTM-N6LTTBFW"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
</script>'''

def esc(s):
    return html.escape(str(s or ""), quote=True)

def slug(s):
    a = unicodedata.normalize("NFKD", s.lower())
    a = "".join(ch for ch in a if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", a).strip("-")[:66] or "noticia"

def layout(title, description, content, relpath, schema=None):
    canonical = f'<link rel="canonical" href="{esc(SITE_URL + "/" + relpath)}">' if SITE_URL else ""
    safe_json = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c") if schema else ""
    jsonld = f'<script type="application/ld+json">{safe_json}</script>' if schema else ""
    # Imagen para X/Twitter, LinkedIn, WhatsApp… Las redes exigen URL absoluta: usa SITE_URL o el dominio público.
    base = SITE_URL or "https://branka.es"
    image = esc(base + "/og-image.png")
    social = (
        f'<meta property="og:url" content="{esc(base + "/" + relpath)}"><meta property="og:site_name" content="Branka">'
        f'<meta property="og:locale" content="es_ES">\n'
        f'<meta property="og:image" content="{image}"><meta property="og:image:width" content="1200">'
        f'<meta property="og:image:height" content="630"><meta property="og:image:alt" content="Branka">\n'
        f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@edebenews">'
        f'<meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description[:155])}">'
        f'<meta name="twitter:image" content="{image}">'
    )
    return f'''<!doctype html>
<html lang="es"><head>
{GOOGLE_TAG}
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | Branka</title><meta name="description" content="{esc(description[:155])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
{canonical}<meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description[:155])}">
{social}
{jsonld}
<style>
:root{{--red:#c73920;--ink:#2b110b;--bg:#fdf7f3;--line:#eecdbb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 system-ui,Arial,sans-serif}}
header{{background:#a52b17;color:white;padding:18px max(20px,calc((100vw - 980px)/2))}}
header a{{color:white;text-decoration:none;font-weight:800;font-size:24px}}
main{{max-width:980px;margin:0 auto;padding:34px 20px 70px}}
h1{{font-size:clamp(30px,4vw,45px);line-height:1.17;letter-spacing:-.03em}}
h2{{font-size:23px;line-height:1.3}}a{{color:#b3331e}}a:hover{{text-decoration-thickness:2px}}
.kicker{{color:#a52b17;font-weight:750;font-size:14px;text-transform:uppercase;letter-spacing:.07em}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:18px;padding-top:14px}}
.card{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px}}
.card h2{{font-size:20px;margin:7px 0}}.card p{{color:#674c41}}
.panel{{border-left:4px solid #e66c2f;background:#fff0e6;padding:16px 22px;margin:30px 0}}
.cta{{display:flex;flex-wrap:wrap;gap:22px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:16px;padding:22px;margin:26px 0}}
.cta img{{width:240px;max-width:100%;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,.1)}}
.cta h2{{margin:0 0 12px}}.cta p{{margin:12px 0 0;font-size:15px}}
.btn{{display:inline-block;background:linear-gradient(90deg,#ec8f35,#da3a22);color:#fff!important;font-weight:750;text-decoration:none;padding:12px 22px;border-radius:999px}}
.meta,footer{{color:#6c4e43;font-size:14px}}
footer{{border-top:1px solid var(--line);padding:20px 0;margin-top:45px}}
nav a{{margin-right:18px}}time{{font-variant-numeric:tabular-nums}}
</style></head><body><header><a href="/">BRANKA</a></header><main>
<nav aria-label="Navegación"><a href="/">Inicio</a><a href="/noticias.html">Noticias</a><a href="/#herramientas">Herramientas</a></nav>
{content}<footer>Branka · Recursos para emprender. Esta sección enlaza fuentes originales y ofrece una lectura práctica; no sustituye a las fuentes ni constituye asesoramiento financiero.</footer>
</main></body></html>'''

def main():
    raw = INDEX.read_text(encoding="utf-8")
    match = re.search(r'<script id="news-data" type="application/json">(.*?)</script>', raw, re.S)
    if not match:
        raise SystemExit("No se encontró news-data")
    feed = json.loads(match.group(1))
    NEWS_DIR.mkdir(exist_ok=True)
    entries = []
    # Solo las piezas originales con análisis suficiente reciben URL individual.
    for item in feed.get("items", []) if feed.get("auto") is True else []:
        paragraphs = item.get("paragraphs", [])
        sources = item.get("sources", [])
        if not item.get("generated_with_ai") or not isinstance(paragraphs,list) or len(paragraphs) < 4 or len(sources) < 2:
            continue
        if not all(isinstance(x,list) and len(x) >= 2 and str(x[1]).startswith("https://") for x in sources):
            continue
        try:
            published = dt.datetime.fromisoformat(item["published"].replace("Z","+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        title = item.get("title", "").strip()
        if not title:
            continue
        key = "|".join(source[1] for source in sources)
        filename = slug(title) + "-" + hashlib.sha256(key.encode()).hexdigest()[:8] + ".html"
        relpath = "noticias/" + filename
        intro = item.get("body","").strip()
        bodytext = "".join("<p>" + esc(p) + "</p>" for p in paragraphs)
        ref_links = "".join('<li><a href="'+esc(src[1])+'" target="_blank" rel="noopener noreferrer">'+esc(src[0])+'</a></li>' for src in sources)
        content = f'''<article><p class="kicker">{esc(item.get("tag", "Branka Insights"))} · Análisis Branka</p>
<h1>{esc(title)}</h1><p class="meta">Branka · Publicado el <time datetime="{esc(published.date().isoformat())}">{esc(published.strftime("%d/%m/%Y"))}</time></p>
<p><strong>{esc(intro)}</strong></p>
{bodytext}
<section class="panel"><h2>Qué significa para tu proyecto</h2><p>{esc(item.get("lesson",""))}</p>
<h2>Una acción para empezar</h2><p>{esc(item.get("action",""))}</p></section>
<h2>Noticias utilizadas como fuentes</h2><p>Este análisis original de Branka combina noticias publicadas por medios independientes. Contrasta los detalles en las fuentes.</p><ul>{ref_links}</ul>
<p class="meta">Análisis redactado con asistencia de IA a partir de titulares y extractos RSS. Los hechos provienen de las fuentes enlazadas y las recomendaciones son interpretación editorial de Branka.</p>
<p><a href="/#herramientas">Explorar herramientas prácticas de Branka</a></p></article>'''
        schema = {"@context":"https://schema.org","@type":"Article","headline":title,"description":intro,
                  "datePublished":published.isoformat(),"inLanguage":"es",
                  "author":{"@type":"Organization","name":"Branka"},
                  "publisher":{"@type":"Organization","name":"Branka"},
                  "citation":[source[1] for source in sources]}
        if SITE_URL:
            schema["mainEntityOfPage"] = SITE_URL + "/" + relpath
        (ROOT / relpath).write_text(layout(title,intro,content,relpath,schema),encoding="utf-8")
        entries.append({"title":title,"url":relpath,"tag":item.get("tag","Actualidad"),
                        "published":published.date().isoformat(),"intro":intro})
    # Guías originales: las herramientas de Branka son más valiosas para SEO que
    # simples reseñas de noticias. Cada ficha tiene contenido útil, URL propia y
    # enlaces internos visibles sin JavaScript.
    tools_match = re.search(r'<script id="tools-data" type="application/json">(.*?)</script>', raw, re.S)
    if not tools_match:
        raise SystemExit("No se encontró tools-data")
    tools_data = json.loads(tools_match.group(1))
    tools_dir = ROOT / "herramientas"
    tools_dir.mkdir(exist_ok=True)
    tool_entries = []
    phase_names = tools_data.get("phases", [])
    for t in tools_data.get("tools", []):
        title = str(t.get("name", "")).strip()
        if not title:
            continue
        slug_path = slug(title) + ".html"
        reltool = "herramientas/" + slug_path
        short = str(t.get("para", "")).strip()
        phase = phase_names[t["ph"]] if isinstance(t.get("ph"), int) and 0 <= t["ph"] < len(phase_names) else "Emprendimiento"
        guide = "".join("<p>" + esc(p) + "</p>" for p in t.get("guion", []) if p)
        blocks = "".join("<li>" + esc(b) + "</li>" for b in t.get("blocks", []))
        example = "<section class=\"panel\"><h2>Ejemplo orientativo</h2><p>" + esc(t["example"]) + "</p></section>" if t.get("example") else ""
        # Llamada a la acción arriba: quien llega desde redes debe ver la descarga sin buscarla.
        app_url = "/#h-" + t["slug"].replace("_", "-")
        pdf_name = f'Branka_Plantilla_{t["slug"]}.pdf'
        if (ROOT / "plantillas" / pdf_name).exists():
            preview = f'Branka_Plantilla_{t["slug"]}.jpg'
            img = f'<img src="/plantillas/{esc(preview)}" alt="Vista previa de la plantilla {esc(title)}" loading="lazy">' if (ROOT / "plantillas" / preview).exists() else ""
            cta = (f'<section class="cta">{img}<div><h2>Descarga la plantilla gratis</h2>'
                   f'<a class="btn" href="/plantillas/{esc(pdf_name)}" download>Descargar plantilla (PDF)</a>'
                   f'<p><a href="{esc(app_url)}">Ver la herramienta completa en Branka</a></p></div></section>')
        else:
            cta = (f'<section class="cta"><div><h2>Descarga la plantilla gratis</h2>'
                   f'<a class="btn" href="{esc(app_url)}">Abrir y descargar la plantilla</a>'
                   f'<p>Hoja práctica con apartados guiados para imprimir o guardar en PDF.</p></div></section>')
        content = f'''<article><p class="kicker">Herramienta {esc(t.get("n", ""))} · {esc(phase)}</p>
<h1>{esc(title)}</h1><p>{esc(short)}</p>
{cta}
<h2>Para qué sirve y cómo utilizarla</h2>{guide}
<h2>Pasos y apartados que debes trabajar</h2><ol>{blocks}</ol>
<h2>Cuándo utilizarla</h2><p>{esc(t.get("cuando", ""))}</p>
{example}<p><a href="{esc(app_url)}">Abrir la herramienta y su plantilla en Branka</a></p>
<p><a href="/noticias.html">Noticias relacionadas con emprendimiento</a></p></article>'''
        tool_schema = {"@context":"https://schema.org","@type":"Article","headline":title,"description":short,"inLanguage":"es","publisher":{"@type":"Organization","name":"Branka"}}
        if SITE_URL:
            tool_schema["mainEntityOfPage"] = SITE_URL + "/" + reltool
        (tools_dir / slug_path).write_text(layout(title, short, content, reltool, tool_schema),encoding="utf-8")
        tool_entries.append((title, reltool, short, phase))
    listing = "<div class=\"cards\">" + "".join(f'<article class="card"><p class="kicker">{esc(ph)}</p><h2><a href="/{esc(path)}">{esc(title)}</a></h2><p>{esc(desc)}</p></article>' for title,path,desc,ph in tool_entries) + "</div>"
    (ROOT/"guias.html").write_text(layout("Guías y herramientas para emprender", "Guías prácticas sobre financiación, rondas de inversión, inteligencia artificial, impacto social y modelos de negocio.", '<h1>Guías prácticas para emprender</h1><p>Herramientas y explicaciones originales de Branka para validar ideas, conseguir financiación, preparar una ronda de inversión y utilizar IA de forma responsable.</p>'+listing, "guias.html", {"@context":"https://schema.org","@type":"CollectionPage","name":"Guías y herramientas para emprender | Branka"}), encoding="utf-8")
    # Preservar artículos antiguos para mantener sus URLs indexadas.
    articles = []
    for entry in entries:
        articles.append(f'''<article class="card"><div class="kicker">{esc(entry["tag"])}</div>
<h2><a href="/{esc(entry["url"])}">{esc(entry["title"])}</a></h2>
<p><time datetime="{esc(entry["published"])}">{esc(entry["published"])}</time></p><p>{esc(entry["intro"])}</p></article>''')
    summary = f'<div class="cards">{"".join(articles)}</div>' if articles else '<p>Aquí aparecerán las noticias verificables seleccionadas por Branka en las próximas actualizaciones diarias. Mientras tanto, puedes consultar nuestras herramientas.</p>'
    page = f'''<section><p class="kicker">Actualidad para emprender</p><h1>Noticias sobre emprendimiento, inversión, inteligencia artificial e impacto social</h1>
<p>Una selección de noticias recientes con enlaces a los medios de origen, fecha de publicación y preguntas útiles para quienes están creando o desarrollando un negocio.</p>
{summary}<section class="panel"><h2>Cómo seleccionamos las noticias</h2>
<p>Revisamos fuentes RSS públicas y descartamos artículos sin fecha o enlace verificable. No inventamos titulares ni atribuimos afirmaciones a una fuente que no las publique. Las sugerencias de Branka son ideas para reflexionar, no asesoramiento profesional.</p></section></section>'''
    webschema = {"@context":"https://schema.org","@type":"CollectionPage","name":"Noticias para emprendedores | Branka","description":"Actualidad de emprendimiento, financiación, inteligencia artificial e impacto social."}
    if SITE_URL:
        webschema["url"] = SITE_URL + "/noticias.html"
    # No modificar noticias.html: esa URL lleva al diseño original de Branka.
    # Las fichas SEO de cada noticia se publican independientemente en /noticias/.
    if SITE_URL:
        all_paths = ["","guias.html"] + ["noticias/"+p.name for p in sorted(NEWS_DIR.glob("*.html"))] + ["herramientas/"+p.name for p in sorted(tools_dir.glob("*.html"))]
        urls = "".join(f"<url><loc>{esc(SITE_URL + '/' + p)}</loc></url>" for p in all_paths)
        (ROOT/"sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+urls+"</urlset>",encoding="utf-8")
        (ROOT/"robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: "+SITE_URL+"/sitemap.xml\n",encoding="utf-8")
    else:
        (ROOT/"robots.txt").write_text("User-agent: *\nAllow: /\n\n# Para generar sitemap.xml y canonical absolutos, configurar SITE_URL en GitHub Actions.\n",encoding="utf-8")
    print(f"SEO: {len(entries)} noticias nuevas y {len(tool_entries)} guías propias generadas. SITE_URL configurada: {bool(SITE_URL)}")

if __name__=="__main__":
    main()
