# -*- coding: utf-8 -*-
"""
Genera un año de operación ficticia de un centro de distribución de palets.

Todo es inventado: productos, proveedores, operarios, destinos y cifras.
El almacén se simula palet a palet y por eventos en el tiempo, de modo que la
ocupación, las entradas, las salidas y los camiones cuadran entre sí.

Uso:     python generar_datos.py
Salida:  ../datos/*.csv  (UTF-8, separador coma, decimales con punto)
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 2026
INICIO = date(2025, 10, 1)
FIN = date(2026, 9, 30)
CARPETA = Path(__file__).resolve().parent.parent / "datos"
rng = np.random.default_rng(SEMILLA)

# ---------------------------------------------------------------- calendario
FESTIVOS = {
    date(2025, 10, 12): "Fiesta Nacional",
    date(2025, 11, 1): "Todos los Santos",
    date(2025, 12, 6): "Día de la Constitución",
    date(2025, 12, 8): "Inmaculada Concepción",
    date(2025, 12, 25): "Navidad",
    date(2026, 1, 1): "Año Nuevo",
    date(2026, 1, 6): "Reyes",
    date(2026, 4, 3): "Viernes Santo",
    date(2026, 5, 1): "Día del Trabajo",
    date(2026, 8, 15): "Asunción",
}
BLACK_FRIDAY = (date(2025, 11, 24), date(2025, 11, 30))
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
FACTOR_DIA = [1.12, 1.05, 1.0, 1.0, 1.08, 0.5, 0.0]  # lunes..domingo


def abierto(d: date) -> bool:
    return d.weekday() < 6 and d not in FESTIVOS


def temporada(d: date) -> str:
    if BLACK_FRIDAY[0] <= d <= BLACK_FRIDAY[1]:
        return "Black Friday"
    if d >= date(d.year, 12, 1) or (d.month == 1 and d.day <= 6):
        return "Navidad"
    if d.month in (7, 8):
        return "Verano"
    return "Normal"


# ------------------------------------------------------------------- layout
# 8 filas de estanterías (A, la más cercana a los muelles), 12 huecos por fila,
# 6 niveles y 3 posiciones de palet por hueco: 1.728 ubicaciones.
PASILLOS = "ABCDEFGH"
HUECOS, NIVELES, POSICIONES = 12, 6, 3
# Coordenadas en "unidades de palet" para el dibujo isométrico.
Y_FILA = {"H": 1.0, "G": 2.1, "F": 5.7, "E": 6.8, "D": 10.4, "C": 11.5, "B": 15.1, "A": 16.2}
ZONA_DE = {"A": "Z1", "B": "Z1", "C": "Z2", "D": "Z2", "E": "Z2", "F": "Z2", "G": "Z3", "H": "Z3"}
ZONAS = [
    ("Z1", "Z1 · Alta rotación", 1, "Filas A y B, junto a los muelles"),
    ("Z2", "Z2 · Rotación media", 2, "Filas C a F"),
    ("Z3", "Z3 · Reserva", 3, "Filas G y H, al fondo"),
]
ZONA_PREF = {"A": ["Z1", "Z2", "Z3"], "B": ["Z2", "Z1", "Z3"], "C": ["Z3", "Z2", "Z1"]}


def x_posicion(hueco: int, pos: int) -> float:
    return round(1.5 + (hueco - 1) * 3.15 + 0.15 + (pos - 1) * 1.0, 2)


# ---------------------------------------------------------------- productos
TEMPORADA_MES = {
    "Bebidas": {1: .8, 2: .85, 3: .95, 4: 1.05, 5: 1.15, 6: 1.4, 7: 1.55, 8: 1.45, 9: 1.1, 10: .95, 11: .95, 12: 1.2},
    "Alimentación": {1: .9, 2: .95, 3: 1, 4: 1.05, 5: 1, 6: .95, 7: .9, 8: .8, 9: 1, 10: 1, 11: 1.05, 12: 1.3},
    "Droguería": {1: .95, 2: .95, 3: 1.05, 4: 1.05, 5: 1, 6: 1, 7: .95, 8: .85, 9: 1, 10: 1, 11: 1.1, 12: 1.1},
    "Higiene y belleza": {1: .9, 2: .9, 3: .95, 4: 1, 5: 1.05, 6: 1.15, 7: 1.2, 8: 1, 9: .95, 10: .95, 11: 1.15, 12: 1.3},
    "Mascotas": {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: .95, 8: .9, 9: 1, 10: 1, 11: 1.05, 12: 1.1},
    "Bazar y hogar": {1: .8, 2: .85, 3: .95, 4: 1, 5: 1, 6: 1, 7: .9, 8: .8, 9: 1, 10: 1, 11: 1.4, 12: 1.5},
    "Temporada Navidad": {1: .25, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: .02, 10: .2, 11: 1.0, 12: 2.4},
}
CATEGORIAS = {
    # n SKU, peso en volumen, valor €/palet, nº proveedores, nombres base
    "Bebidas": (58, .26, (250, 450), 3, [
        "Agua mineral 1,5 L", "Agua con gas 1 L", "Refresco de cola 2 L", "Refresco de naranja 2 L",
        "Zumo de naranja 1 L", "Cerveza lata 33 cl", "Cerveza sin alcohol 33 cl", "Bebida isotónica 50 cl",
        "Té frío al limón 1,5 L", "Gaseosa 1,5 L"]),
    "Alimentación": (75, .28, (400, 1200), 4, [
        "Arroz redondo 1 kg", "Espaguetis 500 g", "Macarrones 500 g", "Aceite de oliva 1 L",
        "Aceite de girasol 1 L", "Tomate triturado 400 g", "Garbanzos cocidos 400 g", "Galletas 800 g",
        "Cereales de desayuno 500 g", "Leche UHT 1 L", "Azúcar 1 kg", "Harina de trigo 1 kg",
        "Atún en aceite 3x80 g", "Café molido 250 g", "Cacao soluble 400 g"]),
    "Droguería": (46, .14, (500, 1100), 3, [
        "Detergente líquido 3 L", "Detergente en cápsulas 40 uds", "Suavizante 2 L", "Lavavajillas a mano 1 L",
        "Pastillas lavavajillas 50 uds", "Lejía 2 L", "Limpiador multiusos 750 ml", "Papel higiénico 12 rollos",
        "Papel de cocina 4 rollos", "Fregasuelos 1,5 L"]),
    "Higiene y belleza": (42, .11, (900, 2500), 3, [
        "Gel de ducha 750 ml", "Champú 400 ml", "Pasta de dientes 75 ml", "Desodorante 200 ml",
        "Pañales talla 4", "Toallitas húmedas 80 uds", "Protector solar 200 ml", "Crema hidratante 400 ml",
        "Jabón de manos 500 ml"]),
    "Mascotas": (25, .06, (500, 900), 2, [
        "Pienso perro adulto 15 kg", "Pienso gato 4 kg", "Arena para gatos 10 L",
        "Comida húmeda gato 12x85 g", "Snacks dentales perro"]),
    "Bazar y hogar": (34, .09, (600, 1800), 3, [
        "Bolsas de basura 30 L", "Papel de aluminio 30 m", "Film transparente 50 m", "Pilas AA 8 uds",
        "Bombillas LED 3 uds", "Velas aromáticas", "Vasos desechables 50 uds", "Servilletas 100 uds",
        "Menaje de cocina"]),
    "Temporada Navidad": (20, .06, (900, 2600), 2, [
        "Turrón duro 300 g", "Turrón blando 300 g", "Polvorones 400 g", "Mantecados surtidos 1 kg",
        "Cava brut 75 cl", "Bombones surtidos 400 g", "Lote navideño", "Mazapán 250 g"]),
}
VOLUMEN_DIARIO = 160  # palets/día de salida esperados de media en días abiertos
# Política de reposición por clase (revisión diaria, el proveedor entrega solo ciertos días):
# se protege la demanda hasta la llegada del pedido que se podría lanzar mañana, más unos
# días de seguridad y un colchón estadístico (z · raíz de la demanda esperada).
SEGURIDAD = {"A": 0.5, "B": 1.0, "C": 2.0}
COBERTURA = {"A": 3.0, "B": 5.0, "C": 10.0}
Z = {"A": 1.3, "B": 1.0, "C": 0.5}

DESTINOS = [
    ("D01", "Madrid", 40.4168, -3.7038, .22),
    ("D02", "Cataluña", 41.3874, 2.1686, .16),
    ("D03", "Andalucía", 37.3891, -5.9845, .15),
    ("D04", "Comunidad Valenciana", 39.4699, -0.3763, .12),
    ("D05", "Castilla y León", 41.6523, -4.7245, .07),
    ("D06", "Castilla-La Mancha", 39.8628, -4.0273, .07),
    ("D07", "País Vasco", 43.2630, -2.9350, .06),
    ("D08", "Galicia", 43.3623, -8.4115, .06),
    ("D09", "Aragón", 41.6488, -0.8891, .05),
    ("D10", "Región de Murcia", 37.9922, -1.1307, .04),
]
PALETS_CAMION = 33
CALENTAMIENTO = 28  # días simulados antes de INICIO que no se registran


def temporada_valor(tabla: dict, d: date) -> float:
    """Factor mensual interpolado entre los días 15 de cada mes."""
    m = d.month
    mitad = date(d.year, m, 15)
    if d >= mitad:
        m2, a2 = (1, d.year + 1) if m == 12 else (m + 1, d.year)
        otro = date(a2, m2, 15)
        w = (d - mitad).days / (otro - mitad).days
        return tabla[m] * (1 - w) + tabla[m2] * w
    m0, a0 = (12, d.year - 1) if m == 1 else (m - 1, d.year)
    otro = date(a0, m0, 15)
    w = (d - otro).days / (mitad - otro).days
    return tabla[m0] * (1 - w) + tabla[m] * w


def factor_extra(cat: str, d: date) -> float:
    f = 1.0
    if BLACK_FRIDAY[0] <= d <= BLACK_FRIDAY[1]:
        f *= {"Bazar y hogar": 1.45, "Higiene y belleza": 1.3, "Droguería": 1.25, "Bebidas": 1.1}.get(cat, 1.05)
    if date(2025, 12, 15) <= d <= date(2025, 12, 23):
        f *= {"Alimentación": 1.25, "Bebidas": 1.2, "Temporada Navidad": 1.4}.get(cat, 1.0)
    if cat == "Temporada Navidad" and date(2026, 1, 7) <= d < date(2026, 9, 1):
        f *= 0.1
    return f


def a_texto(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def main() -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    # La simulación arranca CALENTAMIENTO días antes de INICIO y no registra nada hasta
    # INICIO: así el 1 de octubre ya hay pedidos en camino y el stock está asentado.
    n_dias = (FIN - INICIO).days + 1
    n_sim = CALENTAMIENTO + n_dias
    horizonte = n_sim + 45
    dias = [INICIO - timedelta(CALENTAMIENTO) + timedelta(i) for i in range(horizonte)]
    reales = slice(CALENTAMIENTO, n_sim)

    # ------------------------------------------------------------ calendario
    cal = []
    for d in dias[reales]:
        iso = d.isocalendar()
        cal.append({
            "Fecha": d.isoformat(), "Año": d.year, "Mes": d.month, "Nombre del mes": MESES[d.month - 1],
            "Mes corto": MESES[d.month - 1][:3], "Año-mes": d.year * 100 + d.month,
            "Mes y año": f"{MESES[d.month - 1][:3]} {d.year % 100:02d}",
            "Trimestre": f"T{(d.month - 1) // 3 + 1}", "Semana ISO": iso[1], "Día": d.day,
            "Día de la semana": DIAS[d.weekday()], "Orden día semana": d.weekday() + 1,
            "Abierto": "Sí" if abierto(d) else "No", "Festivo": FESTIVOS.get(d, ""),
            "Temporada": temporada(d),
        })
    horas = [{"Hora": h, "Hora texto": f"{h:02d}:00",
              "Turno": "Mañana" if 6 <= h < 14 else "Tarde" if 14 <= h < 22 else "Noche"} for h in range(24)]

    # ----------------------------------------------------------- ubicaciones
    slots = []
    for i, p in enumerate(PASILLOS):
        for h in range(1, HUECOS + 1):
            for n in range(1, NIVELES + 1):
                for q in range(1, POSICIONES + 1):
                    slots.append({
                        "UbicacionID": f"{p}-{h:02d}-{n}-{q}", "Pasillo": p, "Orden pasillo": i + 1,
                        "Hueco": h, "Nivel": n, "Posición": q, "ZonaID": ZONA_DE[p],
                        "X": x_posicion(h, q), "Y": Y_FILA[p], "Z": round((n - 1) * 0.95, 2),
                    })
    CAP = len(slots)
    pasillo_idx = np.array([PASILLOS.index(s["Pasillo"]) for s in slots])
    nivel_de = np.array([s["Nivel"] for s in slots])
    rank = {}
    for k in "ABC":
        orden = sorted(range(CAP), key=lambda s: (
            ZONA_PREF[k].index(slots[s]["ZonaID"]),
            slots[s]["Nivel"] if k != "C" else -slots[s]["Nivel"],
            slots[s]["Hueco"], pasillo_idx[s], slots[s]["Posición"]))
        r = np.empty(CAP, dtype=int)
        r[orden] = np.arange(CAP)
        rank[k] = r
    libre = np.ones(CAP, dtype=bool)
    montones = {k: [(int(rank[k][s]), s) for s in range(CAP)] for k in "ABC"}
    for k in "ABC":
        heapq.heapify(montones[k])

    def tomar_hueco(k: str):
        m = montones[k]
        while m:
            _, s = heapq.heappop(m)
            if libre[s]:
                libre[s] = False
                return s
        return None

    def liberar(s: int) -> None:
        libre[s] = True
        for k in "ABC":
            heapq.heappush(montones[k], (int(rank[k][s]), s))

    # ---------------------------------------------------- proveedores y SKU
    proveedores, productos = [], []
    n_prov = 0
    sku_num = rng.choice(np.arange(10000, 99999), size=sum(c[0] for c in CATEGORIAS.values()), replace=False)
    j = 0
    for cat, (n, peso, (vmin, vmax), nprov, nombres) in CATEGORIAS.items():
        ids = []
        for _ in range(nprov):
            n_prov += 1
            pid = f"PRV-{n_prov:02d}"
            dias_entrega = sorted(rng.choice(5, size=int(rng.choice([3, 5], p=[.4, .6])),
                                             replace=False).tolist())
            proveedores.append({"ProveedorID": pid, "Proveedor": f"Proveedor {n_prov:02d} · {cat}",
                                "Categoría": cat, "Plazo de entrega (días)": int(rng.integers(1, 4)),
                                "_dias": dias_entrega})
            ids.append(pid)
        crudo = rng.lognormal(0, 1.0, size=n)
        cuenta = defaultdict(int)
        for i in range(n):
            base = nombres[i % len(nombres)]
            cuenta[base] += 1
            productos.append({"SKU": f"SKU-{sku_num[j]}", "Producto": f"{base} · ref. {cuenta[base]:02d}",
                              "Categoría": cat, "ProveedorID": ids[i % nprov],
                              "Valor palet (€)": int(rng.integers(vmin, vmax) // 10 * 10),
                              "_peso": peso * crudo[i] / crudo.sum()})
            j += 1
    prov_de = {p["ProveedorID"]: p for p in proveedores}
    n_sku = len(productos)
    cats = sorted(CATEGORIAS)
    estac = {c: np.array([temporada_valor(TEMPORADA_MES[c], d) * factor_extra(c, d) for d in dias]) for c in cats}
    wd = np.array([FACTOR_DIA[d.weekday()] if abierto(d) else 0.0 for d in dias])
    # Escala: que la salida media en días abiertos sea VOLUMEN_DIARIO
    perfil = np.array([estac[p["Categoría"]] * p["_peso"] for p in productos])  # (sku, día)
    abiertos = wd[reales] > 0
    media = (perfil[:, reales] * wd[reales]).sum(axis=0)[abiertos].mean()
    base = np.array([p["_peso"] for p in productos]) * VOLUMEN_DIARIO / media
    esperado = base[:, None] * np.array([estac[p["Categoría"]] for p in productos]) * wd[None, :]
    acum = np.concatenate([np.zeros((n_sku, 1)), esperado.cumsum(axis=1)], axis=1)

    def esperado_ventana(s: int, desde: int, dias_v: float) -> float:
        hasta = min(horizonte, desde + int(math.ceil(dias_v)))
        return acum[s, hasta] - acum[s, desde]

    # Clase ABC por volumen anual esperado (Pareto 65 / 25 / 10)
    anual = esperado[:, reales].sum(axis=1)
    orden = np.argsort(-anual)
    cum = anual[orden].cumsum() / anual.sum()
    clase = np.empty(n_sku, dtype=object)
    for pos, s in enumerate(orden):
        clase[s] = "A" if cum[pos] <= .65 else "B" if cum[pos] <= .90 else "C"
    for s, p in enumerate(productos):
        p["Clase ABC"] = clase[s]
        p["Demanda media (palets/día)"] = round(anual[s] / abiertos.sum(), 3)
    sku_id = [p["SKU"] for p in productos]
    valor = np.array([p["Valor palet (€)"] for p in productos])

    cache_llegada: dict = {}

    def llegada(pid: str, d0: date) -> date:
        """Primer día de entrega del proveedor, abierto, tras su plazo."""
        if (pid, d0) not in cache_llegada:
            pr = prov_de[pid]
            dl = d0 + timedelta(days=pr["Plazo de entrega (días)"])
            while not (abierto(dl) and dl.weekday() in pr["_dias"]):
                dl += timedelta(days=1)
            cache_llegada[(pid, d0)] = dl
        return cache_llegada[(pid, d0)]

    def siguiente_abierto(d0: date) -> date:
        d1 = d0 + timedelta(days=1)
        while not abierto(d1):
            d1 += timedelta(days=1)
        return d1

    def umbrales(s: int, di: int, desde: int) -> tuple[float, float, date]:
        """Punto de pedido, nivel objetivo y fecha de llegada de un pedido lanzado el día di."""
        c = clase[s]
        pid = productos[s]["ProveedorID"]
        d0 = dias[di]
        proteccion = (llegada(pid, siguiente_abierto(d0)) - d0).days
        e_prot = esperado_ventana(s, desde, proteccion)
        colchon = Z[c] * math.sqrt(e_prot)
        rop = esperado_ventana(s, desde, proteccion + SEGURIDAD[c]) + colchon
        objetivo = esperado_ventana(s, desde, proteccion + COBERTURA[c]) + colchon
        return rop, objetivo, llegada(pid, d0)

    # ------------------------------------------------------------- operarios
    operarios = []
    k = 1
    # Mañana: descarga y ubicación de lo que entra + primeras preparaciones. Tarde: preparación
    # de pedidos; si queda algo por ubicar por la tarde, lo hace un preparador.
    for turno, roles in (("Mañana", (("Carretillero", 4), ("Preparador", 3))), ("Tarde", (("Preparador", 4),))):
        for rol, n in roles:
            for _ in range(n):
                operarios.append({"OperarioID": f"OP-{k:02d}", "Operario": f"Operario {k:02d}",
                                  "Turno": turno, "Rol": rol,
                                  "_ef": float(np.clip(rng.normal(1.0, .12), .75, 1.3))})
                k += 1
    grupos = {}
    for turno in ("Mañana", "Tarde"):
        for rol in ("Carretillero", "Preparador"):
            g = [o for o in operarios if o["Turno"] == turno and o["Rol"] == rol]
            if not g:
                g = [o for o in operarios if o["Turno"] == turno]
            w = np.array([o["_ef"] for o in g])
            grupos[(turno, rol)] = (g, w / w.sum())

    def operario(t: datetime, rol: str) -> dict:
        g, w = grupos[("Mañana" if t.hour < 14 else "Tarde", rol)]
        return g[rng.choice(len(g), p=w)]

    muelles = ([{"MuelleID": f"E{i + 1}", "Muelle": f"Muelle E{i + 1}", "Tipo": "Entrada", "Orden": i + 1,
                 "X": 2.5 + i * 3.0, "Y": 22.0} for i in range(6)] +
               [{"MuelleID": f"S{i + 1}", "Muelle": f"Muelle S{i + 1}", "Tipo": "Salida", "Orden": i + 7,
                 "X": 22.5 + i * 3.0, "Y": 22.0} for i in range(6)])

    # ------------------------------------------------------------ simulación
    movs, camiones, stock_diario, ocup_horaria = [], [], [], []
    stock = [deque() for _ in range(n_sku)]        # huecos por SKU, en orden de entrada (FIFO)
    hueco_sku = np.full(CAP, -1)
    hueco_entrada: list = [None] * CAP
    ocup_pasillo = np.zeros(len(PASILLOS), dtype=int)
    en_pedido = np.zeros(n_sku, dtype=int)
    llegadas = defaultdict(lambda: defaultdict(list))  # día -> proveedor -> [sku, ...]
    pendientes: deque = deque()                       # palets sin hueco, esperando en playa
    en_playa = np.zeros(n_sku, dtype=int)
    contador = {"mov": 0, "sin_hueco": 0, "registrar": False}

    def nuevo_mov(**kw):
        if not contador["registrar"]:
            return
        contador["mov"] += 1
        kw["MovimientoID"] = contador["mov"]
        movs.append(kw)

    def colocar(s_hueco: int, s: int, t: datetime, tipo: str, extra: dict) -> None:
        hueco_sku[s_hueco] = s
        hueco_entrada[s_hueco] = t
        stock[s].append(s_hueco)
        ocup_pasillo[pasillo_idx[s_hueco]] += 1
        dur = None
        op = None
        if tipo == "Entrada":
            o = operario(t, "Carretillero")
            op = o["OperarioID"]
            b = 2.6 + .45 * (nivel_de[s_hueco] - 1) + .12 * pasillo_idx[s_hueco]
            dur = round(b / o["_ef"] * rng.lognormal(0, .18), 1)
        nuevo_mov(FechaHora=t, Tipo=tipo, Signo=1, SKU=sku_id[s], UbicacionID=slots[s_hueco]["UbicacionID"],
                  OperarioID=op, DuracionMin=dur, **extra)

    tot = np.array([umbrales(s, CALENTAMIENTO, CALENTAMIENTO + 1)[:2] for s in range(n_sku)])
    print(f"Política el {INICIO}: punto de pedido {tot[:, 0].sum():.0f}, objetivo {tot[:, 1].sum():.0f}, "
          f"demanda esperada/día {esperado[:, reales].sum(axis=0)[abiertos].mean():.0f}")
    # Arranque del calentamiento: en el punto de pedido, sin nada en camino
    for s in np.argsort([{"A": 0, "B": 1, "C": 2}[c] for c in clase], kind="stable"):
        c = clase[s]
        rop, _, _ = umbrales(s, 0, 0)
        for _ in range(int(round(rop))):
            h = tomar_hueco(c)
            if h is None:
                break
            antig = {"A": 6, "B": 12, "C": 30}[c]
            t = datetime.combine(dias[0], datetime.min.time()) - timedelta(
                minutes=int(rng.integers(60, antig * 1440)))
            colocar(h, s, t, "Stock inicial", {})
    for s in range(n_sku):
        stock[s] = deque(sorted(stock[s], key=lambda h: hueco_entrada[h]))

    destinos_w = np.array([d[4] for d in DESTINOS])
    for di in range(n_sim):
        d = dias[di]
        if di == CALENTAMIENTO:
            # Empieza el registro: lo que hay en las estanterías es el stock inicial
            contador["registrar"] = True
            for h in sorted(np.nonzero(~libre)[0], key=lambda h: hueco_entrada[h]):
                s = int(hueco_sku[h])
                nuevo_mov(FechaHora=hueco_entrada[h], Tipo="Stock inicial", Signo=1, SKU=sku_id[s],
                          UbicacionID=slots[h]["UbicacionID"], OperarioID=None, DuracionMin=None,
                          MuelleID=None, CamionID=None, ProveedorID=productos[s]["ProveedorID"], DestinoID=None)
            print(f"Stock inicial: {CAP - libre.sum()} palets ({(CAP - libre.sum()) / CAP:.1%}), "
                  f"en camino {en_pedido.sum()}")
        dt0 = datetime.combine(d, datetime.min.time())
        demanda = np.zeros(n_sku, dtype=int)
        servidos = np.zeros(n_sku, dtype=int)
        entradas_dia = np.zeros(n_sku, dtype=int)
        eventos = []
        n_camiones_antes = len(camiones)

        if abierto(d):
            sabado = d.weekday() == 5
            # ---- camiones de entrada
            prov_hoy = llegadas.pop(d, {})
            viajes = []
            for pid, lista in prov_hoy.items():
                rng.shuffle(lista)
                for i in range(0, len(lista), PALETS_CAMION):
                    viajes.append((pid, lista[i:i + PALETS_CAMION]))
            rng.shuffle(viajes)
            ini, fin = (6.0, 10.5) if sabado else (6.0, 13.0)
            libre_muelle = {f"E{i + 1}": dt0 for i in range(6)}
            plan = []
            for n, (pid, carga) in enumerate(viajes):
                prev = dt0 + timedelta(hours=ini + (fin - ini) * (n + rng.uniform(.1, .9)) / max(1, len(viajes)))
                prev = prev.replace(second=0, microsecond=0) - timedelta(minutes=prev.minute % 5)
                retraso = rng.normal(3, 10) if rng.random() > .07 else rng.uniform(45, 120)
                real = prev + timedelta(minutes=float(retraso))
                plan.append((real, prev, pid, carga))
            plan.sort(key=lambda x: x[0])
            for n, (real, prev, pid, carga) in enumerate(plan):
                muelle = min(libre_muelle, key=lambda m: (libre_muelle[m], m))
                inicio = max(real, libre_muelle[muelle], dt0 + timedelta(hours=6))
                ritmo = .8 + rng.uniform(0, .3)
                fin_op = inicio + timedelta(minutes=10 + ritmo * len(carga))
                libre_muelle[muelle] = fin_op + timedelta(minutes=5)
                cid = f"E{d:%y%m%d}-{n + 1:02d}"
                camiones.append({"CamionID": cid, "Tipo": "Entrada", "Fecha": d.isoformat(), "MuelleID": muelle,
                                 "ProveedorID": pid, "DestinoID": None, "Palets previstos": len(carga),
                                 "Palets": len(carga), "Hora prevista": a_texto(prev), "Hora real": a_texto(real),
                                 "Inicio operación": a_texto(inicio), "Fin operación": a_texto(fin_op),
                                 "Espera (min)": round((inicio - real).total_seconds() / 60, 1),
                                 "Retraso (min)": round((real - prev).total_seconds() / 60, 1)})
                for i, s in enumerate(carga):
                    t = inicio + timedelta(minutes=10 + ritmo * (i + 1) + rng.uniform(2, 9))
                    eventos.append((t, 0, s, cid, muelle, pid, None))
                    entradas_dia[s] += 1

            # ---- demanda y camiones de salida
            demanda = rng.poisson(esperado[:, di])
            por_destino = defaultdict(list)
            for s in np.nonzero(demanda)[0]:
                reparto = rng.multinomial(demanda[s], destinos_w)
                for k_d, q in enumerate(reparto):
                    por_destino[k_d].extend([s] * q)
            viajes = []
            for k_d, lista in por_destino.items():
                rng.shuffle(lista)
                for i in range(0, len(lista), PALETS_CAMION):
                    viajes.append((k_d, lista[i:i + PALETS_CAMION]))
            libre_muelle_s = {f"S{i + 1}": dt0 for i in range(6)}
            plan = []
            for k_d, carga in viajes:
                if sabado:
                    h = rng.uniform(9.5, 13.5)
                else:
                    h = rng.uniform(11, 14) if rng.random() < .25 else rng.uniform(14, 21.5)
                salida = dt0 + timedelta(hours=float(h))
                salida = salida.replace(second=0, microsecond=0) - timedelta(minutes=salida.minute % 5)
                plan.append((salida, k_d, carga))
            plan.sort(key=lambda x: x[0])
            for n, (salida, k_d, carga) in enumerate(plan):
                cid = f"S{d:%y%m%d}-{n + 1:02d}"
                carga_ini = salida - timedelta(minutes=35)
                muelle = min(libre_muelle_s, key=lambda m: (libre_muelle_s[m], m))
                inicio = max(carga_ini, libre_muelle_s[muelle])
                camiones.append({"CamionID": cid, "Tipo": "Salida", "Fecha": d.isoformat(), "MuelleID": muelle,
                                 "ProveedorID": None, "DestinoID": DESTINOS[k_d][0],
                                 "Palets previstos": len(carga), "Palets": 0, "Hora prevista": a_texto(salida),
                                 "Hora real": None, "Inicio operación": a_texto(inicio), "Fin operación": None,
                                 "Espera (min)": 0.0, "Retraso (min)": None, "_ultima": None})
                libre_muelle_s[muelle] = inicio + timedelta(minutes=40)
                for s in carga:
                    t = salida - timedelta(minutes=float(rng.uniform(35, 150)))
                    eventos.append((t, 1, s, cid, muelle, None, DESTINOS[k_d][0]))
        camion_idx = {c["CamionID"]: c for c in camiones[n_camiones_antes:]}

        # ---- procesar eventos en orden y fotografiar la ocupación cada hora
        eventos.sort(key=lambda e: (e[0], e[1]))
        ev = 0
        for hora in range(24):
            corte = dt0 + timedelta(hours=hora + 1)
            while ev < len(eventos) and eventos[ev][0] < corte:
                t, tipo, s, cid, muelle, pid, did = eventos[ev]
                ev += 1
                if tipo == 0:
                    h = tomar_hueco(clase[s])
                    if h is None:
                        pendientes.append((s, cid, muelle, pid))
                        en_playa[s] += 1
                        contador["sin_hueco"] += 1
                        continue
                    colocar(h, s, t.replace(microsecond=0), "Entrada",
                            {"MuelleID": muelle, "CamionID": cid, "ProveedorID": pid, "DestinoID": None})
                else:
                    if not stock[s]:
                        continue
                    h = stock[s].popleft()
                    o = operario(t, "Preparador")
                    b = 3.2 + .5 * (nivel_de[h] - 1) + .12 * pasillo_idx[h]
                    nuevo_mov(FechaHora=t.replace(microsecond=0), Tipo="Salida", Signo=-1, SKU=sku_id[s],
                              UbicacionID=slots[h]["UbicacionID"], OperarioID=o["OperarioID"],
                              DuracionMin=round(b / o["_ef"] * rng.lognormal(0, .18), 1),
                              MuelleID=muelle, CamionID=cid, ProveedorID=None, DestinoID=did)
                    hueco_sku[h] = -1
                    hueco_entrada[h] = None
                    ocup_pasillo[pasillo_idx[h]] -= 1
                    liberar(h)
                    servidos[s] += 1
                    c = camion_idx[cid]
                    c["Palets"] += 1
                    c["_ultima"] = max(c["_ultima"] or t, t)
                    if pendientes:
                        sp, cidp, mp, pp = pendientes.popleft()
                        en_playa[sp] -= 1
                        h2 = tomar_hueco(clase[sp])
                        # se ubica en el mismo instante en que se libera el hueco, para que la
                        # foto horaria y los movimientos cuadren al segundo
                        colocar(h2, sp, t.replace(microsecond=0), "Entrada",
                                {"MuelleID": mp, "CamionID": cidp, "ProveedorID": pp, "DestinoID": None})
            if contador["registrar"]:
                for i, p in enumerate(PASILLOS):
                    ocup_horaria.append({"Fecha": d.isoformat(), "Hora": hora, "Pasillo": p,
                                         "Ocupadas": int(ocup_pasillo[i])})
        assert ev == len(eventos), f"eventos fuera del día {d}"
        en_pedido -= entradas_dia  # lo que ha llegado hoy deja de estar pendiente de recibir

        # ---- cerrar camiones de salida
        for c in camion_idx.values():
            if c["Tipo"] != "Salida":
                continue
            prev = datetime.fromisoformat(c["Hora prevista"])
            listo = (c["_ultima"] + timedelta(minutes=25)) if c["_ultima"] else prev
            real = max(prev, listo) + timedelta(minutes=float(max(0, rng.normal(3, 7))))
            real = real.replace(microsecond=0)
            c["Hora real"] = a_texto(real)
            c["Fin operación"] = a_texto(real)
            c["Retraso (min)"] = round((real - prev).total_seconds() / 60, 1)

        # ---- foto de stock al cierre
        cierre = dt0 + timedelta(days=1)
        for s in range(n_sku if contador["registrar"] else 0):
            q = len(stock[s])
            if q == 0 and demanda[s] == 0 and entradas_dia[s] == 0:
                continue
            edad = (sum((cierre - hueco_entrada[h]).total_seconds() for h in stock[s]) / q / 86400) if q else None
            stock_diario.append({"Fecha": d.isoformat(), "SKU": sku_id[s], "Stock final (palets)": q,
                                 "Entradas (palets)": int(entradas_dia[s]), "Demanda (palets)": int(demanda[s]),
                                 "Servidos (palets)": int(servidos[s]),
                                 "No servidos (palets)": int(demanda[s] - servidos[s]),
                                 "Edad media (días)": round(edad, 2) if edad is not None else None,
                                 "Valor stock (€)": int(q * valor[s])})

        # ---- reposición: pedidos a proveedores para días de entrega futuros
        if abierto(d):
            pedidos = np.zeros(n_sku, dtype=int)
            llegada_de = {}
            for s in range(n_sku):
                posicion = len(stock[s]) + en_pedido[s] + en_playa[s]
                rop, objetivo, dl = umbrales(s, di, di + 1)
                if rop <= 0.05 or posicion >= rop:
                    continue
                q = int(math.ceil(objetivo - posicion))
                if q <= 0:
                    continue
                pedidos[s] = q
                llegada_de[s] = dl
            for s in np.nonzero(pedidos)[0]:
                llegadas[llegada_de[s]][productos[s]["ProveedorID"]].extend([s] * int(pedidos[s]))
                en_pedido[s] += pedidos[s]

    # ---------------------------------------------------------------- volcado
    def guardar(nombre: str, filas: list, columnas: list | None = None) -> pd.DataFrame:
        df = pd.DataFrame(filas)
        df = df[[c for c in (columnas or df.columns) if not str(c).startswith("_")]]
        df.to_csv(CARPETA / f"{nombre}.csv", index=False, encoding="utf-8")
        print(f"{nombre:<22} {len(df):>8} filas")
        return df

    mv = pd.DataFrame(movs).sort_values(["FechaHora", "MovimientoID"])
    mv["Fecha"] = mv["FechaHora"].dt.date.astype(str)
    mv.loc[mv["Tipo"] == "Stock inicial", "Fecha"] = INICIO.isoformat()
    mv["Hora"] = mv["FechaHora"].dt.hour
    mv.loc[mv["Tipo"] == "Stock inicial", "Hora"] = 0
    mv["FechaHora"] = mv["FechaHora"].dt.strftime("%Y-%m-%d %H:%M:%S")
    guardar("Movimientos", mv.to_dict("records"),
            ["MovimientoID", "FechaHora", "Fecha", "Hora", "Tipo", "Signo", "SKU", "UbicacionID", "MuelleID",
             "CamionID", "OperarioID", "ProveedorID", "DestinoID", "DuracionMin"])
    guardar("Calendario", cal)
    guardar("Horas", horas)
    guardar("Zonas", [{"ZonaID": z, "Zona": n, "Orden": o, "Descripción": t,
                       "Capacidad (palets)": sum(1 for s in slots if s["ZonaID"] == z)} for z, n, o, t in ZONAS])
    guardar("Pasillos", [{"Pasillo": p, "Orden pasillo": i + 1, "ZonaID": ZONA_DE[p], "Y": Y_FILA[p],
                          "Capacidad (palets)": HUECOS * NIVELES * POSICIONES} for i, p in enumerate(PASILLOS)])
    guardar("Ubicaciones", slots)
    guardar("Productos", productos)
    guardar("Proveedores", proveedores)
    guardar("Destinos", [{"DestinoID": i, "Destino": n, "Latitud": la, "Longitud": lo} for i, n, la, lo, _ in DESTINOS])
    guardar("Muelles", muelles)
    guardar("Operarios", operarios)
    guardar("Camiones", [c for c in camiones if c["Fecha"] >= INICIO.isoformat()])
    guardar("StockDiario", stock_diario)
    guardar("OcupacionHoraria", ocup_horaria)

    # --------------------------------------------------------- comprobaciones
    sd = pd.DataFrame(stock_diario)
    por_dia = sd.groupby("Fecha").agg(stock=("Stock final (palets)", "sum"), dem=("Demanda (palets)", "sum"),
                                      serv=("Servidos (palets)", "sum"), ent=("Entradas (palets)", "sum"))
    por_dia["ocup"] = por_dia["stock"] / CAP
    por_dia.index = pd.to_datetime(por_dia.index)
    mes = por_dia.resample("MS").agg({"ocup": ["mean", "max"], "ent": "sum", "serv": "sum", "dem": "sum"})
    print("\nPor mes: ocupación media / máxima, entradas, salidas, servicio")
    for idx, r in mes.iterrows():
        servicio = r[("serv", "sum")] / r[("dem", "sum")] if r[("dem", "sum")] else 1
        print(f"  {idx:%Y-%m}  {r[('ocup', 'mean')]:.1%} / {r[('ocup', 'max')]:.1%}   "
              f"{int(r[('ent', 'sum')]):>6} {int(r[('serv', 'sum')]):>6}   {servicio:.2%}")
    print(f"\nNivel de servicio anual: {sd['Servidos (palets)'].sum() / sd['Demanda (palets)'].sum():.2%}")
    print(f"Palets que esperaron hueco en playa: {contador['sin_hueco']}")
    oh = pd.DataFrame(ocup_horaria)
    assert oh["Ocupadas"].max() <= HUECOS * NIVELES * POSICIONES, "un pasillo supera su capacidad"
    assert (mv["UbicacionID"].notna()).all()


if __name__ == "__main__":
    main()
