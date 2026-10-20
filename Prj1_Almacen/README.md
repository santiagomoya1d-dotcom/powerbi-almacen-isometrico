# Prj1_Almacen · notas técnicas

Piezas que generan el informe `../Prj1_Almacen.pbip`. **Todos los datos son ficticios.** Para la visión general, ver el [README principal](../README.md).

## Qué hay en esta carpeta

| Carpeta / archivo | Qué es |
|---|---|
| `generador/generar_datos.py` | Simula un año (1/10/2025 – 30/9/2026) de un centro de distribución, palet a palet, y escribe los CSV en `datos/`. |
| `datos/*.csv` | Las 14 tablas que lee Power BI (UTF-8, separador coma, decimales con punto). |
| `deneb/construir_escena.py` | Genera `deneb/almacen_isometrico.vega.json`: el almacén isométrico 2:1 (losa, muros, estanterías, palets, carretillas, camiones, muelles, modo corte). |
| `generador/pagina_almacen.py` | Escribe la página «Almacén en vivo» en formato PBIR dentro de `../Prj1_Almacen.Report`. |
| `informe/` | Tema oscuro (`TemaAlmacenOscuro.json`) y fondo de página (`FondoAlmacen.png`), diseñado en Figma. |
| `objetos-visuales/` | Deneb 2.0.1 y HTML Content 2.0.0, versiones «standalone» oficiales (licencia MIT, ver `LICENCIAS-TERCEROS.md`). |
| `BRIEFING_LINKEDIN.md` | Contexto del proyecto para redactar la publicación. |

## Regenerar

Desde esta carpeta, con Python 3.11 o posterior y `pandas` y `numpy` instalados:

```
python generador/generar_datos.py      # datos/*.csv (semilla fija: sale siempre lo mismo)
python deneb/construir_escena.py       # deneb/almacen_isometrico.vega.json
python generador/pagina_almacen.py     # página PBIR en ../Prj1_Almacen.Report
```

Después, en Power BI Desktop: «Actualizar» si cambiaron los datos, y «Aplicar cambios externos» si cambió la página.

## El almacén simulado

- 8 filas de estanterías (A junto a los muelles, H al fondo), 12 huecos, 6 niveles y 3 palets por hueco: **1.728 ubicaciones**.
- Zonas: Z1 alta rotación (A–B), Z2 rotación media (C–F) y Z3 reserva (G–H). Los productos A van a Z1 y a los niveles bajos.
- 300 productos en 7 categorías, 20 proveedores que entregan 3 o 5 días por semana, 10 destinos.
- 6 muelles de entrada (sobre todo por la mañana) y 6 de salida (sobre todo por la tarde). 11 operarios en dos turnos.
- Reposición con punto de pedido y nivel objetivo. La simulación arranca 28 días antes para que el 1 de octubre ya haya pedidos en camino.
- Temporadas: Black Friday, Navidad (con una categoría de turrones y cava) y verano para bebidas.

Resultado: 48.380 palets de entrada, 48.429 de salida, 7.084 camiones, ocupación media del 71 % con picos del 100 % en noviembre y diciembre, y nivel de servicio del 99,5 %.

## Medidas clave

- `Palets en stock`: reconstruye la ocupación en el día y la hora elegidos sumando entradas y restando salidas hasta ese momento. Por ubicación vale 1 o 0: es la base del almacén isométrico.
- `Fecha elegida`: el día pinchado en la curva anual o, si no hay ninguno, el 16/12/2025 (pico de Navidad).
- `SKU / Producto / Clase ABC / Categoría en ubicación`, `Días en stock` y `Actividad en la hora`: qué hay en cada hueco y si se movió en esa hora.
- `Muelles con camión`, `Entradas / Salidas en la hora`, `Modo de color` y `Fila en foco`: lo que necesita la escena 3D.
- `HTML · Cabecera`, `HTML · Indicadores` y `HTML · Leyenda`: HTML y CSS animados para el objeto visual HTML Content.
- Además: inventario (`Stock al cierre`, `Cobertura`, `Nivel de servicio %`), ocupación hora a hora, productividad y simulador (`Palets extra por día` → `Días hasta llenar`).

Comprobado: en 180 momentos de muestra, el stock calculado desde los movimientos coincide al palet con la foto horaria.
