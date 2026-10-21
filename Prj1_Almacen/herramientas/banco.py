# -*- coding: utf-8 -*-
"""
Banco de pruebas de la escena 3D sin Power BI: calcula con pandas lo mismo que las medidas que
recibe Deneb (una fila por ubicación) para uno o varios momentos y escribe un HTML que dibuja la
especificación Vega con vega-embed. Sirve para revisar un cambio de configuración o de escena en
el navegador antes de abrir Power BI.

Uso:  python herramientas/banco.py [--vista "2025-12-16 11@categoria@C@Bebidas"]... [--salida banco.html]
      --vista  FECHA HORA[@modo[@fila en foco[@categoría resaltada]]]; modo = abc, dias o categoria.
               Se puede repetir. Por defecto, la fecha y la hora por defecto de la configuración.
      --datos, --escena, --config  para probar otra variante (por defecto, las del proyecto)
Abre el HTML con un servidor local (python -m http.server) o directamente en el navegador.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "generador"))
from configuracion import DATOS, argumentos, cargar  # noqa: E402

VEGA = "https://cdn.jsdelivr.net/npm/vega@5.30.0/build/vega.min.js"
VEGA_EMBED = "https://cdn.jsdelivr.net/npm/vega-embed@6.26.0/build/vega-embed.min.js"


def muestra(datos: dict, momento: pd.Timestamp, modo: str, foco: str, categoria: str | None) -> list[dict]:
    """Las filas que Power BI pasaría a Deneb en ese momento (final de la hora elegida)."""
    u, m, p, c, cats = datos["u"], datos["m"], datos["p"], datos["c"], datos["cats"]
    hasta = m[m.FechaHora <= momento].merge(p[["SKU", "Producto", "Clase ABC", "Categoría"]], on="SKU")
    todas = hasta.groupby("UbicacionID").Signo.sum()
    ultima = hasta[hasta.Signo == 1].sort_values(["FechaHora", "MovimientoID"]).groupby("UbicacionID").tail(1) \
        .set_index("UbicacionID")
    filtrado = hasta if categoria is None else hasta[hasta["Categoría"] == categoria]
    ocupada = filtrado.groupby("UbicacionID").Signo.sum()
    ini = momento.floor("h")
    fin = ini + pd.Timedelta(hours=1)
    en_muelle = sorted(set(c[(c["Inicio operación"] < fin) & (c["Fin operación"] >= ini)]["MuelleID"]))
    hora = m[(m.Fecha == ini.strftime("%Y-%m-%d")) & (m.Hora == ini.hour)]
    hora_cat = hora if categoria is None else hora[hora.SKU.isin(p.loc[p["Categoría"] == categoria, "SKU"])]
    actividad = hora_cat[hora_cat.Tipo.isin(["Entrada", "Salida"])].groupby("UbicacionID").size()
    paleta = "|".join(f"{r['Tono claro']},{r['Color']},{r['Tono oscuro']}{r['Categoría']}"
                      for _, r in cats.sort_values("Orden").iterrows())
    comunes = {"Muelles con camión": ",".join(en_muelle),
               "Entradas en la hora": int((hora_cat.Tipo == "Entrada").sum()),
               "Salidas en la hora": int((hora_cat.Tipo == "Salida").sum()),
               "Modo de color": modo, "Fila en foco": foco, "Paleta de categorías": paleta}
    filas = []
    for r in u.to_dict("records"):
        uid = r["UbicacionID"]
        o = int(ocupada.get(uid, 0))
        fila = {"UbicacionID": uid, "Pasillo": r["Pasillo"], "Hueco": r["Hueco"], "Nivel": r["Nivel"],
                "Posición": r["Posición"], "Palets en stock": o, "Ocupada sin filtros": int(todas.get(uid, 0)),
                "Producto en ubicación": None, "Clase ABC en ubicación": None, "Categoría en ubicación": None,
                "Días en stock": None, "Actividad en la hora": int(actividad.get(uid, 0)), **comunes}
        if o == 1:
            e = ultima.loc[uid]
            fila.update({"Producto en ubicación": e["Producto"], "Clase ABC en ubicación": e["Clase ABC"],
                         "Categoría en ubicación": e["Categoría"],
                         "Días en stock": round((momento - e.FechaHora).total_seconds() / 86400, 1)})
        filas.append(fila)
    return filas


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argumentos("Dibuja la escena con datos de muestra en un HTML.", "ruta del HTML (por defecto, banco.html aquí)")
    p.add_argument("--vista", action="append", help="FECHA HORA[@modo[@fila[@categoría]]]")
    p.add_argument("--datos", help="carpeta de los CSV (por defecto, datos/)")
    p.add_argument("--escena", help="especificación Vega (por defecto, deneb/almacen_isometrico.vega.json)")
    p.add_argument("--ancho", type=int, default=1312)
    p.add_argument("--alto", type=int, default=824)
    args = p.parse_args()
    cfg = cargar(args.config)
    carpeta = Path(args.datos) if args.datos else DATOS
    escena = Path(args.escena) if args.escena else RAIZ / "deneb" / "almacen_isometrico.vega.json"
    salida = Path(args.salida) if args.salida else Path(__file__).resolve().with_name("banco.html")
    spec = json.loads(escena.read_text(encoding="utf-8"))

    datos = {
        "u": pd.read_csv(carpeta / "Ubicaciones.csv"),
        "m": pd.read_csv(carpeta / "Movimientos.csv", parse_dates=["FechaHora"]),
        "p": pd.read_csv(carpeta / "Productos.csv"),
        "c": pd.read_csv(carpeta / "Camiones.csv", parse_dates=["Inicio operación", "Fin operación"]),
        "cats": pd.read_csv(carpeta / "Categorias.csv"),
    }
    defecto = f"{cfg.fecha_por_defecto or datos['m'].FechaHora.max().date()} {cfg.hora_por_defecto}"
    bloques = []
    for i, v in enumerate(args.vista or [defecto]):
        partes = v.split("@")
        fecha_hora = partes[0].strip().rsplit(" ", 1)
        momento = pd.Timestamp(fecha_hora[0]) + pd.Timedelta(hours=int(fecha_hora[1]), minutes=59, seconds=59)
        modo = partes[1] if len(partes) > 1 and partes[1] else "abc"
        foco = partes[2] if len(partes) > 2 and partes[2] else "Todas"
        categoria = partes[3] if len(partes) > 3 and partes[3] else None
        valores = muestra(datos, momento, modo, foco, categoria)
        sp = json.loads(json.dumps(spec))
        sp["width"], sp["height"] = args.ancho, args.alto
        next(d for d in sp["data"] if d["name"] == "dataset")["values"] = valores
        ocupadas = sum(f["Palets en stock"] for f in valores)
        titulo = (f"{momento:%d/%m/%Y %H}:00 · color {modo} · fila {foco}" + (f" · {categoria}" if categoria else "")
                  + f" · {ocupadas} de {len(valores)} ubicaciones ocupadas · muelles {valores[0]['Muelles con camión'] or '—'}")
        bloques.append((f"v{i}", titulo, sp))
        print(titulo)

    html = ["<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Banco de la escena</title>",
            f"<script src='{VEGA}'></script><script src='{VEGA_EMBED}'></script>",
            "<style>body{background:#060A13;color:#CBD5E1;font-family:'Segoe UI',sans-serif;margin:16px}"
            "h3{font-weight:500;font-size:14px}pre{color:#F87171}</style></head><body>",
            f"<h2 style='font-weight:600'>{cfg.nombre} · {escena.name}</h2>"]
    for id_, titulo, _ in bloques:
        html.append(f"<h3>{titulo}</h3><div id='{id_}'></div><pre id='{id_}e'></pre>")
    html.append("<script>")
    for id_, _, sp in bloques:
        html.append(f"vegaEmbed('#{id_}', {json.dumps(sp, ensure_ascii=False)}, {{renderer: 'canvas', actions: false}})"
                    f".catch(e => document.getElementById('{id_}e').textContent = e.toString());")
    html.append("</script></body></html>")
    salida.write_text("\n".join(html), encoding="utf-8")
    print("Escrito:", salida)


if __name__ == "__main__":
    main()
