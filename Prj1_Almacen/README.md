# Prj1_Almacen · notas técnicas

Piezas que generan el informe `../Prj1_Almacen.pbip`. **Todos los datos son ficticios.** Para la visión general, ver el [README principal](../README.md); para adaptarlo con un agente de IA, la [guía para agentes](../AGENTS.md).

## Qué hay en esta carpeta

| Carpeta / archivo | Qué es |
|---|---|
| `almacen.config.json` | La descripción del almacén: filas, huecos, niveles, palets por hueco, zonas, muelles, categorías con sus colores, horario de la vista, nombre y parámetros de la simulación. Todo lo demás se deriva de aquí. |
| `construir.py` | Lo construye todo en orden y para en el primer fallo: datos, comprobación, escena y página. |
| `CONTRATO_DE_DATOS.md` | Las tablas y columnas que lee el modelo, para sustituir la simulación por datos reales. |
| `generador/configuracion.py` | Lee y valida la configuración; si algo no cuadra, lista todos los problemas. |
| `generador/generar_datos.py` | Simula un año (1/10/2025 – 30/9/2026) de un centro de distribución, palet a palet, y escribe los CSV en `datos/`. |
| `generador/completar_datos.py` | Con datos reales: a partir de ubicaciones, movimientos, productos y camiones calcula el resto de tablas. |
| `generador/comprobar_datos.py` | Valida `datos/` contra el contrato y la configuración. Comprueba, por ejemplo, que ningún hueco tenga dos palets a la vez. |
| `generador/contrato.py` | Columnas que espera cada CSV, las mismas que las consultas de Power Query del modelo. |
| `generador/pagina_almacen.py` | Escribe la página «Almacén en vivo» en formato PBIR dentro de `../Prj1_Almacen.Report`. |
| `deneb/construir_escena.py` | Genera `deneb/almacen_isometrico.vega.json`: el almacén isométrico 2:1 (losa, muros, estanterías, palets, carretillas, camiones, muelles y modo corte), con la disposición calculada a partir de la configuración. |
| `datos/*.csv` | Las 16 tablas que lee Power BI (UTF-8, separador coma, decimales con punto). |
| `herramientas/banco.py` | Dibuja la escena con datos de muestra en un HTML, sin Power BI. |
| `herramientas/validar_pbir.py` | Valida el informe contra los esquemas JSON públicos de Microsoft. |
| `ejemplos/` | Otra configuración (10 filas, 5 categorías, 3+5 muelles) para probar la plantilla. |
| `informe/` | Tema oscuro (`TemaAlmacenOscuro.json`) y fondo de página (`FondoAlmacen.png`), diseñado en Figma. |
| `objetos-visuales/` | Deneb 2.0.1 y HTML Content 2.0.0, versiones «standalone» oficiales (licencia MIT, ver `LICENCIAS-TERCEROS.md`). |
| `BRIEFING_LINKEDIN.md` | Contexto del proyecto para redactar la publicación. |

## Regenerar

Desde esta carpeta, con Python 3.11 o posterior y `pandas` y `numpy` instalados:

```
python construir.py                          # todo, con la simulación (semilla fija: sale siempre lo mismo)
python construir.py --datos-reales mis_datos # con tus CSV en lugar de simular
python construir.py --sin-datos              # sin tocar los datos: nombre, colores, horario, escena y página
python construir.py --config ejemplos/almacen-10-filas.config.json --prueba ../../prueba
                                             # otra variante en una carpeta aparte, con banco.html para verla
```

Los pasos sueltos también funcionan: `generador/generar_datos.py`, `generador/comprobar_datos.py`, `deneb/construir_escena.py` y `generador/pagina_almacen.py`. Todos aceptan `--config`.

Después, en Power BI Desktop: «Actualizar» si cambiaron los datos, y «Aplicar cambios externos» si cambió la página.

## Cómo se adapta

- **Escena 3D.** La primera fila de la configuración es la de junto a los muelles. Contando desde delante, las filas alternan cara al pasillo de delante y cara al de detrás, y cada pareja va espalda con espalda. Con eso, el script calcula pasillos, zonas pintadas en el suelo, fondo y ancho del edificio, posición de los muelles, playas y encuadre.
- **Colores de categoría.** Salen de la tabla `Categorías`. La medida `Paleta de categorías` se los pasa a Vega en un texto (`#claro,#medio,#oscuroNombre|…`), las barras usan `Color de categoría` con formato condicional y la leyenda se construye con `CONCATENATEX`.
- **Muelles y filas.** Las fichas de muelles de `HTML · Indicadores` salen de la tabla `Muelles` y el selector del modo corte (tabla calculada `Fila en foco`) de `Pasillos`.
- **Cabecera y día por defecto.** Salen de la tabla `Almacén`, de una sola fila.

## El almacén simulado (configuración de serie)

- 8 filas de estanterías (A junto a los muelles, H al fondo), 12 huecos, 6 niveles y 3 palets por hueco: **1.728 ubicaciones**.
- Zonas: Z1 alta rotación (A–B), Z2 rotación media (C–F) y Z3 reserva (G–H). Los productos A van a Z1 y a los niveles bajos.
- 300 productos en 7 categorías, 20 proveedores que entregan 3 o 5 días por semana, 10 destinos.
- 6 muelles de entrada (sobre todo por la mañana) y 6 de salida (sobre todo por la tarde). 11 operarios en dos turnos.
- Reposición con punto de pedido y nivel objetivo. La simulación arranca 28 días antes para que el 1 de octubre ya haya pedidos en camino.
- Temporadas: Black Friday, Navidad (con una categoría de turrones y cava) y verano para bebidas.

Resultado: 48.380 palets de entrada, 48.429 de salida, 7.084 camiones, ocupación media del 71 % con picos del 100 % en noviembre y diciembre, y nivel de servicio del 99,5 %.

## Medidas clave

- `Palets en stock`: reconstruye la ocupación en el día y la hora elegidos sumando entradas y restando salidas hasta ese momento. Por ubicación vale 1 o 0: es la base del almacén isométrico.
- `Fecha elegida`: el día pinchado en la curva anual o, si no hay ninguno, la fecha por defecto de la tabla `Almacén` (el 16/12/2025, pico de Navidad, en la configuración de serie).
- `SKU / Producto / Clase ABC / Categoría en ubicación`, `Días en stock` y `Actividad en la hora`: qué hay en cada hueco y si se movió en esa hora.
- `Muelles con camión`, `Entradas / Salidas en la hora`, `Modo de color`, `Fila en foco` y `Paleta de categorías`: lo que necesita la escena 3D.
- `HTML · Cabecera`, `HTML · Indicadores` y `HTML · Leyenda`: HTML y CSS animados para el objeto visual HTML Content.
- Además: inventario (`Stock al cierre`, `Cobertura`, `Nivel de servicio %`), ocupación hora a hora, productividad y simulador (`Palets extra por día` → `Días hasta llenar`).

Comprobado:

- En 180 momentos de muestra, el stock calculado desde los movimientos coincide al palet con la foto horaria.
- Con la configuración de serie, el simulador saca el mismo año byte a byte antes y después de convertirlo en plantilla.
- Partiendo solo de las columnas obligatorias del contrato, `completar_datos.py` reconstruye exactamente la ocupación hora a hora del simulador (70.080 filas).
