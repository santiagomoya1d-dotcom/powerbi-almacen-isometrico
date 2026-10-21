# -*- coding: utf-8 -*-
"""
Lee y valida almacen.config.json, el único sitio donde se describe el almacén.

Lo usan el simulador (generar_datos.py), la escena 3D (deneb/construir_escena.py), el generador de la
página (pagina_almacen.py) y las herramientas de datos reales (completar_datos.py, comprobar_datos.py).
Si algo de la configuración no cuadra, se para con la lista completa de problemas.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # carpeta Prj1_Almacen
CONFIG = RAIZ / "almacen.config.json"
DATOS = RAIZ / "datos"

MAX_FILAS = 18          # la escena reserva bandas de dibujo por encima de la 19 para playa, muelles y camiones
COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
TINTES_ZONA = ["#0E3B44", "#1A2A4A", "#2A1F45", "#3B2A16", "#123B26", "#3B1626"]


@dataclass
class Categoria:
    nombre: str
    nombre_corto: str
    color: str
    color_claro: str
    color_oscuro: str
    orden: int
    simulacion: dict = field(default_factory=dict)


@dataclass
class Zona:
    id: str
    nombre: str
    orden: int
    filas: list
    descripcion: str
    tinte: str


@dataclass
class Configuracion:
    ruta: Path
    nombre: str
    subtitulo: str
    etiqueta: str
    datos_ficticios: bool
    fecha_por_defecto: date | None
    nota_fecha: str
    filas: list                 # de la más cercana a los muelles a la más lejana
    huecos: int
    niveles: int
    posiciones: int
    zonas: list
    muelles_entrada: list
    muelles_salida: list
    primera_hora: int
    ultima_hora: int
    hora_por_defecto: int
    categorias: list
    simulacion: dict

    @property
    def capacidad(self) -> int:
        return len(self.filas) * self.huecos * self.niveles * self.posiciones

    @property
    def zona_de(self) -> dict:
        return {f: z.id for z in self.zonas for f in z.filas}

    @property
    def muelles(self) -> list:
        return self.muelles_entrada + self.muelles_salida


def _sin_comentarios(x):
    if isinstance(x, dict):
        return {k: _sin_comentarios(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, list):
        return [_sin_comentarios(v) for v in x]
    return x


def _mezcla(hex_color: str, con: tuple, t: float) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c + (o - c) * t):02X}" for c, o in zip((r, g, b), con))


def _fecha(texto, errores: list, donde: str) -> date | None:
    if texto in (None, ""):
        return None
    try:
        return date.fromisoformat(str(texto))
    except ValueError:
        errores.append(f"{donde}: «{texto}» no es una fecha AAAA-MM-DD")
        return None


def _rango_filas(filas: list) -> str:
    return f"Fila {filas[0]}" if len(filas) == 1 else f"Filas {filas[0]} a {filas[-1]}"


def cargar(ruta: str | Path | None = None) -> Configuracion:
    ruta = Path(ruta) if ruta else CONFIG
    if not ruta.exists():
        raise SystemExit(f"No encuentro la configuración: {ruta}")
    try:
        c = _sin_comentarios(json.loads(ruta.read_text(encoding="utf-8")))
    except json.JSONDecodeError as e:
        raise SystemExit(f"{ruta.name} no es un JSON válido: {e}")
    err: list[str] = []

    alm = c.get("almacen", {})
    est = c.get("estanterias", {})
    filas = [str(f) for f in est.get("filas", [])]
    if not filas:
        err.append("estanterias.filas: hace falta al menos una fila")
    if len(filas) > MAX_FILAS:
        err.append(f"estanterias.filas: como mucho {MAX_FILAS} filas (hay {len(filas)})")
    if len(set(filas)) != len(filas):
        err.append("estanterias.filas: hay nombres de fila repetidos")
    if any(f in ("Todo", "Todas") for f in filas):
        err.append("estanterias.filas: «Todo» y «Todas» están reservados para el selector de filas")
    limites = {"huecos_por_fila": (1, 40), "niveles": (1, 12), "palets_por_hueco": (1, 4)}
    medidas = {}
    for clave, (lo, hi) in limites.items():
        v = est.get(clave)
        if not isinstance(v, int) or not lo <= v <= hi:
            err.append(f"estanterias.{clave}: debe ser un entero entre {lo} y {hi} (es {v!r})")
            v = lo
        medidas[clave] = v

    # Zonas: si no se dan, un cuarto de las filas delante (alta rotación), la mitad en medio y el resto al fondo
    zonas_cfg = c.get("zonas")
    if not zonas_cfg and filas:
        n = len(filas)
        q = max(1, round(n / 4)) if n >= 3 else 1
        trozos = [filas[:q], filas[q:n - q], filas[n - q:]] if n >= 3 else [filas]
        nombres = ["Alta rotación", "Rotación media", "Reserva"]
        zonas_cfg = [{"id": f"Z{i + 1}", "nombre": nombres[i] if len(trozos) == 3 else "Almacén", "filas": t}
                     for i, t in enumerate(trozos) if t]
    zonas = []
    vistas: list[str] = []
    for i, z in enumerate(zonas_cfg or []):
        zf = [str(f) for f in z.get("filas", [])]
        fuera = [f for f in zf if f not in filas]
        if fuera:
            err.append(f"zonas.{z.get('id')}: filas que no existen en estanterias.filas: {fuera}")
        posiciones = sorted(filas.index(f) for f in zf if f in filas)
        if posiciones and posiciones != list(range(posiciones[0], posiciones[-1] + 1)):
            err.append(f"zonas.{z.get('id')}: sus filas deben ser consecutivas")
        vistas += zf
        orden = [filas[p] for p in posiciones]
        zonas.append(Zona(id=str(z.get("id", f"Z{i + 1}")), nombre=str(z.get("nombre", f"Zona {i + 1}")), orden=i + 1,
                          filas=orden, descripcion=z.get("descripcion") or (_rango_filas(orden) if orden else ""),
                          tinte=z.get("tinte") or TINTES_ZONA[i % len(TINTES_ZONA)]))
    if filas and sorted(vistas) != sorted(filas):
        sin = [f for f in filas if f not in vistas]
        dobles = sorted({f for f in vistas if vistas.count(f) > 1})
        if sin:
            err.append(f"zonas: filas sin zona: {sin}")
        if dobles:
            err.append(f"zonas: filas en más de una zona: {dobles}")

    def lista_muelles(valor, letra: str, donde: str) -> list:
        if isinstance(valor, int):
            return [f"{letra}{i + 1}" for i in range(valor)]
        if isinstance(valor, list) and all(isinstance(v, str) and v for v in valor):
            return list(valor)
        err.append(f"muelles.{donde}: pon un número o una lista de identificadores")
        return []

    mu = c.get("muelles", {})
    entrada = lista_muelles(mu.get("entrada", 6), "E", "entrada")
    salida = lista_muelles(mu.get("salida", 6), "S", "salida")
    if not entrada or not salida:
        err.append("muelles: hace falta al menos un muelle de entrada y uno de salida")
    if len(entrada) > 16 or len(salida) > 16:
        err.append("muelles: como mucho 16 de entrada y 16 de salida")
    if len(set(entrada + salida)) != len(entrada + salida):
        err.append("muelles: hay identificadores repetidos")
    if any("," in m for m in entrada + salida):
        err.append("muelles: los identificadores no pueden llevar comas")

    vista = c.get("vista", {})
    h0, h1 = vista.get("primera_hora", 6), vista.get("ultima_hora", 21)
    hd = vista.get("hora_por_defecto", 11)
    if not (isinstance(h0, int) and isinstance(h1, int) and 0 <= h0 <= h1 <= 23):
        err.append("vista: primera_hora y ultima_hora deben ser horas de 0 a 23, la primera antes que la última")
        h0, h1 = 0, 23
    if h1 - h0 + 1 > 24:
        err.append("vista: como mucho 24 horas")
    if not isinstance(hd, int) or not h0 <= hd <= h1:
        err.append(f"vista.hora_por_defecto: debe estar entre {h0} y {h1}")
        hd = h0

    categorias = []
    for i, k in enumerate(c.get("categorias", [])):
        nombre = str(k.get("nombre", "")).strip()
        if not nombre:
            err.append(f"categorias[{i}]: falta el nombre")
            continue
        if "|" in nombre:
            err.append(f"categorias.{nombre}: el nombre no puede llevar «|»")
        color = k.get("color", "")
        if not COLOR.match(str(color)):
            err.append(f"categorias.{nombre}: color «{color}» no es #RRGGBB")
            color = "#94A3B8"
        claro = k.get("color_claro") or _mezcla(color, (255, 255, 255), 0.45)
        oscuro = k.get("color_oscuro") or _mezcla(color, (0, 0, 0), 0.3)
        for t, v in (("color_claro", claro), ("color_oscuro", oscuro)):
            if not COLOR.match(str(v)):
                err.append(f"categorias.{nombre}: {t} «{v}» no es #RRGGBB")
        categorias.append(Categoria(nombre=nombre, nombre_corto=str(k.get("nombre_corto") or nombre),
                                    color=color.upper(), color_claro=str(claro).upper(), color_oscuro=str(oscuro).upper(),
                                    orden=i + 1, simulacion=k.get("simulacion", {})))
    if not categorias:
        err.append("categorias: hace falta al menos una categoría")
    if len({k.nombre for k in categorias}) != len(categorias):
        err.append("categorias: hay nombres repetidos")

    sim = c.get("simulacion", {})
    sim_inicio = _fecha(sim.get("inicio", "2025-10-01"), err, "simulacion.inicio")
    sim_fin = _fecha(sim.get("fin", "2026-09-30"), err, "simulacion.fin")
    if sim_inicio and sim_fin and sim_fin < sim_inicio:
        err.append("simulacion: fin es anterior a inicio")
    fecha_def = _fecha(alm.get("fecha_por_defecto"), err, "almacen.fecha_por_defecto")

    if err:
        raise SystemExit(f"La configuración {ruta.name} tiene problemas:\n  - " + "\n  - ".join(err))

    capacidad = len(filas) * medidas["huecos_por_fila"] * medidas["niveles"] * medidas["palets_por_hueco"]
    palets_dia = sim.get("palets_por_dia", "auto")
    sim = {
        "semilla": int(sim.get("semilla", 2026)),
        "inicio": sim_inicio,
        "fin": sim_fin,
        "palets_por_dia": capacidad * 160 / 1728 if palets_dia == "auto" else float(palets_dia),
        "palets_por_camion": int(sim.get("palets_por_camion", 33)),
        "calentamiento": int(sim.get("dias_de_calentamiento", 28)),
        "operarios": sim.get("operarios") or {"Mañana": {"Carretillero": 4, "Preparador": 3}, "Tarde": {"Preparador": 4}},
    }
    return Configuracion(
        ruta=ruta, nombre=str(alm.get("nombre", "Almacén")), subtitulo=str(alm.get("subtitulo", "")),
        etiqueta=str(alm.get("etiqueta", "")), datos_ficticios=bool(alm.get("datos_ficticios", False)),
        fecha_por_defecto=fecha_def, nota_fecha=str(alm.get("nota_fecha_por_defecto", "")),
        filas=filas, huecos=medidas["huecos_por_fila"], niveles=medidas["niveles"],
        posiciones=medidas["palets_por_hueco"], zonas=zonas, muelles_entrada=entrada, muelles_salida=salida,
        primera_hora=h0, ultima_hora=h1, hora_por_defecto=hd, categorias=categorias, simulacion=sim)


# ------------------------------------------------------------- tablas que salen de la configuración
def filas_muelles(cfg: Configuracion) -> list[dict]:
    return ([{"MuelleID": m, "Muelle": f"Muelle {m}", "Tipo": "Entrada", "Orden": i + 1}
             for i, m in enumerate(cfg.muelles_entrada)] +
            [{"MuelleID": m, "Muelle": f"Muelle {m}", "Tipo": "Salida", "Orden": len(cfg.muelles_entrada) + i + 1}
             for i, m in enumerate(cfg.muelles_salida)])


def filas_categorias(cfg: Configuracion) -> list[dict]:
    return [{"Categoría": k.nombre, "Nombre corto": k.nombre_corto, "Color": k.color, "Tono claro": k.color_claro,
             "Tono oscuro": k.color_oscuro, "Orden": k.orden} for k in cfg.categorias]


def filas_almacen(cfg: Configuracion) -> list[dict]:
    return [{"Nombre": cfg.nombre, "Subtítulo": cfg.subtitulo, "Etiqueta": cfg.etiqueta,
             "Datos ficticios": "Sí" if cfg.datos_ficticios else "No",
             "Fecha por defecto": cfg.fecha_por_defecto.isoformat() if cfg.fecha_por_defecto else "",
             "Nota de la fecha": cfg.nota_fecha}]


def escribir_csv(ruta: Path, filas: list[dict], columnas: list[str] | None = None) -> None:
    columnas = columnas or (list(filas[0]) if filas else [])
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, lineterminator="\n")
        w.writeheader()
        for fila in filas:
            w.writerow({k: fila.get(k) for k in columnas})


def escribir_tablas_de_configuracion(cfg: Configuracion, carpeta: Path) -> None:
    """Almacen.csv y Categorias.csv: el nombre, la fecha por defecto y los colores que lee el modelo."""
    escribir_csv(carpeta / "Almacen.csv", filas_almacen(cfg))
    escribir_csv(carpeta / "Categorias.csv", filas_categorias(cfg))


def actualizar_tablas_de_configuracion(cfg: Configuracion, carpeta: Path) -> None:
    """Como escribir_tablas_de_configuracion, pero conserva las categorías que ya estaban en Categorias.csv
    y no están en la configuración (las que completar_datos.py añadió con color automático)."""
    import pandas as pd
    filas = filas_categorias(cfg)
    previo = carpeta / "Categorias.csv"
    if previo.exists():
        nombres = {f["Categoría"] for f in filas}
        for r in pd.read_csv(previo, dtype=str, keep_default_na=False).to_dict("records"):
            if r["Categoría"] not in nombres:
                filas.append({**r, "Orden": len(filas) + 1})
    escribir_csv(carpeta / "Almacen.csv", filas_almacen(cfg))
    escribir_csv(carpeta / "Categorias.csv", filas)


def argumentos(descripcion: str, salida: str | None = None):
    """Argumentos comunes: --config (otra configuración) y, si se pide, --salida."""
    import argparse
    p = argparse.ArgumentParser(description=descripcion)
    p.add_argument("--config", help="ruta de la configuración (por defecto, almacen.config.json)")
    if salida:
        p.add_argument("--salida", help=salida)
    return p
