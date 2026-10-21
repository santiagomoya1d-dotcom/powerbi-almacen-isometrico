# -*- coding: utf-8 -*-
"""
Comprueba que la carpeta de datos cumple el contrato (CONTRATO_DE_DATOS.md) y cuadra con
almacen.config.json antes de abrir Power BI: columnas, claves, filas y muelles de la configuración,
y que ninguna ubicación tenga nunca más de un palet ni salidas de huecos vacíos.

Uso:  python generador/comprobar_datos.py [--datos carpeta] [--config ...]
Sale con código 1 si hay errores; los avisos no paran.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from configuracion import DATOS, argumentos, cargar, filas_muelles
from contrato import TABLAS, TIPOS_MOVIMIENTO, columnas, obligatorias

errores: list[str] = []
avisos: list[str] = []


def error(tabla: str, texto: str) -> None:
    errores.append(f"{tabla}: {texto}")


def aviso(tabla: str, texto: str) -> None:
    avisos.append(f"{tabla}: {texto}")


def ejemplos(serie, n: int = 5) -> str:
    vals = list(dict.fromkeys(map(str, serie)))
    return ", ".join(vals[:n]) + (f"… (+{len(vals) - n})" if len(vals) > n else "")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argumentos(__doc__.strip().splitlines()[0])
    p.add_argument("--datos", help="carpeta de los CSV (por defecto, datos/)")
    args = p.parse_args()
    cfg = cargar(args.config)
    carpeta = Path(args.datos) if args.datos else DATOS

    # ------------------------------------------------------------------ archivos y columnas
    t: dict[str, pd.DataFrame] = {}
    for tabla, (papel, _) in TABLAS.items():
        ruta = carpeta / f"{tabla}.csv"
        if not ruta.exists():
            error(tabla, f"falta {ruta.name}" + (" (puede ir solo con la cabecera)" if papel == "opcional" else ""))
            continue
        df = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        if list(df.columns) != columnas(tabla):
            falta = [c for c in columnas(tabla) if c not in df.columns]
            sobra = [c for c in df.columns if c not in columnas(tabla)]
            detalle = (f"faltan {falta}" if falta else "") + ("; " if falta and sobra else "") + (f"sobran {sobra}" if sobra else "")
            error(tabla, f"columnas distintas del contrato: {detalle or 'el orden no coincide'}")
        for c in obligatorias(tabla):
            if c in df.columns and len(df) and (df[c] == "").any() and papel != "opcional":
                error(tabla, f"{int((df[c] == '').sum())} filas sin «{c}», que es obligatoria")
        t[tabla] = df
    if any(n not in t for n in ("Ubicaciones", "Movimientos", "Productos", "Muelles", "Categorias")):
        return informe(carpeta)

    # ------------------------------------------------------------------ ubicaciones
    u = t["Ubicaciones"]
    if u["UbicacionID"].duplicated().any():
        error("Ubicaciones", f"UbicacionID repetidos: {ejemplos(u.loc[u.UbicacionID.duplicated(), 'UbicacionID'])}")
    fuera = sorted(set(u["Pasillo"]) - set(cfg.filas))
    if fuera:
        error("Ubicaciones", f"filas que no están en la configuración: {fuera}")
    sin_ubic = [f for f in cfg.filas if f not in set(u["Pasillo"])]
    if sin_ubic:
        aviso("Ubicaciones", f"filas de la configuración sin ubicaciones: {sin_ubic}")
    for col, tope in (("Hueco", cfg.huecos), ("Nivel", cfg.niveles), ("Posición", cfg.posiciones)):
        v = pd.to_numeric(u[col], errors="coerce")
        malos = u.loc[v.isna() | (v < 1) | (v > tope), "UbicacionID"]
        if len(malos):
            error("Ubicaciones", f"{col} fuera de 1…{tope} (config) en {len(malos)} ubicaciones: {ejemplos(malos)}")
    clave = u[["Pasillo", "Hueco", "Nivel", "Posición"]].astype(str).agg("-".join, axis=1)
    if clave.duplicated().any():
        error("Ubicaciones", f"dos ubicaciones en el mismo sitio (fila-hueco-nivel-posición): {ejemplos(clave[clave.duplicated()])}")
    if len(u) != cfg.capacidad:
        aviso("Ubicaciones", f"{len(u)} ubicaciones y la configuración da {cfg.capacidad}; los huecos sin ubicación se verán vacíos")
    orden = u["Pasillo"].map({f: str(i + 1) for i, f in enumerate(cfg.filas)})
    if (u["Orden pasillo"] != orden).any():
        error("Ubicaciones", "«Orden pasillo» no sigue el orden de estanterias.filas (completar_datos.py lo rellena)")
    if (u["ZonaID"] != u["Pasillo"].map(cfg.zona_de)).any():
        aviso("Ubicaciones", "ZonaID no coincide con las zonas de la configuración")

    # ------------------------------------------------------------------ productos y categorías
    pr, ca = t["Productos"], t["Categorias"]
    if pr["SKU"].duplicated().any():
        error("Productos", f"SKU repetidos: {ejemplos(pr.loc[pr.SKU.duplicated(), 'SKU'])}")
    sin_cat = sorted(set(pr["Categoría"]) - set(ca["Categoría"]))
    if sin_cat:
        error("Productos", f"categorías que no están en Categorias.csv: {sin_cat}")
    malas = sorted(set(pr["Clase ABC"]) - {"A", "B", "C"})
    if malas:
        error("Productos", f"Clase ABC debe ser A, B o C (hay {malas})")
    for c in ("Color", "Tono claro", "Tono oscuro"):
        mal = ca.loc[~ca[c].str.fullmatch(r"#[0-9A-Fa-f]{6}"), "Categoría"]
        if len(mal):
            error("Categorias", f"«{c}» no es #RRGGBB en: {ejemplos(mal)}")
    if ca["Categoría"].str.contains("|", regex=False).any():
        error("Categorias", "los nombres no pueden llevar «|»")

    # ------------------------------------------------------------------ muelles y camiones
    mu = t["Muelles"]
    esperados = [r["MuelleID"] for r in filas_muelles(cfg)]
    if list(mu["MuelleID"]) != esperados:
        error("Muelles", f"no coincide con la configuración: hay {list(mu['MuelleID'])}, se esperan {esperados}")
    if set(mu["Tipo"]) - {"Entrada", "Salida"}:
        error("Muelles", "Tipo debe ser Entrada o Salida")
    ca_ = t.get("Camiones")
    if ca_ is not None and len(ca_):
        otros = sorted(set(ca_["MuelleID"]) - set(mu["MuelleID"]))
        if otros:
            error("Camiones", f"muelles que no están en Muelles: {otros}")
        ini = pd.to_datetime(ca_["Inicio operación"], errors="coerce")
        fin = pd.to_datetime(ca_["Fin operación"], errors="coerce")
        if ini.isna().any() or fin.isna().any():
            error("Camiones", "hay horas de inicio o fin de operación que no se entienden (AAAA-MM-DD HH:MM:SS)")
        elif (fin < ini).any():
            error("Camiones", f"{int((fin < ini).sum())} camiones terminan antes de empezar")

    # ------------------------------------------------------------------ movimientos
    m = t["Movimientos"]
    m_t = pd.to_datetime(m["FechaHora"], errors="coerce")
    if m_t.isna().any():
        error("Movimientos", f"{int(m_t.isna().sum())} FechaHora que no se entienden (AAAA-MM-DD HH:MM:SS)")
    sig = pd.to_numeric(m["Signo"], errors="coerce")
    if not sig.isin([1, -1]).all():
        error("Movimientos", "Signo debe ser 1 (entra) o -1 (sale)")
    esperado = m["Tipo"].map(TIPOS_MOVIMIENTO)
    if ((esperado.notna()) & (esperado != sig)).any():
        error("Movimientos", "el Signo no cuadra con el Tipo (Entrada y Stock inicial = 1, Salida = -1)")
    otros = sorted(set(m["Tipo"]) - set(TIPOS_MOVIMIENTO))
    if otros:
        aviso("Movimientos", f"tipos que no cuentan como entrada ni salida: {otros}")
    for col, ref, tabla in (("UbicacionID", u["UbicacionID"], "Ubicaciones"), ("SKU", pr["SKU"], "Productos")):
        sueltos = m.loc[~m[col].isin(set(ref)), col]
        if len(sueltos):
            error("Movimientos", f"{len(sueltos)} filas con {col} que no está en {tabla}: {ejemplos(sueltos)}")
    con_muelle = m.loc[m["MuelleID"] != "", "MuelleID"]
    if len(set(con_muelle) - set(mu["MuelleID"])):
        error("Movimientos", f"muelles que no están en Muelles: {sorted(set(con_muelle) - set(mu['MuelleID']))}")
    if m["MovimientoID"].duplicated().any():
        error("Movimientos", "MovimientoID repetidos")
    if not m_t.isna().any() and sig.isin([1, -1]).all():
        # Ocupación de cada ubicación en el tiempo: siempre 0 o 1
        orden_mov = pd.DataFrame({"u": m["UbicacionID"], "t": m_t, "id": pd.to_numeric(m["MovimientoID"], errors="coerce"),
                                  "s": sig}).sort_values(["t", "id"], kind="stable")
        acum = orden_mov.groupby("u")["s"].cumsum()
        dobles, vacias = orden_mov.loc[acum > 1, "u"], orden_mov.loc[acum < 0, "u"]
        if len(dobles):
            error("Movimientos", f"ubicaciones con dos palets a la vez ({dobles.nunique()}): {ejemplos(dobles)}")
        if len(vacias):
            error("Movimientos", f"salidas de ubicaciones vacías ({vacias.nunique()}): {ejemplos(vacias)}")
        no_inicial = m["Tipo"] != "Stock inicial"
        fecha_ok = m.loc[no_inicial, "Fecha"] == m_t[no_inicial].dt.strftime("%Y-%m-%d")
        hora_ok = pd.to_numeric(m.loc[no_inicial, "Hora"], errors="coerce") == m_t[no_inicial].dt.hour
        if not (fecha_ok.all() and hora_ok.all()):
            error("Movimientos", "Fecha u Hora no cuadran con FechaHora (completar_datos.py las calcula)")

    # ------------------------------------------------------------------ calendario, ocupación y almacén
    cal = t.get("Calendario")
    if cal is not None:
        dias = set(cal["Fecha"])
        if cal["Fecha"].duplicated().any():
            error("Calendario", "fechas repetidas")
        for tabla, col in (("Movimientos", "Fecha"), ("Camiones", "Fecha"), ("OcupacionHoraria", "Fecha")):
            if tabla in t and len(t[tabla]):
                fuera = set(t[tabla][col]) - dias
                if fuera:
                    error(tabla, f"fechas que no están en el Calendario: {ejemplos(sorted(fuera))}")
    oh = t.get("OcupacionHoraria")
    pas = t.get("Pasillos")
    if oh is not None and pas is not None:
        if list(pas["Pasillo"]) != cfg.filas:
            error("Pasillos", f"deben ser las filas de la configuración, en orden: {cfg.filas}")
        cap = dict(zip(pas["Pasillo"], pd.to_numeric(pas["Capacidad (palets)"], errors="coerce")))
        excede = oh[pd.to_numeric(oh["Ocupadas"], errors="coerce") > oh["Pasillo"].map(cap)]
        if len(excede):
            error("OcupacionHoraria", f"{len(excede)} horas con más palets que capacidad en la fila")
    alm = t.get("Almacen")
    if alm is not None:
        if len(alm) != 1:
            error("Almacen", f"debe tener una sola fila (tiene {len(alm)})")
        elif cal is not None and alm["Fecha por defecto"].iloc[0] not in set(cal["Fecha"]):
            error("Almacen", f"la fecha por defecto {alm['Fecha por defecto'].iloc[0]} no está en el Calendario")

    # ------------------------------------------------------------------ resumen
    if not errores and len(m):
        ultima = m_t.max()
        def n(v: int) -> str:
            return f"{v:,}".replace(",", ".")
        print(f"Datos: {n(len(u))} ubicaciones en {len(cfg.filas)} filas, {n(len(m))} movimientos del "
              f"{m_t[m['Tipo'] != 'Stock inicial'].min():%d/%m/%Y} al {ultima:%d/%m/%Y}, {n(len(pr))} productos en "
              f"{len(ca)} categorías, {len(mu)} muelles.")
    informe(carpeta)


def informe(carpeta: Path) -> None:
    for a in avisos:
        print("aviso:", a)
    for e in errores:
        print("ERROR:", e)
    print(f"{carpeta}: {'correcto' if not errores else f'{len(errores)} errores'}"
          + (f", {len(avisos)} avisos" if avisos else ""))
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
