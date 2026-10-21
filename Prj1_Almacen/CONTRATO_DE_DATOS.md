# Contrato de datos

Qué tablas lee el modelo de Power BI y con qué columnas. Sirve para sustituir los datos simulados por los de un almacén real, exportados de tu sistema de gestión de almacén (SGA).

La fuente de verdad es [`generador/contrato.py`](generador/contrato.py): ahí están las mismas columnas, en el mismo orden que esperan las consultas de Power Query del modelo.

## En resumen

1. Describe tu almacén en [`almacen.config.json`](almacen.config.json): filas, huecos, niveles, palets por hueco, muelles, categorías con su color y nombre del almacén.
2. Exporta de tu SGA **cuatro tablas** en CSV (UTF-8, separador coma, fechas `AAAA-MM-DD HH:MM:SS`):
   - `Ubicaciones.csv`
   - `Movimientos.csv`
   - `Productos.csv`
   - `Camiones.csv` (opcional)
3. Déjalas en una carpeta propia, por ejemplo `mis_datos/`, y lanza:
   ```
   python construir.py --datos-reales mis_datos
   ```
   El script completa el resto de tablas en `datos/`, lo comprueba todo y regenera la escena y la página.
4. En Power BI Desktop, pulsa «Actualizar» y luego «Aplicar cambios externos».

## Las cuatro tablas que aportas tú

Las columnas en **negrita** son obligatorias; las demás pueden faltar (se crean vacías).

### Ubicaciones · una fila por hueco de palet

| Columna | Tipo | Qué es |
|---|---|---|
| **UbicacionID** | texto | Identificador único del hueco en tu SGA, por ejemplo `A-01-1-1`. |
| **Pasillo** | texto | Fila de estanterías. Debe ser una de `estanterias.filas` de la configuración. |
| **Hueco** | entero | Hueco (vano) a lo largo de la fila: de 1 a `huecos_por_fila`. El 1 queda a la izquierda, mirando desde los muelles. |
| **Nivel** | entero | Altura: de 1 (suelo) a `niveles`. |
| **Posición** | entero | Palet dentro del hueco: de 1 a `palets_por_hueco`. |
| Orden pasillo | entero | Se calcula a partir de la configuración. |
| ZonaID | texto | Si no la traes, sale de `zonas` en la configuración. |

No puede haber dos ubicaciones en la misma combinación de fila, hueco, nivel y posición. Si tu almacén tiene menos huecos que la cuadrícula de la configuración, los que falten se ven vacíos.

### Movimientos · una fila por palet que entra o sale de un hueco

| Columna | Tipo | Qué es |
|---|---|---|
| **FechaHora** | fecha y hora | Momento en que el palet se ubica o se retira. |
| **Tipo** | texto | `Entrada`, `Salida` o `Stock inicial`. |
| **Signo** | entero | `1` si entra (Entrada y Stock inicial) y `-1` si sale. |
| **SKU** | texto | Producto del palet. Debe estar en Productos. |
| **UbicacionID** | texto | Hueco. Debe estar en Ubicaciones. |
| MovimientoID | entero | Si falta, se numeran por orden de FechaHora. |
| Fecha, Hora | fecha, entero | Se calculan a partir de FechaHora. |
| MuelleID | texto | Muelle por el que entró o salió. Si lo traes, debe estar en la configuración. |
| CamionID, OperarioID, ProveedorID, DestinoID, DuracionMin | | Opcionales: los usan medidas de productividad que no salen en la página. |

**La regla importante:** el informe reconstruye qué hay en cada hueco sumando `Signo` hasta el momento elegido, así que en ningún momento un hueco puede tener más de un palet ni quedar en negativo. Para eso:

- el stock que ya había al empezar el periodo va como `Stock inicial`, con su FechaHora real de entrada (anterior al primer día);
- cada palet que sale tiene antes su entrada en ese mismo hueco.

`comprobar_datos.py` lo verifica y, si algo falla, te dice en qué huecos.

### Productos · una fila por SKU

| Columna | Tipo | Qué es |
|---|---|---|
| **SKU** | texto | Identificador único. |
| **Producto** | texto | Nombre que se ve en la ficha del palet. |
| **Categoría** | texto | Debe ser una de `categorias` de la configuración. Si no lo es, se le asigna un color automático y se avisa. |
| Clase ABC | texto | `A`, `B` o `C`. Si no la traes, se calcula por salidas: el 65 % del volumen es A, el siguiente 25 % es B y el resto es C. |
| ProveedorID, Valor palet (€), Demanda media (palets/día) | | Opcionales. |

### Camiones · una fila por camión atendido (opcional)

| Columna | Tipo | Qué es |
|---|---|---|
| **CamionID** | texto | Identificador. |
| **Tipo** | texto | `Entrada` o `Salida`. |
| **MuelleID** | texto | Muelle. Debe estar en la configuración. |
| **Inicio operación**, **Fin operación** | fecha y hora | Tiempo que el camión ocupa el muelle; con esto se encienden los muelles y se dibujan los camiones. |
| Fecha | fecha | Se calcula a partir de Inicio operación. |
| ProveedorID, DestinoID, Palets previstos, Palets, Hora prevista, Hora real, Espera (min), Retraso (min) | | Opcionales. |

Sin esta tabla, el informe funciona igual, pero los muelles siempre salen libres.

## Las tablas que se calculan

`completar_datos.py` las escribe en `datos/`; no hace falta prepararlas.

| Tabla | De dónde sale |
|---|---|
| Muelles | `muelles` de la configuración (MuelleID, Muelle, Tipo, Orden). |
| Pasillos | Filas de la configuración y número de ubicaciones de cada una. |
| Zonas | `zonas` de la configuración. |
| Categorias | `categorias` de la configuración: color de barras y leyenda, y dos tonos para las caras de los palets en 3D. |
| Almacen | Nombre, subtítulo, etiqueta, si los datos son ficticios y día que se abre por defecto. |
| Calendario | Del primer al último día con movimientos. «Abierto» = días con entradas o salidas. |
| Horas | De 0 a 23, con turno. |
| OcupacionHoraria | Palets en cada fila al final de cada hora, a partir de Movimientos. Alimenta la curva de ocupación. |

Las tablas `StockDiario`, `Operarios`, `Proveedores` y `Destinos` son **opcionales**: las usan medidas que no aparecen en la página. Si no las traes, se escriben solo con la cabecera.

## Comprobar antes de abrir Power BI

```
python generador/comprobar_datos.py
```

Revisa archivos y columnas, claves entre tablas, que las filas y los muelles coinciden con la configuración, que ningún hueco tiene dos palets a la vez ni salidas en vacío, y que la fecha por defecto está en el calendario. Si hay errores, termina con código 1.

## Límites de la plantilla

- **Estanterías uniformes:** todas las filas tienen los mismos huecos, niveles y palets por hueco. Hasta 18 filas, 40 huecos, 12 niveles y 4 palets por hueco.
- **Muelles:** hasta 16 de entrada y 16 de salida; las playas pintan hasta 6 palets por muelle.
- **Nombres de categoría:** no pueden llevar `|`. Los colores van en formato `#RRGGBB`.
- **Fechas:** el informe muestra de `vista.primera_hora` a `vista.ultima_hora`; los movimientos fuera de ese horario cuentan igual para el stock.
