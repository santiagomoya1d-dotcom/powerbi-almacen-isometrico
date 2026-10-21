# Guía para agentes de IA

Este repositorio es una plantilla: un informe de Power BI que dibuja un almacén en 3D isométrico (Deneb + Vega) y se adapta a otro almacén cambiando **un archivo de configuración** y, si se quiere, **los datos**. Esta guía dice qué tocar para cada cambio, en qué orden y cómo comprobarlo. Para personas, el punto de entrada es el [README](README.md).

## Regla de oro

**No edites a mano lo que se genera.** Cambia la configuración o el script que lo genera y vuelve a construir:

| Archivo generado | Lo genera |
|---|---|
| `Prj1_Almacen/datos/*.csv` | `generador/generar_datos.py` (simulación) o `generador/completar_datos.py` (datos reales) |
| `Prj1_Almacen/deneb/almacen_isometrico.vega.json` | `deneb/construir_escena.py` |
| `Prj1_Almacen.Report/definition/pages/almacen/**` y el tema y fondo de `StaticResources/RegisteredResources/` | `generador/pagina_almacen.py` |

El modelo semántico (`Prj1_Almacen.SemanticModel/definition/**/*.tmdl`) **no** se genera: ya lee todo de las tablas, así que cambiar filas, muelles o categorías no exige tocarlo.

## Mapa

```
Prj1_Almacen.pbip                     se abre con Power BI Desktop
Prj1_Almacen.Report/                  informe PBIR (lo escribe pagina_almacen.py)
Prj1_Almacen.SemanticModel/           modelo TMDL: tablas, relaciones y medidas DAX
Prj1_Almacen/
  almacen.config.json                 ÚNICA descripción del almacén
  construir.py                        orquesta todo: datos → comprobación → escena → página
  CONTRATO_DE_DATOS.md                tablas y columnas para datos reales
  generador/
    configuracion.py                  lee y valida la configuración (lista todos los problemas)
    contrato.py                       columnas que espera cada CSV (igual que Power Query)
    generar_datos.py                  simulador de un año, palet a palet (semilla fija)
    completar_datos.py                datos reales: deriva las tablas que faltan
    comprobar_datos.py                valida datos/ contra el contrato y la configuración
    pagina_almacen.py                 escribe la página PBIR
  deneb/construir_escena.py           geometría isométrica y especificación Vega
  herramientas/
    banco.py                          dibuja la escena con datos de muestra en un HTML, sin Power BI
    validar_pbir.py                   valida el informe contra los esquemas JSON de Microsoft
  ejemplos/almacen-10-filas.config.json   otra configuración de ejemplo
  informe/                            tema y fondo (fuente; se copian al informe)
  objetos-visuales/                   Deneb y HTML Content (.pbiviz)
```

## Requisitos

- Python 3.11 o posterior con `pandas` y `numpy`.
- Para `validar_pbir.py`: `jsonschema` y `referencing`, además de conexión a internet.
- Ejecuta los scripts desde `Prj1_Almacen/` (también funcionan desde otra carpeta: las rutas se resuelven solas).

## Recetas

Todas terminan igual: `python construir.py` (o la variante que se indica) y, en Power BI Desktop, «Actualizar» y «Aplicar cambios externos».

| Petición | Qué cambiar | Cómo construir |
|---|---|---|
| «Mi almacén tiene 10 filas» o «se llaman de otra forma» | `estanterias.filas` (de la más cercana a los muelles a la más lejana). Revisa `zonas`, porque cada fila debe estar en una sola zona y las de una zona deben ser consecutivas; o borra `zonas` para que se repartan solas. | `python construir.py` |
| Otros huecos, niveles o palets por hueco | `estanterias.huecos_por_fila`, `niveles`, `palets_por_hueco` | `python construir.py` |
| Otros muelles | `muelles.entrada` y `muelles.salida`: un número o una lista de identificadores (sin comas) | `python construir.py` |
| Otras categorías | `categorias`: `nombre`, `nombre_corto` (leyenda), `color`; opcionales `color_claro` y `color_oscuro` (caras 3D; si faltan, se calculan) y `simulacion` (solo para el simulador) | `python construir.py` (o `--datos-reales <carpeta>`) |
| Solo colores o nombres cortos de categoría | `categorias[].color…`, `nombre_corto` | `python construir.py --sin-datos` |
| Nombre del almacén, cabecera o día por defecto | `almacen.*` | `python construir.py --sin-datos` |
| Horario del selector de horas o la hora por defecto | `vista.*` | `python construir.py --sin-datos` |
| Usar datos reales de un SGA | Lee `Prj1_Almacen/CONTRATO_DE_DATOS.md`. Pon los CSV en una carpeta aparte y ajusta la configuración a ese almacén. | `python construir.py --datos-reales <carpeta>` |
| Probar una configuración sin tocar nada | Copia la configuración y edítala | `python construir.py --config <copia.json> --prueba <carpeta fuera del repo>`; abre `<carpeta>/banco.html` |
| Cambiar el aspecto de la escena 3D | Constantes y expresiones de `deneb/construir_escena.py` (paletas ABC y días, medidas de racks, camiones…) | `python construir.py --sin-datos` |
| Cambiar la simulación (volumen, temporadas) | `simulacion` y `categorias[].simulacion` de la configuración; festivos y fechas de campaña en `generar_datos.py` | `python construir.py` |

## Cómo comprobar

1. `python construir.py` para en el primer fallo y dice cuál es. Valida la configuración (todos los problemas a la vez) y los datos (`comprobar_datos.py`).
2. **Escena sin Power BI:** `python herramientas/banco.py --vista "AAAA-MM-DD HH@categoria@C"` escribe `herramientas/banco.html`. Para verlo, sirve la carpeta con `python -m http.server` y ábrelo en un navegador. Formato de cada vista: `fecha hora@modo@fila@categoría`, donde el modo es `abc`, `dias` o `categoria`, la fila es la del modo corte y la categoría es la que se resalta; se pueden poner varias `--vista`.
3. **Informe:** `python herramientas/validar_pbir.py` debe terminar con «Archivos con errores: 0».
4. **Modelo:** si tienes acceso al servidor MCP de modelado de Power BI con Desktop abierto, no debe haber medidas con error: `EVALUATE FILTER(INFO.MEASURES(), [State] <> 1)` tiene que devolver una tabla vacía.

## Cosas que no son evidentes

- **Orden de las filas.** La primera de `estanterias.filas` es la de junto a los muelles. Contando desde delante, las filas alternan cara al pasillo de delante y cara al de detrás, y cada pareja va espalda con espalda. La escena calcula sola pasillos, fondo y ancho del edificio; el edificio se ensancha si los muelles no caben.
- **Colores de categoría.** Viajan como datos: tabla `Categorías`, medida `Paleta de categorías` (texto `#claro,#medio,#oscuroNombre|…`) y lectura en Vega. Por eso una categoría nueva no exige tocar la escena, y su nombre no puede llevar `|`.
- **Medidas que dependen de tablas, no de listas.** Las fichas de muelles (`HTML · Indicadores`) salen de `Muelles`, la leyenda de `Categorías` y el selector de filas (tabla calculada `Fila en foco`) de `Pasillos`. Usan `ALLNOBLANKROW` porque los movimientos sin muelle crean la fila en blanco de `Muelles`.
- **DAX y nombres con tilde.** Los nombres de tabla con tildes van entre comillas simples: `'Categorías'`, `'Almacén'`.
- **Stock por reconstrucción.** `Palets en stock` suma `Movimientos[Signo]` hasta el momento elegido. Si un hueco llega a tener dos palets a la vez en los datos, el 3D lo pinta mal; `comprobar_datos.py` lo detecta.
- **Semilla fija.** Con la configuración de serie, `generar_datos.py` produce siempre los mismos CSV, byte a byte. Si cambias el simulador y quieres conservar el año publicado, compara `datos/` antes y después.
- **Saltos de línea.** Los `.py`, `.md` y `.json` de `Prj1_Almacen/` usan LF; los CSV, el `.vega.json` y los TMDL usan CRLF, como los escribe Power BI. Respétalo para no ensuciar los diffs.
- **Power BI Desktop.** Si el modelo se cambia con el servidor MCP mientras Desktop está abierto, después hay que llevar los cambios a los TMDL: exporta con `ExportToTmdlFolder` y copia los archivos que difieran, salvo `database.tmdl`. Si Desktop guarda después de que hayas escrito la página, la pisa: vuelve a lanzar `pagina_almacen.py`.

## Lo que no hay que hacer

- No metas datos reales de nadie en el repositorio público. Los de serie son ficticios y así se declaran (`almacen.datos_ficticios`).
- No subas `.pbi/localSettings.json` ni `.pbi/cache.abf`: están en `.gitignore`.
- No cambies los identificadores de los objetos visuales ni las versiones de esquema a mano: `pagina_almacen.py` los lee de lo que guardó Desktop.
