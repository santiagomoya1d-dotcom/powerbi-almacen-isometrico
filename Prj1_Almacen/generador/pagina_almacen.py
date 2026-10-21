# -*- coding: utf-8 -*-
"""
Escribe la página «Almacén en vivo» del informe en formato PBIR (archivos de texto del proyecto PBIP).

Uso:     python pagina_almacen.py            (busca Prj1_Almacen.Report en la raíz del repositorio)
         python pagina_almacen.py [--config otra.config.json] [--proyecto "<carpeta con Prj1_Almacen.Report>"]
Después: en Power BI Desktop, «Aplicar cambios externos» (o cerrar y abrir el .pbip).

Lee de los archivos que ya guardó Power BI las versiones de esquema y los identificadores de
Deneb y HTML Content, para escribir lo mismo que escribiría Desktop. De almacen.config.json toma
las horas del selector, la hora por defecto y el número de filas del selector de modo corte.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from configuracion import argumentos, cargar

RAIZ = Path(__file__).resolve().parent.parent          # carpeta Prj1_Almacen (generador, deneb, informe…)
_p = argumentos("Escribe la página «Almacén en vivo» del informe (PBIR).")
_p.add_argument("--proyecto", help="carpeta que contiene Prj1_Almacen.Report (por defecto, la raíz del repositorio)")
_p.add_argument("--escena", help="especificación Vega (por defecto, deneb/almacen_isometrico.vega.json)")
ARGS = _p.parse_args()
CFG = cargar(ARGS.config)
PROYECTO = Path(ARGS.proyecto) if ARGS.proyecto else next(
    c for c in (RAIZ, RAIZ.parent) if any(c.glob("*.Report")))   # raíz del repositorio, junto al .pbip
INFORME = next(PROYECTO.glob("*.Report"))
DEF = INFORME / "definition"
PAGINA = "almacen"
TEMA = "TemaAlmacenOscuro.json"
FONDO = "FondoAlmacen.png"

ESQ = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"


def leer(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def escribir(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def esquema(nombre: str, defecto: str) -> str:
    """Versión de esquema que ya usa Desktop en este proyecto para ese tipo de archivo."""
    for f in DEF.rglob(f"{nombre}.json"):
        s = leer(f).get("$schema")
        if s:
            return s
    if nombre == "visual":
        # Sin objetos visuales todavía: la versión que declara el informe para esta versión de Desktop
        version = leer(DEF / "report.json").get("themeCollection", {}).get("baseTheme", {}) \
            .get("reportVersionAtImport", {})
        if isinstance(version, dict) and version.get("visual"):
            return f"{ESQ}/visualContainer/{version['visual']}/schema.json"
    return f"{ESQ}/{defecto}/schema.json"


# ----------------------------------------------------------------- expresiones
def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def texto(s: str):
    return lit("'" + s.replace("'", "''") + "'")


def color(h: str):
    return {"solid": {"color": texto(h)}}


def col(tabla: str, campo: str):
    return {"Column": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": campo}}


def med(tabla: str, campo: str):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": tabla}}, "Property": campo}}


def proy(campo: dict, nombre_corto: str | None = None):
    tipo = "Column" if "Column" in campo else "Measure"
    tabla = campo[tipo]["Expression"]["SourceRef"]["Entity"]
    prop = campo[tipo]["Property"]
    ref = f"Sum({tabla}.{prop})" if False else f"{tabla}.{prop}"
    return {"field": campo, "queryRef": ref, "nativeQueryRef": nombre_corto or prop}


def contenedor(titulo: str | None = None, fondo: str | None = None, relleno: int = 0):
    obj = {
        "background": [{"properties": {"show": lit("true" if fondo else "false")} | ({"color": color(fondo), "transparency": lit("0D")} if fondo else {})}],
        "border": [{"properties": {"show": lit("false")}}],
        "dropShadow": [{"properties": {"show": lit("false")}}],
        "visualHeader": [{"properties": {"show": lit("false")}}],
        "padding": [{"properties": {k: lit(f"{relleno}D") for k in ("top", "bottom", "left", "right")}}],
        "title": [{"properties": {"show": lit("true" if titulo else "false")} | ({"text": texto(titulo), "fontColor": color("#94A3B8"), "fontSize": lit("11D")} if titulo else {})}],
    }
    return obj


def visual(nombre: str, x, y, ancho, alto, z, cuerpo: dict, filtros: dict | None = None) -> dict:
    v = {
        "$schema": esquema("visual", "visualContainer/2.13.0"),
        "name": nombre,
        "position": {"x": x, "y": y, "z": z, "width": ancho, "height": alto, "tabOrder": z},
        "visual": cuerpo,
    }
    if filtros:
        v["filterConfig"] = filtros
    return v


def filtro_in(tabla: str, campo: str, valor_literal: str):
    return {
        "Version": 2,
        "From": [{"Name": "t", "Entity": tabla, "Type": 0}],
        "Where": [{"Condition": {"In": {
            "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "t"}}, "Property": campo}}],
            "Values": [[{"Literal": {"Value": valor_literal}}]]}}}],
    }


# --------------------------------------------------------------- objetos visuales
def identificador(nombre: str) -> str:
    """GUID del objeto visual (de AppSource o importado desde archivo, p. ej. STANDALONEdeneb…)."""
    rep = DEF / "report.json"
    ids = list(leer(rep).get("publicCustomVisuals", [])) if rep.exists() else []
    if rep.exists():
        for paquete in leer(rep).get("resourcePackages", []):
            ids += [paquete.get("name", "")] + [i.get("name", "") for i in paquete.get("items", [])]
    ids += [leer(f).get("visual", {}).get("visualType", "") for f in DEF.rglob("visual.json")]
    ids += [c.name for c in (INFORME / "CustomVisuals").glob("*")] if (INFORME / "CustomVisuals").exists() else []
    for i in ids:
        if nombre.lower() in i.lower():
            return i
    raise SystemExit(f"No encuentro el objeto visual {nombre} en el informe: impórtalo y guarda.")


def html(nombre, x, y, ancho, alto, z, medida, guid):
    return visual(nombre, x, y, ancho, alto, z, {
        "visualType": guid,
        "query": {"queryState": {"content": {"projections": [proy(med("Medidas", medida))]}}},
        "objects": {"contentFormatting": [{"properties": {"format": texto("html"), "renderMode": texto("rebuild"),
                                                          "userSelect": lit("false"), "noDataMessage": texto("")}}],
                    # Lo añade Desktop al guardar: se escribe igual para que el repositorio no cambie solo
                    "compatibility": [{"properties": {"legacyRendering": lit("true")}}]},
        "visualContainerObjects": contenedor(),
        "drillFilterOtherVisuals": True,
    })


def deneb(nombre, x, y, ancho, alto, z, guid, spec: str):
    campos = [col("Ubicaciones", c) for c in ("UbicacionID", "Pasillo", "Hueco", "Nivel", "Posición")]
    campos += [med("Medidas", m) for m in (
        "Palets en stock", "Ocupada sin filtros", "Producto en ubicación", "Clase ABC en ubicación",
        "Categoría en ubicación", "Días en stock", "Muelles con camión", "Entradas en la hora",
        "Salidas en la hora", "Modo de color", "Actividad en la hora", "Fila en foco", "Paleta de categorías")]
    return visual(nombre, x, y, ancho, alto, z, {
        "visualType": guid,
        "query": {"queryState": {"dataset": {"projections": [proy(c) for c in campos]}}},
        "objects": {"vega": [{"properties": {
            "provider": texto("vega"),
            "jsonSpec": texto(spec),
            "jsonConfig": texto("{}"),
            "renderMode": texto("canvas"),
            "enableTooltips": lit("true"),
            "enableContextMenu": lit("true"),
            "enableSelection": lit("false"),
            "enableHighlight": lit("false"),
        }}]},
        "visualContainerObjects": contenedor(),
        "drillFilterOtherVisuals": True,
    })


def segmentador(nombre, x, y, ancho, alto, z, tabla, campo, valor_literal, filtros=None):
    return visual(nombre, x, y, ancho, alto, z, {
        "visualType": "slicer",
        "query": {"queryState": {"Values": {"projections": [proy(col(tabla, campo))]}}},
        "objects": {
            "data": [{"properties": {"mode": texto("Basic")}}],
            "general": [{"properties": {"orientation": lit("1D"),
                                        "filter": {"filter": filtro_in(tabla, campo, valor_literal)}}}],
            "selection": [{"properties": {"singleSelect": lit("true"), "strictSingleSelect": lit("true"),
                                          "selectAllCheckboxEnabled": lit("false")}}],
            "header": [{"properties": {"show": lit("false")}}],
            "items": [{"properties": {"fontColor": color("#CBD5E1"), "background": color("#111B2E"),
                                      "outline": texto("Frame"), "outlineColor": color("#22324D"),
                                      "textSize": lit("11D")}}],
        },
        "visualContainerObjects": contenedor(),
        "drillFilterOtherVisuals": True,
    }, filtros)


def botonera(nombre, x, y, ancho, alto, z, tabla, campo, valor_literal, columnas, filtros=None, letra=11):
    """Segmentador de botones (fichas redondeadas, una fila) con estilo propio para la opción elegida."""
    def por_estado(objeto, normal, elegido, encima=None):
        filas = [{"properties": normal, "selector": {"id": "default"}},
                 {"properties": elegido, "selector": {"id": "selection:selected"}}]
        if encima:
            filas.append({"properties": encima, "selector": {"id": "interaction:hover"}})
        return filas

    return visual(nombre, x, y, ancho, alto, z, {
        "visualType": "advancedSlicerVisual",
        "query": {"queryState": {"Values": {"projections": [proy(col(tabla, campo))]}}},
        "objects": {
            "general": [{"properties": {"filter": {"filter": filtro_in(tabla, campo, valor_literal)}}}],
            "selection": [{"properties": {"singleSelect": lit("true"), "strictSingleSelect": lit("true"),
                                          "selectAllCheckboxEnabled": lit("false")}}],
            "layout": [{"properties": {"style": texto("Cards"), "orientation": lit("2L"), "rowCount": lit("1L"),
                                       "columnCount": lit(f"{columnas}L"), "autoGrid": lit("false"),
                                       "cellPadding": lit("4L"), "maxTiles": lit(f"{columnas}L")}}],
            "shapeCustomRectangle": [{"properties": {"tileShape": texto("rectangleRoundedByPixel"),
                                                     "rectangleRoundedCurve": lit("8L")}}],
            "fillCustom": por_estado("fillCustom",
                                     {"show": lit("true"), "fillColor": color("#0C1322"), "transparency": lit("0D")},
                                     {"show": lit("true"), "fillColor": color("#2DD4BF"), "transparency": lit("0D")},
                                     {"show": lit("true"), "fillColor": color("#16233B"), "transparency": lit("0D")}),
            "outline": por_estado("outline",
                                  {"show": lit("true"), "lineColor": color("#22324D"), "weight": lit("1D"), "transparency": lit("0D")},
                                  {"show": lit("true"), "lineColor": color("#5EEAD4"), "weight": lit("1D"), "transparency": lit("0D")}),
            "value": por_estado("value",
                                {"show": lit("true"), "fontColor": color("#94A3B8"), "fontSize": lit(f"{letra}D"),
                                 "fontFamily": texto("Segoe UI Semibold"), "horizontalAlignment": texto("center")},
                                {"show": lit("true"), "fontColor": color("#04211D"), "fontSize": lit(f"{letra}D"),
                                 "fontFamily": texto("Segoe UI Semibold"), "horizontalAlignment": texto("center")}),
            # Sin brillo: Power BI encoge la ficha para dejarle sitio y el texto se cortaba
            "glowCustom": [{"properties": {"show": lit("false")}}],
            "label": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": contenedor(),
        "drillFilterOtherVisuals": True,
    }, filtros)


def curva(nombre, x, y, ancho, alto, z):
    return visual(nombre, x, y, ancho, alto, z, {
        "visualType": "areaChart",
        "query": {"queryState": {
            "Category": {"projections": [proy(col("Calendario", "Fecha")) | {"active": True}]},
            "Y": {"projections": [proy(med("Medidas", "Ocupación horaria %"))]},
        }},
        "objects": {
            "dataPoint": [{"properties": {"fill": color("#2DD4BF")}}],
            "lineStyles": [{"properties": {"strokeWidth": lit("2D")}}],
            "valueAxis": [{"properties": {"start": lit("0.4D"), "end": lit("1D"), "gridlineShow": lit("true"),
                                          "labelColor": color("#64748B"), "gridlineColor": color("#1E293B")}}],
            "categoryAxis": [{"properties": {"labelColor": color("#64748B"), "showAxisTitle": lit("false")}}],
            "legend": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": contenedor(),
        "drillFilterOtherVisuals": True,
    })


def barras(nombre, x, y, ancho, alto, z):
    # Color de cada barra por valor de campo (fx): la medida «Color de categoría» lee la tabla Categorías,
    # así que una categoría nueva sale con su color sin tocar este archivo
    colores = [{"properties": {"fill": {"solid": {"color": {"expr": med("Medidas", "Color de categoría")}}}},
                "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}]
    return visual(nombre, x, y, ancho, alto, z, {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {"projections": [proy(col("Categorías", "Categoría")) | {"active": True}]},
                "Y": {"projections": [proy(med("Medidas", "Palets en stock"))]},
            },
            "sortDefinition": {"sort": [{"field": med("Medidas", "Palets en stock"), "direction": "Descending"}],
                               "isDefaultSort": True},
        },
        "objects": {
            "dataPoint": colores,
            "labels": [{"properties": {"show": lit("true"), "color": color("#E2E8F0"), "fontSize": lit("10D")}}],
            "valueAxis": [{"properties": {"show": lit("false"), "gridlineShow": lit("false")}}],
            "categoryAxis": [{"properties": {"labelColor": color("#CBD5E1"), "fontSize": lit("10D")}}],
        },
        "visualContainerObjects": contenedor(),
        "drillFilterOtherVisuals": True,
    })


# ------------------------------------------------------------------------ tema
def registrar_tema() -> None:
    rep_path = DEF / "report.json"
    rep = leer(rep_path)
    destino = INFORME / "StaticResources" / "RegisteredResources" / TEMA
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RAIZ / "informe" / TEMA, destino)
    tc = rep.setdefault("themeCollection", {})
    base = tc.get("baseTheme", {})
    tc["customTheme"] = {"name": TEMA, "reportVersionAtImport": base.get("reportVersionAtImport", "5.66"),
                         "type": "RegisteredResources"}
    paquetes = rep.setdefault("resourcePackages", [])
    reg = next((p for p in paquetes if p.get("type") == "RegisteredResources"), None)
    if reg is None:
        reg = {"name": "RegisteredResources", "type": "RegisteredResources", "items": []}
        paquetes.append(reg)
    reg["items"] = [i for i in reg.get("items", []) if i.get("name") not in (TEMA, FONDO)]
    reg["items"].append({"name": TEMA, "path": TEMA, "type": "CustomTheme"})
    # Fondo de página diseñado en Figma (archivo «Almacén CD-01 · Power BI»)
    shutil.copyfile(RAIZ / "informe" / FONDO, destino.parent / FONDO)
    reg["items"].append({"name": FONDO, "path": FONDO, "type": "Image"})
    escribir(rep_path, rep)


# --------------------------------------------------------------------- página
def main() -> None:
    g_deneb = identificador("deneb")
    g_html = identificador("htmlContent")
    ruta_escena = Path(ARGS.escena) if ARGS.escena else RAIZ / "deneb" / "almacen_isometrico.vega.json"
    spec = ruta_escena.read_text(encoding="utf-8")
    spec = json.dumps(json.loads(spec), ensure_ascii=False, separators=(",", ":"))

    paginas = DEF / "pages"
    meta_path = paginas / "pages.json"
    meta = leer(meta_path) if meta_path.exists() else {"$schema": f"{ESQ}/pagesMetadata/1.1.0/schema.json"}
    orden = [p for p in meta.get("pageOrder", []) if p != PAGINA]

    # Quita las páginas vacías de partida (solo con los objetos visuales de prueba, sin datos)
    for carpeta in [c for c in paginas.iterdir() if c.is_dir() and c.name != PAGINA]:
        vis = list((carpeta / "visuals").glob("*/visual.json"))
        if all(not leer(v).get("visual", {}).get("query") for v in vis):
            shutil.rmtree(carpeta)
            orden = [p for p in orden if p != carpeta.name]
            print("Página vacía eliminada:", leer(carpeta / "page.json")["displayName"] if (carpeta / "page.json").exists() else carpeta.name)

    dir_pag = paginas / PAGINA
    if dir_pag.exists():
        shutil.rmtree(dir_pag)
    escribir(dir_pag / "page.json", {
        "$schema": esquema("page", "page/2.1.0"),
        "name": PAGINA,
        "displayName": "Almacén en vivo",
        "displayOption": "FitToPage",
        "height": 1080,
        "width": 1920,
        "objects": {
            "background": [{"properties": {
                "color": color("#060A13"),
                "image": {"image": {
                    "name": texto(FONDO),
                    "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1,
                                                             "ItemName": FONDO}}},
                    "scaling": texto("Fit"),
                }},
                "transparency": lit("0D"),
            }}],
            "outspace": [{"properties": {"color": color("#04070D"), "transparency": lit("0D")}}],
        },
        "visualInteractions": [
            {"source": "barrasCategoria", "target": "almacen3d", "type": "DataFilter"},
            {"source": "barrasCategoria", "target": "indicadores", "type": "DataFilter"},
            {"source": "barrasCategoria", "target": "curvaOcupacion", "type": "NoFilter"},
            {"source": "curvaOcupacion", "target": "barrasCategoria", "type": "DataFilter"},
        ],
    })

    filtro_horas = {"filters": [{
        "name": "horasDeTrabajo",
        "field": col("Horas", "Hora"),
        "type": "Advanced",
        "filter": {"Version": 2, "From": [{"Name": "h", "Entity": "Horas", "Type": 0}], "Where": [{"Condition": {"And": {
            "Left": {"Comparison": {"ComparisonKind": 2, "Left": {"Column": {"Expression": {"SourceRef": {"Source": "h"}}, "Property": "Hora"}}, "Right": {"Literal": {"Value": f"{CFG.primera_hora}L"}}}},
            "Right": {"Comparison": {"ComparisonKind": 4, "Left": {"Column": {"Expression": {"SourceRef": {"Source": "h"}}, "Property": "Hora"}}, "Right": {"Literal": {"Value": f"{CFG.ultima_hora}L"}}}}}}}]},
        "howCreated": "User",
    }]}

    # Rejilla de la página (1920×1080), igual que el fondo diseñado en Figma:
    # escenario 3D a la izquierda (32,100 · 1328×956) y columna derecha (1384 · 504 de ancho)
    n_horas = CFG.ultima_hora - CFG.primera_hora + 1
    n_filas = len(CFG.filas) + 1                       # «Todo» y una ficha por fila
    objetos = [
        html("cabecera", 104, 20, 1784, 64, 1000, "HTML · Cabecera", g_html),
        botonera("selectorHora", 172, 114, 808, 44, 2000, "Horas", "Hora", f"{CFG.hora_por_defecto}L", n_horas, filtro_horas,
                 letra=11 if n_horas <= 16 else 9),
        botonera("selectorColor", 1048, 114, 300, 44, 3000, "Color por", "Color por", "'ABC'", 3),
        deneb("almacen3d", 40, 172, 1312, 824, 4000, g_deneb, spec),
        # Modo corte: la fila elegida pasa a primer plano y las de delante se vuelven transparentes
        # Posición y tamaño ajustados a mano en Power BI (20/10/2026)
        botonera("selectorFila", 222, 1008, 581, 40, 4500, "Fila en foco", "Fila", "'Todo'", n_filas,
                 letra=10 if n_filas <= 11 else 9),
        html("leyenda", 803, 1012, 541, 32, 5000, "HTML · Leyenda", g_html),
        html("indicadores", 1384, 100, 504, 480, 6000, "HTML · Indicadores", g_html),
        curva("curvaOcupacion", 1392, 634, 488, 134, 7000),
        barras("barrasCategoria", 1392, 830, 488, 218, 8000),
    ]
    for v in objetos:
        escribir(dir_pag / "visuals" / v["name"] / "visual.json", v)

    meta["pageOrder"] = [PAGINA] + orden
    meta["activePageName"] = PAGINA
    escribir(meta_path, meta)
    registrar_tema()
    print(f"Página escrita con {len(objetos)} objetos visuales. Deneb={g_deneb} HTML={g_html}")


if __name__ == "__main__":
    main()
