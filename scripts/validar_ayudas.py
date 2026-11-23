#!/usr/bin/env python3
"""Valida contenido/ayudas.json antes de publicar. Uso: python3 scripts/validar_ayudas.py

Sale con error (y no se debe publicar) si alguna ficha no cumple el formato.
También marca como "cerrada" las convocatorias cuya fecha límite ya ha pasado.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "contenido" / "ayudas.json"
SCOPES = {"España", "Europa", "Andalucía", "Aragón", "Asturias", "Illes Balears", "Canarias", "Cantabria", "Castilla-La Mancha", "Castilla y León", "Cataluña", "Comunitat Valenciana", "Extremadura", "Galicia", "Madrid", "Murcia", "Navarra", "Euskadi", "La Rioja", "Ceuta", "Melilla"}
TYPES = {"Subvención", "Préstamo", "Capital", "Mixta", "Programa"}
STATUS = {"abierta", "permanente", "consultar", "proxima", "cerrada"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")


def main():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    raw = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<script id="tools-data" type="application/json">(.*?)</script>', raw, re.S)
    tools = json.loads(m.group(1))
    slugs = {t["slug"] for t in (tools["tools"] if isinstance(tools, dict) else tools)}
    today = dt.date.today()
    errors, names = [], set()
    for i, a in enumerate(data.get("items", [])):
        where = f"ficha {i + 1} ({a.get('name', '?')})"
        for k, lo, hi in (("name", 3, 120), ("org", 3, 120), ("amount", 5, 200), ("for", 30, 600)):
            v = a.get(k)
            if not isinstance(v, str) or not lo <= len(v) <= hi or "<" in v or EMAIL.search(v):
                errors.append(f"{where}: '{k}' debe tener {lo}-{hi} caracteres, sin HTML ni correos")
        if a.get("name", "").lower() in names:
            errors.append(f"{where}: ficha duplicada")
        names.add(a.get("name", "").lower())
        if a.get("scope") not in SCOPES:
            errors.append(f"{where}: scope debe ser uno de {sorted(SCOPES)}")
        if a.get("type") not in TYPES:
            errors.append(f"{where}: type debe ser uno de {sorted(TYPES)}")
        if a.get("status") not in STATUS:
            errors.append(f"{where}: status debe ser uno de {sorted(STATUS)}")
        if a.get("tool") not in slugs:
            errors.append(f"{where}: herramienta desconocida {a.get('tool')}")
        if not str(a.get("url", "")).startswith("https://"):
            errors.append(f"{where}: url oficial https obligatoria")
        src = a.get("sources")
        if not isinstance(src, list) or not src or not all(isinstance(s, list) and len(s) == 2 and str(s[1]).startswith("https://") for s in src):
            errors.append(f"{where}: al menos una fuente [nombre, https://...]")
        d = a.get("deadline")
        if d is not None:
            try:
                deadline = dt.date.fromisoformat(d)
                if deadline < today and a.get("status") != "cerrada":
                    a["status"] = "cerrada"
                    print(f"Marcada como cerrada: {a.get('name')}")
            except ValueError:
                errors.append(f"{where}: deadline debe ser AAAA-MM-DD o null")
        if a.get("opens"):
            try:
                dt.date.fromisoformat(a["opens"])
            except ValueError:
                errors.append(f"{where}: opens debe ser AAAA-MM-DD")
        if a.get("status") == "proxima" and not a.get("opens"):
            errors.append(f"{where}: una ayuda 'proxima' necesita la fecha de apertura en 'opens'")
        if a.get("status") == "abierta" and not d:
            errors.append(f"{where}: una ayuda 'abierta' necesita deadline; si no tiene fecha usa 'permanente' o 'consultar'")
        try:
            dt.date.fromisoformat(a.get("checked", ""))
        except ValueError:
            errors.append(f"{where}: checked debe ser la fecha de revisión AAAA-MM-DD")
    if errors:
        print("NO SE PUBLICA:\n- " + "\n- ".join(errors))
        return 1
    data["updated"] = today.isoformat()
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    abiertas = sum(1 for a in data["items"] if a["status"] != "cerrada")
    print(f"OK: {len(data['items'])} ayudas ({abiertas} abiertas o permanentes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
