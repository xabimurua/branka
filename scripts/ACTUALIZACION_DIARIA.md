# Actualización diaria de Branka (Noticias y Aprende)

Cada mañana una tarea programada de Claude publica en branka.es:

- **Noticias:** 2 o 3 artículos propios sobre lo más relevante de las últimas 24-48 h en startups, inversión, IA aplicada a negocio e impacto social, con su lección para emprendedores.
- **Aprende:** 1 episodio de podcast reciente o especialmente útil para emprendedores.

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

3. Publicar y generar páginas:

```bash
python3 scripts/publicar_diario.py /tmp/hoy.json
SITE_URL=https://branka.es python3 scripts/generar_paginas_seo.py
```

4. Commit y push normal a `main` (autor `xabimurua@users.noreply.github.com`; nunca force-push).

## Reglas

- Todo en español, claro y cercano, pensado para quien empieza a emprender.
- Solo hechos comprobados en las fuentes enlazadas; nada inventado. Si no hay noticias verificables, no se publica.
- Redactar con palabras propias: nada copiado de las fuentes.
- No repetir noticias ni episodios ya publicados (el script los descarta).
- Nunca publicar correos personales ni datos privados.
