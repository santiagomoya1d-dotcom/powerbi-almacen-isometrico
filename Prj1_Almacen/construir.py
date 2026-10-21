# -*- coding: utf-8 -*-
"""
Construye todo a partir de almacen.config.json, en orden, y para en el primer fallo:
datos → comprobación de datos → escena 3D (Vega) → página del informe (PBIR).

Uso:
  python construir.py                          simula un año con la configuración y lo monta todo
  python construir.py --datos-reales CARPETA   usa tus CSV (ver CONTRATO_DE_DATOS.md) en lugar de simular
  python construir.py --sin-datos              sin simular ni leer datos: nombre, colores y horario desde la
                                               configuración, comprobación, escena y página (si cambian filas,
                                               muelles o categorías, la comprobación pedirá rehacer los datos)
  python construir.py --config otra.json --prueba CARPETA
                                               variante de prueba: datos, escena y banco.html en CARPETA,
                                               sin tocar datos/ ni el informe
Después, en Power BI Desktop: «Actualizar» (si cambiaron los datos) y «Aplicar cambios externos»
(o cerrar y abrir el .pbip). Si cambiaron las filas o los muelles, hace falta lo uno y lo otro.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


def paso(titulo: str, *args: str) -> None:
    print(f"\n=== {titulo}", flush=True)
    r = subprocess.run([sys.executable, *args], cwd=RAIZ, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode:
        raise SystemExit(f"\nParado en «{titulo}» (código {r.returncode}). Corrige lo que indica y vuelve a lanzarlo.")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Construye datos, escena y página a partir de la configuración.")
    p.add_argument("--config", help="otra configuración (por defecto, almacen.config.json)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--datos-reales", metavar="CARPETA", help="carpeta con tus CSV en lugar de simular")
    g.add_argument("--sin-datos", action="store_true", help="no tocar los datos")
    p.add_argument("--prueba", metavar="CARPETA", help="escribir todo en CARPETA, sin tocar datos/ ni el informe")
    args = p.parse_args()
    cfg = ["--config", args.config] if args.config else []

    prueba = Path(args.prueba).resolve() if args.prueba else None
    datos = str(prueba / "datos") if prueba else None
    escena = str(prueba / "almacen_isometrico.vega.json") if prueba else None
    destino = ["--salida", datos] if datos else []

    paso("Configuración", "-c", "import sys; sys.path.insert(0, 'generador'); from configuracion import cargar; "
         f"c = cargar({args.config!r} if {bool(args.config)} else None); "
         "print(f'{c.nombre}: {len(c.filas)} filas x {c.huecos} huecos x {c.niveles} niveles x {c.posiciones} = "
         "{c.capacidad} ubicaciones; muelles {len(c.muelles_entrada)}+{len(c.muelles_salida)}; "
         "{len(c.categorias)} categorías')")
    if args.datos_reales:
        paso("Datos reales", "generador/completar_datos.py", "--entrada", args.datos_reales, *cfg, *destino)
    elif args.sin_datos:
        # Nombre, cabecera, fecha por defecto y colores también son datos (Almacen.csv y Categorias.csv)
        paso("Tablas de la configuración", "-c", "import sys; from pathlib import Path; sys.path.insert(0, 'generador'); "
             "from configuracion import cargar, actualizar_tablas_de_configuracion, DATOS; "
             f"c = cargar({args.config!r} if {bool(args.config)} else None); "
             f"d = Path({datos!r}) if {bool(datos)} else DATOS; actualizar_tablas_de_configuracion(c, d); "
             "print('Almacen.csv y Categorias.csv al día en', d)")
    else:
        paso("Simulación", "generador/generar_datos.py", *cfg, *destino)
    paso("Comprobación de datos", "generador/comprobar_datos.py", *cfg, *(["--datos", datos] if datos else []))
    paso("Escena 3D", "deneb/construir_escena.py", *cfg, *(["--salida", escena] if escena else []))
    if prueba:
        paso("Banco de pruebas", "herramientas/banco.py", *cfg, "--datos", datos, "--escena", escena,
             "--salida", str(prueba / "banco.html"))
        print(f"\nVariante lista en {prueba}. Ábrela con: python -m http.server --directory \"{prueba}\" "
              "y luego http://localhost:8000/banco.html")
    else:
        paso("Página del informe", "generador/pagina_almacen.py", *cfg)
        print("\nListo. En Power BI Desktop: «Actualizar» si cambiaron los datos y «Aplicar cambios externos».")


if __name__ == "__main__":
    main()
