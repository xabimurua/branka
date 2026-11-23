# Actualización diaria de Branka (Noticias y Aprende)

Cada mañana una tarea programada de Claude publica en branka.es:

- **Noticias:** 2 o 3 artículos propios sobre lo más relevante de las últimas 24-48 h en startups, inversión, IA aplicada a negocio e impacto social, con su lección para emprendedores.
- **Aprende:** 1 episodio de podcast reciente o especialmente útil para emprendedores.
- **Ayudas:** el mapa de ayudas y subvenciones (`contenido/ayudas.json`, página `#ayudas`).

La GitHub Action `noticias-diarias.yml` ya no se ejecuta sola (solo a mano), para no duplicar.

## Pasos

1. Investigar con búsqueda web y leer las fuentes originales. Cada noticia necesita **al menos 2 fuentes https distintas** que confirmen los hechos.
2. Escribir `/tmp/hoy.json`:

```json
{
  "noticias": [{
    "tag": "Financiación | Inteligencia artificial | Impacto social | Emprendimiento | Mercado | Producto | ...",
    "title": "Titular en español (10-150 caracteres)",
    "dek": "Entradilla: qué ha pasado (40-300)",
    "insight": "Lección para quien emprende (40-400)",
    "action": "Una acción concreta que puede hacer hoy (20-300)",
    "tool": "slug de una herramienta de tools-data en index.html",
    "sources": [["Medio", "https://..."], ["Otro medio", "https://..."]],
    "paragraphs": ["4 a 6 párrafos propios, de 80 a 700 caracteres cada uno"]
  }],
  "episodios": [{
    "title": "Título del episodio",
    "show": "Nombre del podcast",
    "lang": "ES | EN",
    "why": "Qué aprende un emprendedor con él (30-300)",
    "tool": "slug de herramienta",
    "url": "https://... (YouTube con ?v= se reproduce en la web)",
    "published": "2026-11-22T00:00:00+00:00"
  }]
}
```

3. Publicar y generar páginas (y validar las ayudas):

```bash
python3 scripts/publicar_diario.py /tmp/hoy.json
SITE_URL=https://branka.es python3 scripts/generar_paginas_seo.py
python3 scripts/validar_ayudas.py
```

4. Commit y push normal a `main` (autor `xabimurua@users.noreply.github.com`; nunca force-push).

## Ayudas y subvenciones (`contenido/ayudas.json`)

Cada día:

1. Busca convocatorias **nuevas** para emprender en **toda España**: estatales (SEPE, Seguridad Social, ENISA, CDTI, ICO, ministerios), de **cada comunidad autónoma** (gobiernos autonómicos, agencias de desarrollo como SPRI, ACCIÓ, IDEPA, IVACE, Agencia IDEA, IGAPE…, diputaciones y cabildos) y europeas (EIC y similares). Rota cada día varias comunidades para cubrirlas todas a lo largo de la semana, empezando por las que tienen menos fichas. Prioriza las fuentes oficiales (BOE, boletines autonómicos y provinciales, webs de los organismos) y la Base de Datos Nacional de Subvenciones (infosubvenciones.es).
2. Revisa las que ya están: si ha cambiado el plazo, el importe o el estado, corrígelo. Si una cerrada se vuelve a convocar, actualiza la ficha (nombre con el nuevo año, nueva fecha, `status`).
3. Añade solo ayudas comprobadas en su convocatoria oficial. No inventes importes ni fechas: si no sabes el plazo, usa `"status": "consultar"` y `"deadline": null`.
4. Elimina fichas cerradas hace más de 6 meses que no vayan a repetirse.
5. Ejecuta `python3 scripts/validar_ayudas.py` (marca solas como cerradas las vencidas y valida el formato). Si falla, corrige y repite.

Formato de cada ficha:

```json
{
  "name": "Nombre de la convocatoria y año",
  "org": "Organismo",
  "scope": "España (estatal) | Europa | nombre de la comunidad: Andalucía, Aragón, Asturias, Illes Balears, Canarias, Cantabria, Castilla-La Mancha, Castilla y León, Cataluña, Comunitat Valenciana, Extremadura, Galicia, Madrid, Murcia, Navarra, Euskadi, La Rioja, Ceuta, Melilla",
  "area": "opcional: provincia, isla o municipio (p. ej. Gipuzkoa)",
  "type": "Subvención | Préstamo | Capital | Mixta | Programa",
  "amount": "Qué da y cuánto, en una frase",
  "for": "A quién va dirigida y requisitos clave (30-600 caracteres)",
  "deadline": "AAAA-MM-DD o null",
  "opens": "AAAA-MM-DD, solo si aún no ha abierto",
  "status": "abierta (con deadline) | proxima (con opens) | permanente | consultar | cerrada",
  "url": "https://enlace a la convocatoria oficial",
  "sources": [["Nombre de la fuente", "https://..."]],
  "tool": "slug de herramienta de tools-data en index.html",
  "checked": "AAAA-MM-DD (fecha de hoy)"
}
```

## Reglas

- Todo en español, claro y cercano, pensado para quien empieza a emprender.
- Solo hechos comprobados en las fuentes enlazadas; nada inventado. Si no hay noticias verificables, no se publica.
- Redactar con palabras propias: nada copiado de las fuentes.
- No repetir noticias ni episodios ya publicados (el script los descarta).
- Nunca publicar correos personales ni datos privados.
