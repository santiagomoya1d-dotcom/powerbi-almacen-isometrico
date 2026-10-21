# -*- coding: utf-8 -*-
"""
Construye la especificación Vega del almacén isométrico (almacen_isometrico.vega.json).

La geometría fija (losa, muros, estanterías, marcas del suelo, muelles) se calcula aquí, en
coordenadas del mundo, y va incrustada en la especificación. Lo que depende de los datos
(palets, camiones, playa, carretillas, pilotos de muelle) lo monta Vega a partir del
conjunto «dataset» que le pasa Deneb desde Power BI.

Proyección isométrica 2:1:  px = ox + (x - y)·s     py = oy + ((x + y)/2 - z·ZF)·s
Caras visibles de cada caja: superior, derecha (plano x+dx) e izquierda (plano y+dy).
La luz viene de atrás a la derecha: superior clara, derecha media, izquierda oscura.

La disposición (filas, pasillos, muelles y tamaño del edificio) se calcula a partir de
almacen.config.json: no hay coordenadas escritas a mano para un almacén concreto.

Uso: python construir_escena.py [--config otra.config.json] [--salida otra.vega.json]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "generador"))
from configuracion import argumentos, cargar  # noqa: E402

ARGS = argumentos("Genera la especificación Vega del almacén isométrico.",
                  "ruta del .vega.json (por defecto, deneb/almacen_isometrico.vega.json)").parse_args()
CFG = cargar(ARGS.config)
SALIDA = Path(ARGS.salida) if ARGS.salida else Path(__file__).resolve().with_name("almacen_isometrico.vega.json")


def r3(v: float) -> float:
    return round(v, 3)


# ------------------------------------------------------------------ medidas (unidades de palet)
ZF = 1.05                      # escala vertical
X0 = 3.0                       # x donde empiezan las estanterías
HUECOS, NIVELES, POSICIONES = CFG.huecos, CFG.niveles, CFG.posiciones
BAY = r3(POSICIONES * 1.0 + 0.2)   # ancho de un hueco: un palet (0,88) por posición más holgura
LH = 1.05                      # altura entre niveles
FONDO_RACK = 1.1
ANCHO_PASILLO = 3.0
ALTO_RACK = r3((NIVELES - 1) * LH + 1.3)
ALTO_MURO = r3(max(8.2, ALTO_RACK + 1.65))
FIN_RACK = X0 + HUECOS * BAY
LUZ = (-0.2, 0.42)             # desplazamiento de la sombra por unidad de altura

# Filas de atrás (banda 1) hacia delante (junto a los muelles). Contando desde delante, las filas
# alternan «pos» (el pasillo de acceso queda delante, hacia los muelles) y «neg» (queda detrás),
# de modo que cada pareja pos/neg va espalda con espalda y cada pasillo da servicio a dos filas.
LADO = {f: "pos" if i % 2 == 0 else "neg" for i, f in enumerate(CFG.filas)}
FILAS, PASILLOS = [], []       # (pasillo, y inicial, lado) · (y0, y1, con paso de cebra)
y = 0.6
if LADO[CFG.filas[-1]] == "neg":                    # la fila del fondo necesita pasillo detrás
    PASILLOS.append((0.25, 2.6, False))
    y = 2.6
for f in reversed(CFG.filas):
    FILAS.append((f, r3(y), LADO[f]))
    fin = y + FONDO_RACK
    if LADO[f] == "pos":
        PASILLOS.append((r3(fin), r3(fin + ANCHO_PASILLO), True))
        y = fin + ANCHO_PASILLO
    else:
        y = fin + 0.15                                # espalda con espalda con la siguiente
YF = r3(y)                     # fin del pasillo delantero, donde empieza la playa
BANDA = {p: i + 1 for i, (p, _, _) in enumerate(FILAS)}
N_FILAS = len(FILAS)
Y_FILA = {p: y0 for p, y0, _ in FILAS}
ZONAS = [(z.id, z.tinte, min(Y_FILA[f] for f in z.filas), max(Y_FILA[f] for f in z.filas) + FONDO_RACK)
         for z in CFG.zonas if z.filas]

D = r3(YF + 4.3)               # fondo del edificio (muro de muelles)
D_PATIO = r3(D + 7.6)          # fin del patio de camiones
# Muelles de entrada desde la izquierda y de salida hacia la derecha, cada 3,25; el edificio se
# ensancha si no caben junto a las estanterías
PASO_MUELLE = 3.25
N_E, N_S = len(CFG.muelles_entrada), len(CFG.muelles_salida)
W = r3(max(FIN_RACK + 3.6, 12.5 + (N_E + N_S - 2) * PASO_MUELLE))   # ancho del edificio
MUELLES = [(m, r3(3.6 + i * PASO_MUELLE), True) for i, m in enumerate(CFG.muelles_entrada)] + \
          [(m, r3(W - 4.45 - (N_S - 1 - j) * PASO_MUELLE), False) for j, m in enumerate(CFG.muelles_salida)]
X_E0 = MUELLES[0][1]
X_S0 = MUELLES[N_E][1]

# --------------------------------------------------------------------- paleta
C = {
    "losa": ["#1C2536", "#111827", "#151D2C"],
    "patio": ["#141A25", "#0B1019", "#0E141F"],
    "muro": ["#3B475E", "#2B364A", "#212A3B"],
    "nervio": ["#46536C", "#334058", "#28334A"],
    "ventana": ["#4F79B0", "#3E679E", "#365C8F"],
    "puntal": ["#5A6D8C", "#435572", "#33425A"],
    "larguero": ["#FFA463", "#F4782F", "#C65A1D"],
    "protector": ["#FDE047", "#EAB308", "#A16207"],
    "hormigon": ["#5B6577", "#465062", "#384152"],
    "portico": ["#64748B", "#475569", "#334155"],
    "nivelador": ["#3F4A5C", "#323C4D", "#262F3E"],
    "carretilla": ["#FDE047", "#FACC15", "#CA8A04"],
    "oscuro": ["#4B5563", "#374151", "#1F2937"],
    "cargador": ["#2DD4BF", "#14B8A6", "#0F766E"],
}


def caja(x, y, z, dx, dy, dz, c, k, f="tdi", o=1.0, tipo="fijo"):
    r = lambda v: round(v, 3)
    return {"b": {"x": r(x), "y": r(y), "z": r(z), "dx": r(dx), "dy": r(dy), "dz": r(dz),
                  "c": c, "k": k, "f": f, "o": o}, "tipo": tipo}


def plano(pts, z=0.0, fill=None, op=1.0, st=None, sw=0.0, g=None, orden=0):
    return {"px": [round(p[0], 3) for p in pts], "py": [round(p[1], 3) for p in pts], "n": len(pts),
            "z": z, "fill": fill, "op": op, "st": st, "sw": sw, "g": g, "orden": orden}


def rect(x0, y0, x1, y1, **kw):
    return plano([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)


def sombra(x0, y0, x1, y1, h, op=0.3, orden=5):
    """Sombra de un prisma sobre el suelo: envolvente de la planta y su copia desplazada."""
    vx, vy = LUZ[0] * h, LUZ[1] * h
    # Con vx<0 y vy>0 la envolvente recorre estos seis vértices
    pts = [(x0, y0), (x1, y0), (x1, y1), (x1 + vx, y1 + vy), (x0 + vx, y1 + vy), (x0 + vx, y0 + vy)]
    return plano(pts, fill="#00040D", op=op, orden=orden)


def circulo(cx, cy, r, n=8, **kw):
    return plano([(cx + r * math.cos(2 * math.pi * i / n), cy + r * 0.62 * math.sin(2 * math.pi * i / n))
                  for i in range(n)], **kw)


base, fijas, planos, lineas, textos = [], [], [], [], []

# ------------------------------------------------------------------ losa y patio
base.append(caja(-0.35, -0.35, -0.9, W + 0.7, D + 0.65, 0.9, C["losa"], 0))
base.append(caja(-0.35, D + 0.3, -1.0, W + 0.7, D_PATIO - D - 0.3, 0.92, C["patio"], 1))

# ------------------------------------------------------------------ suelo
# Juntas del pavimento
for x in [i * 4.5 for i in range(1, math.ceil(W / 4.5))]:
    lineas.append({"a": [x, 0, 0], "b": [x, D, 0], "st": "#26324A", "sw": 0.05, "op": 0.7, "da": None})
for y in [i * 4.5 for i in range(1, math.ceil(D / 4.5))]:
    lineas.append({"a": [0, y, 0], "b": [W, y, 0], "st": "#26324A", "sw": 0.05, "op": 0.7, "da": None})
# Tinte de zonas bajo las estanterías
for _, color, y0, y1 in ZONAS:
    planos.append(rect(X0 - 0.5, y0 - 0.25, FIN_RACK + 0.5, y1 + 0.25, fill=color, op=0.55, orden=1))
# Pasillos: líneas amarillas a los lados y luz cenital
N_LUCES = max(1, int((FIN_RACK - X0 - 1.0) / 7.2))
for y0, y1, _ in PASILLOS:
    for yy in (y0 + 0.18, y1 - 0.18):
        planos.append(rect(X0 - 0.4, yy - 0.04, FIN_RACK + 0.4, yy + 0.04, fill="#EAB308", op=0.55, orden=3))
    for cx in [X0 + 4 + i * 7.2 for i in range(N_LUCES)]:
        planos.append(circulo(cx, (y0 + y1) / 2, 2.6, n=10, fill="luz", op=1, g="radial", orden=2))
# Pasillo peatonal junto al muro izquierdo
planos.append(rect(0.35, 0.3, 2.2, D - 0.5, fill="#22C55E", op=0.10, orden=2))
for xx in (0.35, 2.2):
    lineas.append({"a": [xx, 0.3, 0], "b": [xx, D - 0.5, 0], "st": "#22C55E", "sw": 0.07, "op": 0.6, "da": [6, 4]})
for y0, y1, _ in [p for p in PASILLOS if p[2]]:   # pasos de cebra en la boca de cada pasillo
    for i in range(5):
        yy = y0 + 0.5 + i * (y1 - y0 - 1.0) / 4
        planos.append(rect(0.5, yy - 0.12, 2.05, yy + 0.12, fill="#E5E7EB", op=0.35, orden=3))
# Carriles de playa delante de cada muelle y niveladores
for mid, mx, entrada in MUELLES:
    tono = "#14B8A6" if entrada else "#F43F5E"
    planos.append(rect(mx - 1.2, YF + 0.2, mx + 1.2, D - 1.3, fill=tono, op=0.09, st=tono, sw=0.05, orden=2))
    planos.append(rect(mx - 1.2, D - 1.15, mx + 1.2, D - 0.05, fill="#2A3344", op=1, orden=3))
    for i in range(6):   # franja de seguridad amarilla y negra en el borde del nivelador
        planos.append(rect(mx - 1.2 + i * 0.4, D - 1.15, mx - 1.0 + i * 0.4, D - 0.95, fill="#EAB308", op=0.9, orden=4))
# Calle transversal delantera: línea discontinua central
lineas.append({"a": [X0 - 0.4, YF - 1.5, 0], "b": [FIN_RACK + 0.4, YF - 1.5, 0], "st": "#E5E7EB", "sw": 0.06, "op": 0.35, "da": [10, 8]})
# Zona de carga de baterías a la derecha
FIN_BATERIAS = min(12.5, YF - 1.0)
planos.append(rect(W - 2.6, 3.0, W - 0.4, FIN_BATERIAS, fill="#14B8A6", op=0.08, st="#14B8A6", sw=0.05, orden=2))

# Patio: plazas de cada muelle
for mid, mx, entrada in MUELLES:
    for xx in (mx - 1.55, mx + 1.55):
        lineas.append({"a": [xx, D + 0.6, -0.08], "b": [xx, D + 7.0, -0.08], "st": "#CBD5E1", "sw": 0.06, "op": 0.35, "da": None})
lineas.append({"a": [0.5, D_PATIO - 0.4, -0.08], "b": [W - 0.5, D_PATIO - 0.4, -0.08], "st": "#EAB308", "sw": 0.07, "op": 0.5, "da": [12, 8]})

# Sombras de muros y estanterías
planos.append(sombra(0, -0.35, W, 0, ALTO_MURO * 0.35, op=0.35, orden=5))
for p, y0, _ in FILAS:
    planos.append(sombra(X0 - 0.1, y0, FIN_RACK + 0.1, y0 + FONDO_RACK, ALTO_RACK, op=0.22, orden=5))

# ------------------------------------------------------------------ muros
K0 = 0
fijas.append(caja(-0.35, -0.35, 0, W + 0.35, 0.35, ALTO_MURO, C["muro"], K0 + 1))
fijas.append(caja(-0.35, 0, 0, 0.35, D, ALTO_MURO, C["muro"], K0 + 0))
for i in range(1, int(W / 1.6)):
    x = i * 1.6
    fijas.append(caja(x, 0, 0, 0.07, 0.07, ALTO_MURO - 0.25, C["nervio"], K0 + 10 + x))
    if i < int(W / 1.6) - 1:
        fijas.append(caja(x + 0.12, 0.02, ALTO_MURO - 1.85, 1.42, 0, 0.95, C["ventana"], K0 + 10.5 + x, f="i", o=0.75))
for j in range(1, int(D / 1.6)):
    y = j * 1.6
    fijas.append(caja(0, y, 0, 0.07, 0.07, ALTO_MURO - 0.25, C["nervio"], K0 + 5 - y / 100))
    fijas.append(caja(0.02, y + 0.12, ALTO_MURO - 1.85, 0, 1.42, 0.95, C["ventana"], K0 + 5.5 - y / 100, f="d", o=0.75))

# ------------------------------------------------------------------ estanterías
for p, y0, lado in FILAS:
    kb = BANDA[p] * 1e7
    y1 = y0 + FONDO_RACK
    for i in range(HUECOS + 1):
        b = X0 + i * BAY
        fijas.append(caja(b - 0.06, y0, 0, 0.12, 0.1, ALTO_RACK, C["puntal"], kb + b * 10))
        fijas.append(caja(b - 0.06, y1 - 0.1, 0, 0.12, 0.1, ALTO_RACK, C["puntal"], kb + 9e6 + b * 10))
    for b in (X0, FIN_RACK):   # travesaños del bastidor de cabecera
        for zz in [r3(0.6 + 1.7 * i) for i in range(int((ALTO_RACK - 1.1) / 1.7) + 1)]:
            fijas.append(caja(b - 0.04, y0 + 0.1, zz, 0.08, FONDO_RACK - 0.2, 0.06, C["puntal"], kb + 9e6 + b * 10 + 1))
    for yy in (y0 - 0.12, y1 - 0.1):   # protectores amarillos de cabecera
        fijas.append(caja(X0 - 0.3, yy, 0, 0.42, 0.22, 0.55, C["protector"], kb + (9e6 if yy > y0 else -1) + 5))
    for n in range(2, NIVELES + 1):
        zt = (n - 1) * LH
        fijas.append(caja(X0 - 0.06, y0, zt - 0.13, FIN_RACK - X0 + 0.12, 0.1, 0.13, C["larguero"], kb + n * 1e5 + 100))
        fijas.append(caja(X0 - 0.06, y1 - 0.1, zt - 0.13, FIN_RACK - X0 + 0.12, 0.1, 0.13, C["larguero"], kb + n * 1e5 + 90000))

# ------------------------------------------------------------------ muro de muelles y pórticos
KM = 2.5e8
tramos, x_ant = [], -0.35
for mid, mx, entrada in sorted(MUELLES, key=lambda m: m[1]):
    tramos.append((x_ant, mx - 1.25))
    x_ant = mx + 1.25
tramos.append((x_ant, W))
for xa, xb in tramos:
    fijas.append(caja(xa, D, 0, xb - xa, 0.3, 1.0, C["hormigon"], KM + xa * 10))
for mid, mx, entrada in MUELLES:
    for xp in (mx - 1.32, mx + 1.17):
        fijas.append(caja(xp, D, 0, 0.15, 0.3, 3.3, C["portico"], KM + xp * 10 + 1))
    fijas.append(caja(mx - 1.32, D, 3.0, 2.64, 0.3, 0.35, C["portico"], KM + mx * 10 + 2))
    fijas.append(caja(mx - 1.2, D + 0.3, 0, 0.25, 0.18, 0.55, C["oscuro"], KM + mx * 10 + 3))   # topes de goma
    fijas.append(caja(mx + 0.95, D + 0.3, 0, 0.25, 0.18, 0.55, C["oscuro"], KM + mx * 10 + 3))

# Cargadores de baterías y dos carretillas cargando
for yy in [v for v in (4.0, 7.0, 10.0) if v + 0.8 <= FIN_BATERIAS]:
    fijas.append(caja(W - 0.8, yy, 0, 0.5, 0.8, 1.4, C["cargador"], 1.5e7 + yy))

# ------------------------------------------------------------------ textos fijos
# (Los nombres de zona no se pintan en el muro: chocaban con las etiquetas de ocupación de cada fila)
textos.append({"x": r3(X_E0 + 0.4), "y": r3(YF - 0.75), "z": 0, "t": "PLAYA DE ENTRADA", "sz": 0.5, "ang": 26.57,
               "col": "#5EEAD4", "op": 0.75, "w": "bold", "al": "left"})
textos.append({"x": r3(X_S0 + 0.3), "y": r3(YF - 0.75), "z": 0, "t": "PLAYA DE SALIDA", "sz": 0.5, "ang": 26.57,
               "col": "#FDA4AF", "op": 0.75, "w": "bold", "al": "left"})
textos.append({"x": r3(W - 2.4), "y": 2.6, "z": 0, "t": "CARGA DE BATERÍAS", "sz": 0.42, "ang": -26.57,
               "col": "#5EEAD4", "op": 0.6, "w": "normal", "al": "left"})
for mid, mx, entrada in MUELLES:
    textos.append({"x": mx, "y": D + 0.3, "z": 3.95, "t": mid, "sz": 0.5, "ang": 0,
                   "col": "#E2E8F0", "op": 0.9, "w": "bold", "al": "center"})


# ------------------------------------------------------------------ encuadre
def esquinas(bx):
    b = bx["b"]
    for x in (b["x"], b["x"] + b["dx"]):
        for y in (b["y"], b["y"] + b["dy"]):
            for z in (b["z"], b["z"] + b["dz"]):
                yield x, y, z


pts = [p for bx in base + fijas for p in esquinas(bx)]
pts += [(W, D_PATIO, 0), (0, D_PATIO, 0)]
us = [x - y for x, y, z in pts]
vs = [(x + y) / 2 - z * ZF for x, y, z in pts]
U0, U1, V0, V1 = min(us) - 0.6, max(us) + 0.6, min(vs) - 1.2, max(vs) + 1.6
DU, DV = U1 - U0, V1 - V0


# ------------------------------------------------------------------ expresiones Vega
def pxy(x, y, z):
    """Expresión del punto proyectado como 'x,y'."""
    return f"(ox + (({x}) - ({y})) * s) + ',' + (oy + ((({x}) + ({y})) / 2 - ({z}) * {ZF}) * s)"


def obj(**campos):
    return "{" + ", ".join(f"{k}: {v}" for k, v in campos.items()) + "}"


def arr(colores):
    return "[" + ", ".join(f"'{c}'" for c in colores) + "]"


# Paletas por modo de color: [superior, derecha, izquierda]. Las de categoría no están aquí: llegan
# de los datos (medida «Paleta de categorías», tabla Categorías del modelo).
ABC = {"A": ["#7AF0DC", "#2BC8B2", "#159A89"], "B": ["#B4C0FF", "#7C8CF6", "#5865D6"],
       "C": ["#F3B5FF", "#D57BEA", "#A855C7"]}
DIAS = [["#7AF0DC", "#2BC8B2", "#159A89"], ["#FDE68A", "#FBBF24", "#C98A0B"], ["#FDA4AF", "#F43F5E", "#BE123C"]]
FANTASMA = ["#94A3B8", "#64748B", "#475569"]
MADERA = ["#C99B62", "#A77A46", "#7C5831"]

expr_tono = (
    "modo == 'dias' ? (datum.dias < 7 ? " + arr(DIAS[0]) + " : datum.dias <= 21 ? " + arr(DIAS[1]) + " : " + arr(DIAS[2]) + ")"
    " : modo == 'categoria' ? (datum.tonosCat || " + arr(FANTASMA) + ")"
    " : (datum.clase == 'A' ? " + arr(ABC["A"]) + " : datum.clase == 'B' ? " + arr(ABC["B"]) + " : " + arr(ABC["C"]) + ")"
)

# Partes de un palet en estantería, en coordenadas absolutas a partir de sx (x del hueco), y0, z0
K_PALET = "datum.banda * 1e7 + datum.Nivel * 1e5 + 1000 + datum.sx * 100"
expr_partes_palet = (
    "datum.estado == 'ocupada' ? ["
    + obj(x="datum.sx + 0.06", y="datum.y0 + 0.08", z="datum.z0", dx="0.88", dy="0.94", dz="0.14",
          c=arr(MADERA), k=K_PALET, f="'tdi'", o="1", p="'base'") + ", "
    + obj(x="datum.sx + 0.16", y="datum.y0 + 1.02", z="datum.z0 + 0.03", dx="0.2", dy="0", dz="0.08",
          c="['#2B1D10', '#2B1D10', '#2B1D10']", k=K_PALET + " + 1", f="'i'", o="1", p="'hueco'") + ", "
    + obj(x="datum.sx + 0.58", y="datum.y0 + 1.02", z="datum.z0 + 0.03", dx="0.2", dy="0", dz="0.08",
          c="['#2B1D10', '#2B1D10', '#2B1D10']", k=K_PALET + " + 1", f="'i'", o="1", p="'hueco'") + ", "
    + obj(x="datum.sx + 0.1", y="datum.y0 + 0.12", z="datum.z0 + 0.14", dx="0.8", dy="0.86", dz="datum.alto",
          c="datum.tono", k=K_PALET + " + 2", f="'tdi'", o="1", p="'carga'")
    + "] : ["
    + obj(x="datum.sx + 0.1", y="datum.y0 + 0.12", z="datum.z0 + 0.14", dx="0.8", dy="0.86", dz="datum.alto",
          c=arr(FANTASMA), k=K_PALET + " + 2", f="'tdi'", o="0.1", p="'fantasma'")
    + "]"
)

# Camión atracado en el muelle (mx = centro de la puerta)
K_CAMION = "3e8 + datum.X * 100"
expr_partes_camion = "[" + ", ".join([
    obj(x="datum.X - 1.05", y=f"{D + 4.0}", z="0", dx="2.1", dy="1.15", dz="0.6", c="['#1E293B', '#111827', '#0B1220']", k=K_CAMION + " + 0", f="'tdi'", o="1", p="'rueda'"),
    obj(x="datum.X - 1.15", y=f"{D + 0.25}", z="0.6", dx="2.3", dy="5.5", dz="2.7", c="['#F1F5F9', '#D5DCE6', '#A9B4C4']", k=K_CAMION + " + 1", f="'tdi'", o="1", p="'remolque'"),
    obj(x="datum.X + 1.15", y=f"{D + 0.7}", z="1.25", dx="0", dy="4.6", dz="0.38", c="datum.franja", k=K_CAMION + " + 2", f="'d'", o="1", p="'franja'"),
    obj(x="datum.X - 1.0", y=f"{D + 6.05}", z="0", dx="2.0", dy="0.95", dz="0.45", c="['#1E293B', '#111827', '#0B1220']", k=K_CAMION + " + 3", f="'tdi'", o="1", p="'rueda'"),
    obj(x="datum.X - 1.05", y=f"{D + 5.85}", z="0.4", dx="2.1", dy="1.5", dz="2.2", c="datum.cabina", k=K_CAMION + " + 4", f="'tdi'", o="1", p="'cabina'"),
    obj(x="datum.X - 0.85", y=f"{D + 7.35}", z="1.45", dx="1.7", dy="0", dz="0.8", c="['#1E3A5F', '#1E3A5F', '#1E3A5F']", k=K_CAMION + " + 5", f="'i'", o="1", p="'luna'"),
    obj(x="datum.X - 0.95", y=f"{D + 7.35}", z="0.55", dx="0.32", dy="0", dz="0.18", c="['#FEF3C7', '#FEF3C7', '#FEF3C7']", k=K_CAMION + " + 6", f="'i'", o="1", p="'faro'"),
    obj(x="datum.X + 0.63", y=f"{D + 7.35}", z="0.55", dx="0.32", dy="0", dz="0.18", c="['#FEF3C7', '#FEF3C7', '#FEF3C7']", k=K_CAMION + " + 6", f="'i'", o="1", p="'faro'"),
]) + "]"


# Carretilla elevadora en coordenadas locales (horquillas hacia -y local); sg = 1 o -1 según lado
def parte_local(lx, ly, lz, ldx, ldy, ldz, col, orden, nombre):
    y_expr = f"(datum.sg > 0 ? datum.yc + ({ly}) : datum.yc - ({ly}) - ({ldy}))"
    return obj(x=f"datum.xc + ({lx})", y=y_expr, z=str(lz), dx=str(ldx), dy=str(ldy), dz=str(ldz), c=arr(col),
               k=f"datum.kb + (datum.xc + datum.yc) * 1000 + {orden}", f="'tdi'", o="1", p=f"'{nombre}'")


expr_partes_carretilla = "[" + ", ".join([
    parte_local(-0.32, -1.05, 0.04, 0.64, 0.62, 0.06, C["oscuro"], 0, "horquilla"),
    parte_local(-0.42, -0.46, 0, 0.84, 0.13, 2.15, C["oscuro"], 1, "mastil"),
    parte_local(-0.45, -0.33, 0.12, 0.9, 1.0, 0.72, C["carretilla"], 2, "cuerpo"),
    parte_local(-0.45, 0.67, 0.12, 0.9, 0.26, 0.98, ["#FACC15", "#CA8A04", "#A16207"], 3, "contrapeso"),
    parte_local(-0.43, -0.28, 0.84, 0.06, 0.06, 1.05, C["oscuro"], 4, "poste"),
    parte_local(0.37, -0.28, 0.84, 0.06, 0.06, 1.05, C["oscuro"], 4, "poste"),
    parte_local(-0.43, 0.6, 0.84, 0.06, 0.06, 1.05, C["oscuro"], 4, "poste"),
    parte_local(0.37, 0.6, 0.84, 0.06, 0.06, 1.05, C["oscuro"], 4, "poste"),
    parte_local(-0.47, -0.3, 1.88, 0.94, 0.96, 0.06, C["oscuro"], 5, "techo"),
]) + "]"

# Palets de playa: dos columnas por tres filas en cada carril; datum.mx = centro del carril
Y_PLAYA = r3(YF + 0.35)
expr_partes_playa = "[" + ", ".join([
    obj(x="datum.mx - 1.02 + datum.col * 1.1", y=f"{Y_PLAYA} + datum.fila * 1.05", z="0", dx="0.88", dy="0.9", dz="0.14",
        c=arr(MADERA), k=f"2e8 + ({Y_PLAYA} + datum.fila * 1.05) * 1000 + (datum.mx + datum.col) * 10", f="'tdi'", o="1", p="'base'"),
    obj(x="datum.mx - 0.98 + datum.col * 1.1", y=f"{r3(Y_PLAYA + 0.04)} + datum.fila * 1.05", z="0.14", dx="0.8", dy="0.82", dz="0.66",
        c="datum.entrada ? ['#E8C995', '#CDA56C', '#A27F4B'] : ['#EEF3F9', '#CDD6E2', '#A9B6C8']",
        k=f"2e8 + ({Y_PLAYA} + datum.fila * 1.05) * 1000 + (datum.mx + datum.col) * 10 + 1", f="'tdi'", o="1", p="'cargaPlaya'"),
]) + "]"
CAP_E, CAP_S = 6 * N_E, 6 * N_S          # seis palets por carril de playa
IDS_E = "[" + ", ".join(f"'{m}'" for m in CFG.muelles_entrada) + "]"
IDS_S = "[" + ", ".join(f"'{m}'" for m in CFG.muelles_salida) + "]"

# ------------------------------------------------------------------ especificación
muelles_vals = [{"id": m, "X": x, "entrada": e} for m, x, e in MUELLES]
filas_vals = [{"Pasillo": p, "y0": y0, "banda": BANDA[p], "lado": lado} for p, y0, lado in FILAS]

campos_caja = [
    ("ax", "ox + (B.x - B.y) * s"), ("ay", f"oy + ((B.x + B.y) / 2 - (B.z + B.dz) * {ZF}) * s"),
    ("bx", "ox + (B.x + B.dx - B.y) * s"), ("by", f"oy + ((B.x + B.dx + B.y) / 2 - (B.z + B.dz) * {ZF}) * s"),
    ("cx", "ox + (B.x + B.dx - B.y - B.dy) * s"), ("cy", f"oy + ((B.x + B.dx + B.y + B.dy) / 2 - (B.z + B.dz) * {ZF}) * s"),
    ("qx", "ox + (B.x - B.y - B.dy) * s"), ("qy", f"oy + ((B.x + B.y + B.dy) / 2 - (B.z + B.dz) * {ZF}) * s"),
    ("h", f"B.dz * {ZF} * s"),
]
trans_caja = [{"type": "formula", "as": a, "expr": e.replace("B.", "datum.b.")} for a, e in campos_caja]
trans_caras = [
    {"type": "formula", "as": "lados", "expr": "[0, 1, 2]"},
    {"type": "flatten", "fields": ["lados"], "as": ["cara"]},
    {"type": "filter", "expr": "indexof(datum.b.f, datum.cara == 0 ? 'i' : datum.cara == 1 ? 'd' : 't') >= 0"},
    {"type": "formula", "as": "trazo", "expr":
        "datum.cara == 0 ? 'M' + datum.qx + ',' + (datum.qy + datum.h) + 'L' + datum.cx + ',' + (datum.cy + datum.h) + 'L' + datum.cx + ',' + datum.cy + 'L' + datum.qx + ',' + datum.qy + 'Z'"
        " : datum.cara == 1 ? 'M' + datum.bx + ',' + (datum.by + datum.h) + 'L' + datum.cx + ',' + (datum.cy + datum.h) + 'L' + datum.cx + ',' + datum.cy + 'L' + datum.bx + ',' + datum.by + 'Z'"
        " : 'M' + datum.ax + ',' + datum.ay + 'L' + datum.bx + ',' + datum.by + 'L' + datum.cx + ',' + datum.cy + 'L' + datum.qx + ',' + datum.qy + 'Z'"},
    {"type": "formula", "as": "relleno", "expr": "datum.cara == 2 ? datum.b.c[0] : datum.cara == 1 ? datum.b.c[1] : datum.b.c[2]"},
    {"type": "collect", "sort": {"field": ["b.k", "cara"]}},
]


def marca_caras(nombre, datos, interactiva=False):
    enc = {
        "path": {"field": "trazo"},
        "fill": {"field": "relleno"},
        "fillOpacity": {"field": "b.o"},
        "stroke": {"value": "rgba(3,7,18,0.35)"},
        "strokeWidth": {"value": 0.35},
    }
    if interactiva:
        # «encima» vale null sin nada señalado: se comprueba antes de comparar (null == undefined es verdadero)
        señalado = "(datum.p == 'carga' || datum.p == 'cargaPlaya') && encima != null && datum.id == encima"
        enc["stroke"] = {"signal": f"{señalado} ? '#FFFFFF' : datum.p == 'carga' && datum.activo && datum.cara == 2 ? '#FDE68A' : (datum.p == 'carga' || datum.p == 'cargaPlaya') && datum.cara == 2 ? 'rgba(255,255,255,0.22)' : datum.b.o < 1 ? 'transparent' : 'rgba(3,7,18,0.35)'"}
        enc["strokeWidth"] = {"signal": f"({señalado}) || (datum.p == 'carga' && datum.activo && datum.cara == 2) ? 1.6 : 0.4"}
        enc["cursor"] = {"signal": "datum.p == 'carga' || datum.p == 'cargaPlaya' ? 'pointer' : 'default'"}
        enc["tooltip"] = {"signal": "datum.p == 'carga' ? {'Ubicación': datum.id, 'Producto': datum.producto, 'Categoría': datum.categoria, 'Clase ABC': datum.clase, 'Días en stock': datum.dias, 'Movimientos en esta hora': datum.mov}"
                                    " : datum.p == 'cargaPlaya' ? {'Zona': datum.zona, 'Estado': datum.situacion, 'Palet': datum.numero} : null"}
    return {"type": "path", "name": nombre, "from": {"data": datos}, "encode": {"update": enc}}


puntos_plano = " + ".join(
    [f"(datum.n > {i} ? '{'M' if i == 0 else 'L'}' + (ox + (datum.px[{i}] - datum.py[{i}]) * s) + ',' + "
     f"(oy + ((datum.px[{i}] + datum.py[{i}]) / 2 - datum.z * {ZF}) * s) : '')" for i in range(10)]) + " + 'Z'"

spec = {
    "$schema": "https://vega.github.io/schema/vega/v5.json",
    "description": f"{CFG.nombre}: almacén isométrico. Generado por deneb/construir_escena.py a partir de {CFG.ruta.name}: no editar a mano.",
    "background": "transparent",
    "padding": 0,
    "autosize": "none",
    "signals": [
        {"name": "modo", "update": "length(data('dataset')) && data('dataset')[0]['Modo de color'] ? data('dataset')[0]['Modo de color'] : 'abc'"},
        {"name": "s", "update": f"max(1, min(width / {DU:.2f}, height / {DV:.2f}))"},
        {"name": "ox", "update": f"(width - {DU:.2f} * s) / 2 - ({U0:.2f}) * s"},
        {"name": "oy", "update": f"(height - {DV:.2f} * s) / 2 - ({V0:.2f}) * s"},
        {"name": "muelles", "update": "length(data('dataset')) && data('dataset')[0]['Muelles con camión'] ? split(data('dataset')[0]['Muelles con camión'], ',') : []"},
        {"name": "nEntrada", "update": f"length(data('dataset')) ? min({CAP_E}, data('dataset')[0]['Entradas en la hora'] || 0) : 0"},
        {"name": "nSalida", "update": f"length(data('dataset')) ? min({CAP_S}, data('dataset')[0]['Salidas en la hora'] || 0) : 0"},
        # Categorías y sus tres tonos, en un texto «#claro,#medio,#oscuroNombre|…» (medida Paleta de categorías)
        {"name": "paletaCat", "update": "length(data('dataset')) && data('dataset')[0]['Paleta de categorías'] ? data('dataset')[0]['Paleta de categorías'] : ''"},
        {"name": "foco", "update": "length(data('dataset')) && data('dataset')[0]['Fila en foco'] ? data('dataset')[0]['Fila en foco'] : 'Todas'"},
        {"name": "bandaFoco", "update": "foco == 'Todas' ? 99 : indexof(" + json.dumps([p for p, _, _ in FILAS]).replace('"', "'") + ", foco) + 1"},
        {"name": "encima", "value": None, "on": [
            {"events": "@mundo:mouseover", "update": "datum.p == 'carga' || datum.p == 'cargaPlaya' ? datum.id : null"},
            {"events": "@mundo:mouseout", "update": "null"}]},
    ],
    "data": [
        {"name": "dataset"},
        {"name": "filas", "values": filas_vals},
        {"name": "categorias", "values": [{}], "transform": [
            {"type": "formula", "as": "lista", "expr": "paletaCat ? split(paletaCat, '|') : []"},
            {"type": "flatten", "fields": ["lista"], "as": ["item"]},
            {"type": "formula", "as": "tonos", "expr": "split(substring(datum.item, 0, 23), ',')"},
            {"type": "formula", "as": "categoria", "expr": "substring(datum.item, 23)"},
        ]},
        {"name": "puertas", "values": muelles_vals, "transform": [
            {"type": "formula", "as": "ocupado", "expr": "indexof(muelles, datum.id) >= 0"}]},
        {"name": "huecos", "source": "dataset", "transform": [
            {"type": "lookup", "from": "filas", "key": "Pasillo", "fields": ["Pasillo"], "values": ["y0", "banda", "lado"]},
            {"type": "formula", "as": "estado", "expr": "datum['Palets en stock'] == 1 ? 'ocupada' : datum['Ocupada sin filtros'] == 1 ? 'atenuada' : 'libre'"},
            {"type": "formula", "as": "mov", "expr": "datum['Actividad en la hora'] || 0"},
            {"type": "formula", "as": "activo", "expr": "datum.mov > 0"},
            {"type": "formula", "as": "sx", "expr": f"{X0} + (datum.Hueco - 1) * {BAY} + 0.1 + (datum['Posición'] - 1) * 1.0"},
            {"type": "formula", "as": "z0", "expr": f"(datum.Nivel - 1) * {LH}"},
        ]},
        {"name": "palet", "source": "huecos", "transform": [
            {"type": "filter", "expr": "datum.estado != 'libre'"},
            {"type": "project", "fields": ["UbicacionID", "Nivel", "sx", "y0", "z0", "banda", "estado", "activo", "mov",
                                           "Producto en ubicación", "Clase ABC en ubicación", "Categoría en ubicación", "Días en stock",
                                           "Hueco", "Posición"],
             "as": ["id", "Nivel", "sx", "y0", "z0", "banda", "estado", "activo", "mov", "producto", "clase", "categoria", "dias",
                    "Hueco", "pos"]},
            {"type": "lookup", "from": "categorias", "key": "categoria", "fields": ["categoria"], "values": ["tonos"],
             "as": ["tonosCat"]},
            {"type": "formula", "as": "alto", "expr": "(datum.clase == 'A' ? 0.7 : datum.clase == 'B' ? 0.63 : 0.56) - ((datum.Hueco * 7 + datum.pos * 13 + datum.Nivel * 5) % 4) * 0.025"},
            {"type": "formula", "as": "tono", "expr": expr_tono},
            {"type": "formula", "as": "partes", "expr": expr_partes_palet},
            {"type": "flatten", "fields": ["partes"], "as": ["b"]},
            {"type": "formula", "as": "p", "expr": "datum.b.p"},
        ]},
        {"name": "carretillas", "source": "huecos", "transform": [
            {"type": "filter", "expr": "datum.activo"},
            {"type": "formula", "as": "azar", "expr": "(datum.Hueco * 37 + datum.Nivel * 11 + datum.banda * 7) % 23"},
            {"type": "window", "sort": {"field": "azar"}, "ops": ["row_number"], "as": ["orden"], "groupby": ["Pasillo"]},
            {"type": "filter", "expr": "datum.orden == 1"},
            {"type": "formula", "as": "sg", "expr": "datum.lado == 'pos' ? 1 : -1"},
            {"type": "formula", "as": "xc", "expr": "datum.sx + 0.5"},
            {"type": "formula", "as": "yc", "expr": f"datum.lado == 'pos' ? datum.y0 + {FONDO_RACK} + 1.55 : datum.y0 - 1.55"},
            {"type": "formula", "as": "kb", "expr": "(datum.lado == 'pos' ? datum.banda : datum.banda - 1) * 1e7 + 9.5e6"},
            {"type": "project", "fields": ["xc", "yc", "sg", "kb"]},
            {"type": "formula", "as": "partes", "expr": expr_partes_carretilla},
            {"type": "flatten", "fields": ["partes"], "as": ["b"]},
            {"type": "formula", "as": "p", "expr": "datum.b.p"},
        ]},
        {"name": "camiones", "source": "puertas", "transform": [
            {"type": "filter", "expr": "datum.ocupado"},
            {"type": "formula", "as": "franja", "expr": "datum.entrada ? ['#2DD4BF', '#2DD4BF', '#2DD4BF'] : ['#F43F5E', '#F43F5E', '#F43F5E']"},
            {"type": "formula", "as": "cabina", "expr": "datum.entrada ? ['#5EEAD4', '#14B8A6', '#0F766E'] : ['#FDA4AF', '#F43F5E', '#BE123C']"},
            {"type": "formula", "as": "partes", "expr": expr_partes_camion},
            {"type": "flatten", "fields": ["partes"], "as": ["b"]},
            {"type": "formula", "as": "p", "expr": "datum.b.p"},
        ]},
        {"name": "pilotos", "source": "puertas", "transform": [
            {"type": "formula", "as": "b", "expr": obj(x="datum.X - 0.2", y=f"{D + 0.3}", z="3.38", dx="0.4", dy="0.05", dz="0.22",
                                                       c="datum.ocupado ? ['#FCA5A5', '#EF4444', '#B91C1C'] : ['#86EFAC', '#22C55E', '#15803D']",
                                                       k=f"{2.6e8} + datum.X * 10", f="'tdi'", o="1", p="'piloto'")},
        ]},
        {"name": "playa", "transform": [
            {"type": "sequence", "start": 0, "stop": CAP_E + CAP_S, "as": "i"},
            {"type": "formula", "as": "entrada", "expr": f"datum.i < {CAP_E}"},
            {"type": "formula", "as": "j", "expr": f"datum.entrada ? datum.i : datum.i - {CAP_E}"},
            {"type": "filter", "expr": "datum.entrada ? datum.j < nEntrada : datum.j < nSalida"},
            {"type": "formula", "as": "carril", "expr": f"datum.j % (datum.entrada ? {N_E} : {N_S})"},
            {"type": "formula", "as": "hueco", "expr": f"floor(datum.j / (datum.entrada ? {N_E} : {N_S}))"},
            {"type": "formula", "as": "col", "expr": "datum.hueco % 2"},
            {"type": "formula", "as": "fila", "expr": "floor(datum.hueco / 2)"},
            # La playa necesita la clave del muelle de su carril
            {"type": "formula", "as": "clave", "expr": f"datum.entrada ? {IDS_E}[datum.carril] : {IDS_S}[datum.carril]"},
            {"type": "lookup", "from": "puertas", "key": "id", "fields": ["clave"], "values": ["X"], "as": ["mx"],
             "default": 0},
            # Ficha de los palets de playa (aún sin ubicación ni producto asignado en la vista)
            {"type": "formula", "as": "zona", "expr": "datum.entrada ? 'Playa de entrada · muelle ' + datum.clave : 'Playa de salida · muelle ' + datum.clave"},
            {"type": "formula", "as": "situacion", "expr": "datum.entrada ? 'Recibido, pendiente de ubicar en estantería' : 'Preparado, pendiente de cargar en camión'"},
            {"type": "formula", "as": "numero", "expr": "(datum.j + 1) + ' de ' + (datum.entrada ? nEntrada : nSalida) + ' en la playa'"},
            {"type": "formula", "as": "id", "expr": "(datum.entrada ? 'PE-' : 'PS-') + datum.j"},
            {"type": "formula", "as": "partes", "expr": expr_partes_playa},
            {"type": "flatten", "fields": ["partes"], "as": ["b"]},
            {"type": "formula", "as": "p", "expr": "datum.b.p"},
        ]},
        {"name": "base", "values": base, "transform": trans_caja + trans_caras},
        {"name": "planos", "values": planos, "transform": [{"type": "collect", "sort": {"field": "orden"}}]},
        {"name": "lineas", "values": lineas},
        {"name": "sombrasDin", "source": "camiones", "transform": [
            {"type": "filter", "expr": "datum.p == 'remolque'"},
            {"type": "formula", "as": "x0", "expr": "datum.b.x"}, {"type": "formula", "as": "x1", "expr": "datum.b.x + datum.b.dx"},
            {"type": "formula", "as": "y0", "expr": "datum.b.y"}, {"type": "formula", "as": "y1", "expr": f"datum.b.y + 7.0"},
        ]},
        {"name": "escena", "source": ["fijasCaras", "palet", "carretillas", "camiones", "pilotos", "playa"],
         "transform": trans_caja + trans_caras + [
             # Banda de dibujo = fila de estanterías (1 = la del fondo … N = la de junto a los muelles)
             {"type": "formula", "as": "banda", "expr": "floor(datum.b.k / 1e7)"},
             {"type": "formula", "as": "fantasma", "expr": f"datum.banda >= 1 && datum.banda <= {N_FILAS} && datum.banda > bandaFoco"},
         ]},
        # Modo corte: las filas que quedan delante de la fila en foco se dibujan aparte, en fantasma
        {"name": "vivas", "source": "escena", "transform": [
            {"type": "filter", "expr": "!datum.fantasma"},
            {"type": "collect", "sort": {"field": ["b.k", "cara"]}}]},
        {"name": "rayos", "source": "escena", "transform": [
            {"type": "filter", "expr": "datum.fantasma"},
            {"type": "collect", "sort": {"field": ["b.k", "cara"]}}]},
        {"name": "fijasCaras", "values": fijas},
        {"name": "filasOcupacion", "source": "huecos", "transform": [
            {"type": "aggregate", "groupby": ["Pasillo", "y0", "lado"], "fields": ["Palets en stock", "UbicacionID"],
             "ops": ["sum", "count"], "as": ["ocupados", "capacidad"]},
            {"type": "formula", "as": "pct", "expr": "datum.ocupados / datum.capacidad"},
            # Las filas de cada pareja llevan la etiqueta en extremos opuestos para no solaparse
            {"type": "formula", "as": "xr", "expr": f"datum.lado == 'neg' ? {X0 - 1.2} : {FIN_RACK + 1.2}"},
        ]},
        {"name": "textos", "values": textos},
    ],
    "marks": [],
}

# El conjunto «escena» usa «fijasCaras» como fuente: debe declararse antes
datos = spec["data"]
i_esc = next(i for i, d in enumerate(datos) if d["name"] == "escena")
i_fij = next(i for i, d in enumerate(datos) if d["name"] == "fijasCaras")
datos.insert(i_esc, datos.pop(i_fij))

sombra_dyn = ("'M' + (ox + (datum.x0 - datum.y0) * s) + ',' + (oy + (datum.x0 + datum.y0) / 2 * s)"
              f" + 'L' + (ox + (datum.x1 - datum.y0) * s) + ',' + (oy + (datum.x1 + datum.y0) / 2 * s)"
              f" + 'L' + (ox + (datum.x1 + {LUZ[0] * 3} - datum.y1 - {LUZ[1] * 3}) * s) + ',' + (oy + (datum.x1 + {LUZ[0] * 3} + datum.y1 + {LUZ[1] * 3}) / 2 * s)"
              f" + 'L' + (ox + (datum.x0 + {LUZ[0] * 3} - datum.y1 - {LUZ[1] * 3}) * s) + ',' + (oy + (datum.x0 + {LUZ[0] * 3} + datum.y1 + {LUZ[1] * 3}) / 2 * s) + 'Z'")

spec["marks"] = [
    {   # sombra difusa bajo la maqueta
        "type": "path",
        "encode": {"update": {
            "path": {"signal": " + ".join([
                f"'{c}' + (ox + ({x} - {y}) * s) + ',' + (oy + (({x} + {y}) / 2 + 1.6) * s)"
                for c, (x, y) in zip("MLLL", [(-2, -2), (W + 2, -2), (W + 2, D_PATIO + 2), (-2, D_PATIO + 2)])]) + " + 'Z'"},
            "fill": {"value": {"gradient": "radial", "x1": 0.5, "y1": 0.5, "r1": 0, "x2": 0.5, "y2": 0.5, "r2": 0.5,
                               "stops": [{"offset": 0, "color": "rgba(0,0,0,0.55)"}, {"offset": 1, "color": "rgba(0,0,0,0)"}]}},
        }},
    },
    marca_caras("losa", "base"),
    {
        "type": "path", "from": {"data": "planos"},
        "encode": {"update": {
            "path": {"signal": puntos_plano},
            "fill": {"signal": "datum.g == 'radial' ? {gradient: 'radial', x1: 0.5, y1: 0.5, r1: 0, x2: 0.5, y2: 0.5, r2: 0.5, stops: [{offset: 0, color: 'rgba(170,205,255,0.10)'}, {offset: 1, color: 'rgba(170,205,255,0)'}]} : datum.fill || 'transparent'"},
            "fillOpacity": {"field": "op"},
            "stroke": {"signal": "datum.st || 'transparent'"},
            "strokeWidth": {"signal": "datum.sw * s"},
            "strokeOpacity": {"value": 0.6},
        }},
    },
    {
        "type": "rule", "from": {"data": "lineas"},
        "encode": {"update": {
            "x": {"signal": "ox + (datum.a[0] - datum.a[1]) * s"},
            "y": {"signal": f"oy + ((datum.a[0] + datum.a[1]) / 2 - datum.a[2] * {ZF}) * s"},
            "x2": {"signal": "ox + (datum.b[0] - datum.b[1]) * s"},
            "y2": {"signal": f"oy + ((datum.b[0] + datum.b[1]) / 2 - datum.b[2] * {ZF}) * s"},
            "stroke": {"field": "st"},
            "strokeWidth": {"signal": "max(0.5, datum.sw * s)"},
            "strokeOpacity": {"field": "op"},
            "strokeDash": {"signal": "datum.da || [1, 0]"},
        }},
    },
    {
        "type": "path", "from": {"data": "sombrasDin"},
        "encode": {"update": {"path": {"signal": sombra_dyn}, "fill": {"value": "#00040D"}, "fillOpacity": {"value": 0.35}}},
    },
    marca_caras("mundo", "vivas", interactiva=True),
    {   # filas delante de la fila en foco: cristal casi transparente que no captura el ratón
        "type": "path", "name": "rayosX", "from": {"data": "rayos"}, "interactive": False,
        "encode": {"update": {
            "path": {"field": "trazo"},
            "fill": {"field": "relleno"},
            "fillOpacity": {"value": 0.045},
            "stroke": {"value": "#BAE6FD"},
            "strokeOpacity": {"signal": "datum.p == 'carga' ? 0.16 : 0.1"},
            "strokeWidth": {"value": 0.5},
        }},
    },
    {
        "type": "text", "from": {"data": "textos"},
        "encode": {"update": {
            "x": {"signal": "ox + (datum.x - datum.y) * s"},
            "y": {"signal": f"oy + ((datum.x + datum.y) / 2 - datum.z * {ZF}) * s"},
            "text": {"field": "t"}, "angle": {"field": "ang"}, "align": {"field": "al"}, "baseline": {"value": "middle"},
            "fill": {"field": "col"}, "fillOpacity": {"field": "op"}, "font": {"value": "Segoe UI"},
            "fontWeight": {"field": "w"}, "fontSize": {"signal": "max(7, datum.sz * s)"},
        }},
    },
]

# Etiqueta flotante de ocupación por fila, sobre la cabecera de cada estantería
PX = "ox + (datum.xr - datum.y0 - 0.55) * s"
PY = f"oy + ((datum.xr + datum.y0 + 0.55) / 2 - {r3(ALTO_RACK + 1.15)} * {ZF}) * s"
COLOR_PCT = "datum.pct >= 0.9 ? '{r}' : datum.pct >= 0.75 ? '{a}' : '{v}'"
spec["marks"] += [
    {"type": "rule", "from": {"data": "filasOcupacion"}, "encode": {"update": {
        "x": {"signal": PX}, "x2": {"signal": PX}, "y": {"signal": PY + " + 0.68 * s"},
        "y2": {"signal": f"oy + ((datum.xr + datum.y0 + 0.55) / 2 - {ALTO_RACK} * {ZF}) * s"},
        "stroke": {"value": "#94A3B8"}, "strokeOpacity": {"value": 0.5}, "strokeWidth": {"value": 1}, "strokeDash": {"value": [2, 2]}}}},
    {"type": "rect", "from": {"data": "filasOcupacion"}, "encode": {"update": {
        "x": {"signal": PX + " - 2.7 * s"}, "width": {"signal": "5.4 * s"},
        "y": {"signal": PY + " - 0.68 * s"}, "height": {"signal": "1.36 * s"}, "cornerRadius": {"signal": "0.68 * s"},
        "fill": {"signal": "datum.Pasillo == foco ? 'rgba(45,212,191,0.22)' : 'rgba(10,16,30,0.88)'"},
        "opacity": {"signal": "foco == 'Todas' || datum.Pasillo == foco ? 1 : 0.45"},
        "stroke": {"signal": "datum.Pasillo == foco ? '#FFFFFF' : " + COLOR_PCT.format(r="#F43F5E", a="#F59E0B", v="#2DD4BF")},
        "strokeWidth": {"signal": "datum.Pasillo == foco ? 2 : 1.3"}}}},
    {"type": "text", "from": {"data": "filasOcupacion"}, "encode": {"update": {
        "x": {"signal": PX + " - 1.75 * s"}, "y": {"signal": PY}, "baseline": {"value": "middle"}, "align": {"value": "center"},
        "text": {"field": "Pasillo"}, "fill": {"value": "#FFFFFF"}, "font": {"value": "Segoe UI"},
        "opacity": {"signal": "foco == 'Todas' || datum.Pasillo == foco ? 1 : 0.45"},
        "fontWeight": {"value": "bold"}, "fontSize": {"signal": "max(8, 0.8 * s)"}}}},
    {"type": "text", "from": {"data": "filasOcupacion"}, "encode": {"update": {
        "x": {"signal": PX + " + 0.75 * s"}, "y": {"signal": PY}, "baseline": {"value": "middle"}, "align": {"value": "center"},
        "text": {"signal": "format(datum.pct * 100, '.0f') + ' %'"},
        "fill": {"signal": COLOR_PCT.format(r="#FDA4AF", a="#FCD34D", v="#5EEAD4")},
        "opacity": {"signal": "foco == 'Todas' || datum.Pasillo == foco ? 1 : 0.45"},
        "font": {"value": "Segoe UI"}, "fontWeight": {"value": "bold"}, "fontSize": {"signal": "max(8, 0.7 * s)"}}}},
]

SALIDA.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
n_fijas = sum(len(x["b"]["f"]) for x in fijas)
print(f"Escena escrita en {SALIDA.name}: {N_FILAS} filas, {N_E}+{N_S} muelles, edificio {W:g} x {D:g}. "
      f"{len(fijas)} cajas fijas ({n_fijas} caras), {len(planos)} planos, {len(lineas)} líneas, {len(textos)} textos. "
      f"Encuadre U {U0:.1f}..{U1:.1f}  V {V0:.1f}..{V1:.1f}  ({DU:.1f} x {DV:.1f})")
