# -*- coding: utf-8 -*-
"""
Valida los JSON del informe (formato PBIR) contra sus esquemas públicos de Microsoft (el $schema de
cada archivo), resolviendo las referencias remotas. Necesita conexión a internet y los paquetes
jsonschema y referencing (pip install jsonschema referencing).

Uso:  python herramientas/validar_pbir.py            (valida Prj1_Almacen.Report, junto al .pbip)
      python herramientas/validar_pbir.py "<carpeta .Report>"
Sale con código 1 si algún archivo no cumple su esquema.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

RAIZ = Path(__file__).resolve().parent.parent
cache: dict = {}


def bajar(uri: str):
    if uri not in cache:
        with urllib.request.urlopen(uri, timeout=30) as r:
            cache[uri] = json.loads(r.read().decode("utf-8"))
    return cache[uri]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    informe = Path(sys.argv[1]) if len(sys.argv) > 1 else next(
        c for base in (RAIZ, RAIZ.parent) for c in base.glob("*.Report"))
    registro = Registry(retrieve=lambda uri: Resource.from_contents(bajar(uri), default_specification=DRAFT7))
    fallos = 0
    for f in sorted(informe.rglob("*.json")):
        if {"StaticResources", "CustomVisuals", ".pbi"} & set(f.parts):
            continue
        doc = json.loads(f.read_text(encoding="utf-8-sig"))
        uri = doc.get("$schema")
        if not uri:
            continue
        errores = sorted(Draft7Validator(bajar(uri), registry=registro).iter_errors(doc), key=lambda e: list(e.path))
        rel = f.relative_to(informe)
        if errores:
            fallos += 1
            print(f"✗ {rel}  ({uri.split('/definition/')[-1]})")
            for e in errores[:6]:
                print("    -", "/".join(map(str, e.path)) or "(raíz)", ":", e.message[:220])
        else:
            print(f"✓ {rel}")
    print("Archivos con errores:", fallos)
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
