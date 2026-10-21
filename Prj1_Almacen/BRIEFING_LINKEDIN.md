# Briefing para el post de LinkedIn · Almacén CD-01, gemelo digital en Power BI

Documento de contexto para el agente que redacta y optimiza el post. Reúne qué es el informe, qué enseña la imagen, cómo se construyó, las cifras comprobadas y lo que **no** hay que afirmar. El post lo firma **Santiago Moya**.

---

## 1. En una frase

Un informe de Power BI que dibuja un almacén completo en 3D isométrico y deja **viajar en el tiempo**: eliges un día y una hora del año y ves qué palet hay en cada una de las 1.728 ubicaciones, qué camiones están en cada muelle y dónde se mueven las carretillas. Datos ficticios, construido en una mañana con IA (Claude) como compañero de desarrollo.

## 2. Qué se ve en la imagen

Página única, **«Almacén en vivo»**, 1920×1080, estética oscura de «torre de control»:

- **Cabecera:** «Almacén CD-01 · gemelo digital», el día y la hora que se están viendo, y dos etiquetas: «Simulación hora a hora» y «Datos ficticios».
- **Escenario central (el 3D):**
  - un almacén en isométrica, como una maqueta: muros con ventanales, 8 filas de estanterías (A–H) con largueros naranjas y palets de colores;
  - muelles con pilotos verde/rojo, camiones atracados (turquesa = proveedor, rosa = cliente), playas de entrada y salida con palets de cartón o filmados, y carretillas elevadoras en los pasillos;
  - sobre cada fila, una etiqueta con su ocupación («A · 100 %»).
- **Barras del escenario:**
  - arriba: la hora del día (6–21) y el selector de color (ABC / Días / Categoría);
  - abajo: «Fila en primer plano» (Todo, A–H).
- **Columna derecha:**
  - anillo de ocupación con estado («Holgado», «En tensión» o «Saturado»);
  - flujo del día (entradas, salidas y neto);
  - los 12 muelles encendidos según tengan camión;
  - curva de ocupación hora a hora del día;
  - curva de ocupación de los 365 días (se pincha para cambiar de día);
  - stock por categoría (se pincha para resaltar esos palets en el 3D).

Por defecto abre el **16 de diciembre de 2025 a las 11:00**, el pico de la campaña de Navidad: almacén al 100 %, todas las filas en rojo y el estado «Saturado».

## 3. Qué permite hacer (interacción)

- **Viajar en el tiempo:**
  - un clic en una hora o en un día de la curva anual y todo se recalcula;
  - el estado de cada hueco se reconstruye a partir de los movimientos: entradas suman y salidas restan hasta ese instante.
- **Leer cada palet:**
  - al pasar el ratón, la ficha dice la ubicación, el producto, la categoría, la clase ABC, los días que lleva en stock y si se movió en esa hora;
  - los palets movidos en la hora elegida se marcan, y las carretillas aparecen en esos pasillos.
- **Cambiar la lectura del color:**
  - **ABC:** los productos A, de alta rotación, junto a los muelles;
  - **Días:** marca en rojo los palets antiguos, de más de 21 días;
  - **Categoría.**
- **Filtrar por categoría:** al pinchar una categoría, el resto de palets queda casi transparente y cada fila muestra cuánto ocupa esa categoría.
- **Modo corte (rayos X):** al elegir una fila, las que tiene delante se vuelven de cristal y dejan de interceptar el ratón. Así se puede consultar cualquier palet de los pasillos interiores. Resuelve el problema clásico de las vistas isométricas: lo de delante tapa lo de detrás.

## 4. Cómo está hecho (de los datos a la página)

1. **Datos simulados palet a palet (Python):**
   - un año completo (1/10/2025 – 30/9/2026) de un centro de distribución inventado;
   - pedidos de clientes con estacionalidad (Black Friday, Navidad con turrones y cava, verano para bebidas), reposición a proveedores con plazos y días de entrega, ubicación de cada palet según su rotación, camiones por muelle con retrasos y operarios por turnos;
   - se simulan cuatro semanas de calentamiento antes del 1 de octubre para que el arranque sea realista;
   - todo cuadra entre sí: ninguna ubicación tiene nunca dos palets.
2. **Modelo semántico en Power BI:**
   - construido directamente en Power BI Desktop por la IA a través del servidor MCP de modelado de Power BI: tablas, relaciones, medidas DAX y una tabla de fechas;
   - las medidas se validaron con consultas DAX. Por ejemplo, el stock reconstruido desde los movimientos coincide al palet con la foto horaria en 180 momentos de muestra.
3. **El 3D, con Deneb (Vega):**
   - Power BI no trae vistas 3D de serie. El almacén se dibuja con **Deneb**, un objeto visual que ejecuta gramática **Vega**;
   - un script de Python genera la especificación: proyección isométrica 2:1, unas 530 piezas fijas (muros, puntales, largueros, muelles) y la geometría de cada palet a partir de los datos, en total unas 11.000 caras;
   - todo se ordena por profundidad para que unas piezas tapen a otras correctamente.
4. **Tarjetas animadas, con HTML Content:** medidas DAX que devuelven HTML y CSS (anillo que se rellena, estado que late, curva que se dibuja, pilotos de muelle).
5. **Diseño en Figma:** fondo de la página, paneles de cristal, rejilla técnica, esquinas tipo pantalla de control y logotipo. Exportado como imagen de fondo de Power BI.
6. **Informe como código (PBIP / PBIR / TMDL):**
   - la página la escribe un script de Python en el formato de proyecto de Power BI;
   - se valida contra los esquemas JSON públicos de Microsoft antes de abrirla;
   - el modelo vive en archivos TMDL legibles.
7. **Iteración con capturas:** cada versión se revisó sobre la pantalla real de Power BI. Por ejemplo, el modo corte nació de una pregunta de usuario: «¿y cómo selecciono un palet de un pasillo interior?».

## 5. Cifras comprobadas

| Dato | Valor |
|---|---|
| Ubicaciones de palet | 1.728 (8 filas × 12 huecos × 6 niveles × 3 posiciones) |
| Productos (SKU) | 300 en 7 categorías |
| Proveedores / destinos | 20 proveedores · 10 regiones de destino |
| Muelles / operarios | 12 muelles (6 de entrada, 6 de salida) · 11 operarios en 2 turnos |
| Movimientos de palets en el año | 97.957 filas: 48.380 entradas, 48.429 salidas y 1.148 de stock inicial |
| Camiones atendidos | 7.084 |
| Ocupación media / máxima | 70,9 % / 100 % (noviembre y diciembre) |
| Nivel de servicio | 99,5 % de los palets pedidos servidos |
| Puntualidad de camiones | 88,7 % con 15 minutos de retraso o menos |
| Modelo | 20 tablas, 20 relaciones, 61 medidas DAX |
| Código | unas 2.800 líneas de Python (configuración, simulador, datos reales y comprobación, escena 3D, página y banco de pruebas) |
| Tiempo | el informe, una mañana (20 de octubre de 2026); convertirlo en plantilla adaptable, otra (21 de octubre de 2026) |

## 6. Papel de la IA (para contarlo con honestidad)

- **La IA (Claude, en Claude Code) hizo de equipo de desarrollo:**
  - escribió el simulador y las medidas DAX;
  - montó el modelo dentro de Power BI mediante el servidor MCP de modelado;
  - generó la escena 3D en Vega, diseñó el fondo en Figma mediante su conexión MCP, y escribió y validó los archivos del informe.
- **El autor marcó el rumbo y tomó las decisiones:**
  - qué contar y qué estética buscar;
  - exigir un nivel de diseño profesional y detectar los problemas de uso;
  - decidir qué se quedaba y qué se cambiaba en cada iteración.
- **Mensaje de fondo:** la IA no sustituye el criterio de negocio ni de diseño; multiplica lo que una persona con ese criterio puede construir en poco tiempo.

## 7. Ángulos posibles para el post

- **«Viajar en el tiempo dentro de un almacén»:** elegir día y hora y ver el estado exacto, palet a palet.
- **«Power BI no hace 3D… hasta que lo dibujas»:** Deneb y Vega llevan Power BI más allá de sus gráficos estándar.
- **«Un año de operación en una mañana»:** del dato simulado al informe terminado con IA como compañero.
- **«El detalle que separa un concepto bonito de una herramienta usable»:** el modo corte para llegar a los pasillos interiores.
- **«Informe como código»:** PBIP, TMDL y validación contra esquemas, versionable en Git y reproducible.
- **«Tu almacén en un archivo»:** es una plantilla. Filas, huecos, niveles, muelles y categorías se describen en `almacen.config.json` y una orden lo reconstruye todo: datos, escena 3D y página. Se probó con otra variante (10 filas, 5 categorías, 8 muelles) sin tocar una línea del modelo.
- **«Pensado para que lo adapte otra IA»:** el repositorio trae una guía para agentes (`AGENTS.md`) y un contrato de datos para conectar un SGA real. Basta con pedirle a un agente «mi almacén tiene 10 filas».
- **Llamada a la acción:** el repositorio es público, para que cualquiera lo abra, lo pruebe y lo adapte a su almacén.

## 8. Lo que no hay que afirmar

- **Los datos son 100 % ficticios.** «Almacén CD-01», los productos (genéricos, sin marcas) y los proveedores («Proveedor 01…») son inventados. No representan a ninguna empresa real ni al empleador del autor; no lo menciones.
- **No es un sistema conectado en tiempo real.** «Gemelo digital» se usa en sentido de simulación: el informe reproduce un año simulado, no lee un almacén real.
- **No es 3D real ni un motor de videojuego.** Es una proyección isométrica dibujada con Vega dentro de Power BI. Se puede decir «vista 3D isométrica».
- **Sin promesas de rendimiento ni de escala** que no se hayan medido.
- **Deneb y HTML Content son objetos visuales de terceros, con licencia MIT.** Se usan sus versiones «standalone» oficiales, importadas desde archivo.

## 9. Contenido del repositorio

| Pieza | Qué es |
|---|---|
| `README.md` (raíz) | Presentación pública del proyecto, con captura, cómo abrirlo y créditos |
| `Prj1_Almacen.pbip` + `Prj1_Almacen.Report/` + `Prj1_Almacen.SemanticModel/` | El informe en formato de proyecto de Power BI (PBIR + TMDL) |
| `Prj1_Almacen/generador/generar_datos.py` | Simulador del año de operación (crea los CSV) |
| `Prj1_Almacen/generador/pagina_almacen.py` | Escribe la página del informe en PBIR |
| `Prj1_Almacen/deneb/construir_escena.py` | Genera la especificación Vega del almacén isométrico |
| `Prj1_Almacen/datos/*.csv` | Los datos ficticios (16 tablas) |
| `Prj1_Almacen/informe/` | Tema oscuro y fondo de página diseñado en Figma |
| `Prj1_Almacen/objetos-visuales/` | Deneb 2.0.1 y HTML Content 2.0.0 (standalone, MIT) |
| `Prj1_Almacen/almacen.config.json` | La descripción del almacén: filas, huecos, niveles, muelles y categorías |
| `Prj1_Almacen/construir.py` | Reconstruye datos, escena y página con una orden |
| `Prj1_Almacen/CONTRATO_DE_DATOS.md` | Las tablas y columnas para usar datos reales de un SGA |
| `AGENTS.md` | Guía para que un agente de IA adapte la plantilla: qué tocar, en qué orden y cómo comprobarlo |
| `Prj1_Almacen/README.md` | Notas técnicas: cómo regenerarlo, cómo se adapta y qué hace cada medida clave |
| `docs/captura-almacen.webp` | Captura de la página |

**Para abrirlo hace falta:**
- Power BI Desktop de agosto de 2026 o posterior;
- apuntar el parámetro `CarpetaDatos` a la carpeta `Prj1_Almacen/datos/` y pulsar «Actualizar» (el repositorio no incluye la caché de datos);
- los objetos visuales ya van incrustados en el informe. Si no aparecen, se importan desde `Prj1_Almacen/objetos-visuales/`.

El diseño se hizo en Figma (archivo «Almacén CD-01 · Power BI», no público).

## 10. Glosario rápido

- **Deneb:** objeto visual de Power BI para dibujar con Vega o Vega-Lite.
- **Vega:** gramática declarativa de visualización (JSON).
- **HTML Content:** objeto visual que muestra HTML y CSS generados por medidas DAX.
- **PBIP / PBIR / TMDL:** formatos de proyecto de Power BI en archivos de texto (informe y modelo), pensados para Git.
- **DAX:** lenguaje de medidas de Power BI.
- **MCP:** protocolo con el que la IA se conecta a herramientas como Power BI Desktop y Figma.
- **Clase ABC:** clasificación de productos por volumen de salida. A = alta rotación.
- **Playa:** zona junto a los muelles donde esperan los palets recién descargados o preparados para cargar.
