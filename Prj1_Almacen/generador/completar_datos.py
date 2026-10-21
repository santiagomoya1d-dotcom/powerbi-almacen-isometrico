# -*- coding: utf-8 -*-
"""
Prepara datos reales para el informe: toma las tablas que salen de tu SGA (Ubicaciones, Movimientos,
Productos y, si las tienes, Camiones) y escribe en datos/ las 18 tablas que lee el modelo, con las
columnas exactas del contrato (CONTRATO_DE_DATOS.md).

Calcula lo que falta: muelles, pasillos, zonas, categorías y almacén (de almacen.config.json),
calendario y horas, ocupación hora a hora por fila, clase ABC si no la traes, y las columnas
opcionales vacías. Las tablas opcionales que no traigas se escriben solo con la cabecera.

Uso:  python generador/completar_datos.py --entrada carpeta_con_tus_csv [--salida datos] [--config ...]
Después: python generador/comprobar_datos.py
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from configuracion import (DATOS, _mezcla, argumentos, cargar, escribir_csv, filas_almacen, filas_categorias,
                           filas_muelles)
from contrato import TABLAS, TIPOS_MOVIMIENTO, columnas, obligatorias

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
COLORES_EXTRA = ["#38BDF8", "#F59E0B", "#22C55E", "#EC4899", "#F97316", "#8B5CF6", "#EF4444", "#14B8A6",
                 "#EAB308", "#6366F1", "#84CC16", "#F43F5E"]
avisos: list[str] = []


def leer(carpeta: Path, tabla: str, necesaria: bool) -> pd.DataFrame | None:
    ruta = carpeta / f"{tabla}.csv"
    if not ruta.exists():
        if necesaria:
            raise SystemExit(f"Falta {ruta}: es obligatoria (ver CONTRATO_DE_DATOS.md)")
        return None
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    falta = [c for c in obligatorias(tabla) if c not in df.columns]
    if falta:
        raise SystemExit(f"{tabla}.csv no tiene las columnas obligatorias {falta}")
    sobran = [c for c in df.columns if c not in columnas(tabla)]
    if sobran:
        avisos.append(f"{tabla}: se ignoran las columnas que no están en el contrato: {sobran}")
    return df


def ajustar(df: pd.DataFrame, tabla: str) -> pd.DataFrame:
    """Columnas del contrato, en su orden; las que falten, vacías."""
    for c in columnas(tabla):
        if c not in df.columns:
            df[c] = ""
    return df[columnas(tabla)]


def guardar(df: pd.DataFrame, carpeta: Path, tabla: str) -> None:
    df = ajustar(df.copy(), tabla)
    df.to_csv(carpeta / f"{tabla}.csv", index=False, encoding="utf-8", lineterminator="\r\n")
    print(f"{tabla:<18} {len(df):>8} filas  ({TABLAS[tabla][0]})")


def texto_fecha(serie: pd.Series) -> pd.Series:
    return serie.dt.strftime("%Y-%m-%d")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argumentos(__doc__.strip().splitlines()[0], "carpeta donde se escriben las tablas (por defecto, datos/)")
    p.add_argument("--entrada", required=True, help="carpeta con tus CSV (Ubicaciones, Movimientos, Productos, Camiones…)")
    args = p.parse_args()
    cfg = cargar(args.config)
    entrada = Path(args.entrada)
    salida = Path(args.salida) if args.salida else DATOS
    if entrada.resolve() == salida.resolve():
        raise SystemExit("--entrada y --salida deben ser carpetas distintas (la salida se sobrescribe)")
    salida.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ ubicaciones
    u = leer(entrada, "Ubicaciones", True)
    orden_fila = {f: i + 1 for i, f in enumerate(cfg.filas)}
    desconocidas = sorted(set(u["Pasillo"]) - set(orden_fila))
    if desconocidas:
        raise SystemExit(f"Ubicaciones: filas que no están en estanterias.filas de la configuración: {desconocidas}")
    u["Orden pasillo"] = u["Pasillo"].map(orden_fila)
    if "ZonaID" not in u.columns or (u["ZonaID"] == "").all():
        u["ZonaID"] = u["Pasillo"].map(cfg.zona_de)

    # ------------------------------------------------------------------ movimientos
    m = leer(entrada, "Movimientos", True)
    m["_t"] = pd.to_datetime(m["FechaHora"], errors="coerce")
    if m["_t"].isna().any():
        raise SystemExit(f"Movimientos: {int(m['_t'].isna().sum())} filas con FechaHora que no se entiende (usa AAAA-MM-DD HH:MM:SS)")
    if "MovimientoID" not in m.columns or (m["MovimientoID"] == "").all():
        m = m.sort_values("_t", kind="stable").reset_index(drop=True)
        m["MovimientoID"] = range(1, len(m) + 1)
    operaciones = m[m["Tipo"] != "Stock inicial"]
    if operaciones.empty:
        raise SystemExit("Movimientos: no hay entradas ni salidas, solo stock inicial")
    primer_dia = operaciones["_t"].min().normalize()
    ultimo_dia = operaciones["_t"].max().normalize()
    m["Fecha"] = texto_fecha(m["_t"].dt.normalize())
    m["Hora"] = m["_t"].dt.hour.astype(str)
    previo = m["_t"] < primer_dia               # el stock inicial cuenta desde el primer día, a las 00
    m.loc[previo, "Fecha"] = primer_dia.strftime("%Y-%m-%d")
    m.loc[previo, "Hora"] = "0"
    m["FechaHora"] = m["_t"].dt.strftime("%Y-%m-%d %H:%M:%S")
    otros = sorted(set(m["Tipo"]) - set(TIPOS_MOVIMIENTO))
    if otros:
        avisos.append(f"Movimientos: tipos que el informe no cuenta como entrada ni salida: {otros}")

    # ------------------------------------------------------------------ productos y categorías
    pr = leer(entrada, "Productos", True)
    if "Clase ABC" not in pr.columns or (pr["Clase ABC"] == "").all():
        salidas = m[m["Tipo"] == "Salida"].groupby("SKU").size().reindex(pr["SKU"]).fillna(0)
        acum = salidas.sort_values(ascending=False).cumsum() / max(1, salidas.sum())
        clase = acum.apply(lambda v: "A" if v <= .65 else "B" if v <= .90 else "C")
        pr["Clase ABC"] = pr["SKU"].map(clase).fillna("C")
        avisos.append("Productos: sin «Clase ABC»; calculada por salidas (65 % A, 25 % B, 10 % C)")
    cats = filas_categorias(cfg)
    conocidas = {c["Categoría"] for c in cats}
    for i, nueva in enumerate(sorted(set(pr["Categoría"]) - conocidas)):
        color = COLORES_EXTRA[(len(cats) + i) % len(COLORES_EXTRA)]
        cats.append({"Categoría": nueva, "Nombre corto": nueva, "Color": color,
                     "Tono claro": _mezcla(color, (255, 255, 255), 0.45), "Tono oscuro": _mezcla(color, (0, 0, 0), 0.3),
                     "Orden": len(cats) + 1})
        avisos.append(f"Categorías: «{nueva}» no está en la configuración; se le da el color {color} (añádela a "
                      "almacen.config.json para elegirlo)")
    sin_uso = conocidas - set(pr["Categoría"])
    if sin_uso:
        avisos.append(f"Categorías de la configuración sin productos: {sorted(sin_uso)}")

    # ------------------------------------------------------------------ camiones y muelles
    c = leer(entrada, "Camiones", False)
    if c is None:
        c = pd.DataFrame(columns=columnas("Camiones"))
        avisos.append("Camiones: no hay; los muelles saldrán siempre libres")
    else:
        ini = pd.to_datetime(c["Inicio operación"], errors="coerce")
        if "Fecha" not in c.columns or (c["Fecha"] == "").all():
            c["Fecha"] = texto_fecha(ini.dt.normalize())
    muelles = filas_muelles(cfg)
    ids = {r["MuelleID"] for r in muelles}
    usados = (set(c["MuelleID"]) | set(m.get("MuelleID", pd.Series(dtype=str)))) - {""}
    if usados - ids:
        raise SystemExit(f"Muelles en tus datos que no están en la configuración (muelles.entrada / muelles.salida): "
                         f"{sorted(usados - ids)}")

    # ------------------------------------------------------------------ calendario y horas
    fechas = [primer_dia, ultimo_dia]
    if len(c):
        fc = pd.to_datetime(c["Fecha"], errors="coerce").dropna()
        fechas += [fc.min(), fc.max()]
    dias = pd.date_range(min(fechas), max(fechas), freq="D")
    con_actividad = set(operaciones["_t"].dt.normalize())
    cal = pd.DataFrame({
        "Fecha": dias.strftime("%Y-%m-%d"), "Año": dias.year, "Mes": dias.month,
        "Nombre del mes": [MESES[d.month - 1] for d in dias], "Mes corto": [MESES[d.month - 1][:3] for d in dias],
        "Año-mes": dias.year * 100 + dias.month,
        "Mes y año": [f"{MESES[d.month - 1][:3]} {d.year % 100:02d}" for d in dias],
        "Trimestre": [f"T{(d.month - 1) // 3 + 1}" for d in dias], "Semana ISO": dias.isocalendar().week.values,
        "Día": dias.day, "Día de la semana": [DIAS[d.weekday()] for d in dias], "Orden día semana": dias.weekday + 1,
        "Abierto": ["Sí" if d in con_actividad else "No" for d in dias], "Festivo": "", "Temporada": "Normal"})
    horas = pd.DataFrame({"Hora": range(24), "Hora texto": [f"{h:02d}:00" for h in range(24)],
                          "Turno": ["Mañana" if 6 <= h < 14 else "Tarde" if 14 <= h < 22 else "Noche" for h in range(24)]})

    # ------------------------------------------------------------------ ocupación hora a hora por fila
    # Fotografía al final de cada hora: movimientos con FechaHora anterior al corte (igual que el simulador)
    pasillo_de = dict(zip(u["UbicacionID"], u["Pasillo"]))
    mm = m.assign(Pasillo=m["UbicacionID"].map(pasillo_de), s=pd.to_numeric(m["Signo"], errors="coerce").fillna(0))
    origen = dias[0]
    cubo = ((mm["_t"] - origen) // pd.Timedelta(hours=1)).clip(lower=0).astype(int)
    n_horas = len(dias) * 24
    tabla = (mm.assign(cubo=cubo).groupby(["cubo", "Pasillo"])["s"].sum().unstack(fill_value=0)
             .reindex(range(n_horas), fill_value=0).reindex(columns=cfg.filas, fill_value=0).cumsum())
    larga = tabla.stack().rename("Ocupadas").reset_index()
    larga.columns = ["cubo", "Pasillo", "Ocupadas"]
    larga["Fecha"] = (origen + pd.to_timedelta(larga["cubo"] // 24, unit="D")).dt.strftime("%Y-%m-%d")
    larga["Hora"] = larga["cubo"] % 24
    larga["Ocupadas"] = larga["Ocupadas"].astype(int)
    oh = larga.assign(_o=larga["Pasillo"].map(orden_fila)).sort_values(["cubo", "_o"])

    # ------------------------------------------------------------------ pasillos, zonas y almacén
    cap_fila = u.groupby("Pasillo").size()
    pas = pd.DataFrame([{"Pasillo": f, "Orden pasillo": i + 1, "ZonaID": cfg.zona_de[f],
                         "Capacidad (palets)": int(cap_fila.get(f, 0))} for i, f in enumerate(cfg.filas)])
    zon = pd.DataFrame([{"ZonaID": z.id, "Zona": f"{z.id} · {z.nombre}", "Orden": z.orden, "Descripción": z.descripcion,
                         "Capacidad (palets)": int(sum(cap_fila.get(f, 0) for f in z.filas))} for z in cfg.zonas])
    alm = filas_almacen(cfg)
    if not alm[0]["Fecha por defecto"]:
        alm[0]["Fecha por defecto"] = ultimo_dia.strftime("%Y-%m-%d")

    # ------------------------------------------------------------------ escribir
    print(f"Datos de {entrada} → {salida}")
    guardar(u, salida, "Ubicaciones")
    guardar(m.sort_values(["_t", "MovimientoID"], kind="stable"), salida, "Movimientos")
    guardar(pr, salida, "Productos")
    guardar(c, salida, "Camiones")
    guardar(pd.DataFrame(muelles), salida, "Muelles")
    guardar(pas, salida, "Pasillos")
    guardar(zon, salida, "Zonas")
    guardar(cal, salida, "Calendario")
    guardar(horas, salida, "Horas")
    guardar(oh, salida, "OcupacionHoraria")
    escribir_csv(salida / "Almacen.csv", alm, columnas("Almacen"))
    escribir_csv(salida / "Categorias.csv", cats, columnas("Categorias"))
    print(f"{'Almacen, Categorias':<18}          desde {cfg.ruta.name}")
    for t in ("StockDiario", "Operarios", "Proveedores", "Destinos"):
        df = leer(entrada, t, False)
        guardar(df if df is not None else pd.DataFrame(columns=columnas(t)), salida, t)
    for a in avisos:
        print("aviso:", a)
    print("Siguiente paso: python generador/comprobar_datos.py" + (f" --datos \"{salida}\"" if args.salida else ""))


if __name__ == "__main__":
    main()
