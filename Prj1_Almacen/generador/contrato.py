# -*- coding: utf-8 -*-
"""
Contrato de datos: qué CSV lee el modelo de Power BI y con qué columnas (las mismas, en el mismo
orden, que las consultas de Power Query del modelo). Lo explica para personas CONTRATO_DE_DATOS.md.

Cada tabla tiene un papel:
  «tuyo»       lo aportas tú desde tu sistema de gestión de almacén (SGA); hay columnas obligatorias
  «derivado»   lo calcula completar_datos.py a partir de tus tablas y de almacen.config.json
  «opcional»   lo usan medidas que no salen en la página; puede ir con la cabecera y sin filas
"""
from __future__ import annotations

TEXTO, ENTERO, DECIMAL, FECHA, FECHA_HORA = "texto", "entero", "decimal", "fecha", "fecha y hora"

# tabla: (papel, [(columna, tipo, obligatoria), ...])
TABLAS: dict[str, tuple[str, list[tuple[str, str, bool]]]] = {
    "Ubicaciones": ("tuyo", [
        ("UbicacionID", TEXTO, True), ("Pasillo", TEXTO, True), ("Orden pasillo", ENTERO, False),
        ("Hueco", ENTERO, True), ("Nivel", ENTERO, True), ("Posición", ENTERO, True), ("ZonaID", TEXTO, False)]),
    "Movimientos": ("tuyo", [
        ("MovimientoID", ENTERO, False), ("FechaHora", FECHA_HORA, True), ("Fecha", FECHA, False), ("Hora", ENTERO, False),
        ("Tipo", TEXTO, True), ("Signo", ENTERO, True), ("SKU", TEXTO, True), ("UbicacionID", TEXTO, True),
        ("MuelleID", TEXTO, False), ("CamionID", TEXTO, False), ("OperarioID", TEXTO, False),
        ("ProveedorID", TEXTO, False), ("DestinoID", TEXTO, False), ("DuracionMin", DECIMAL, False)]),
    "Productos": ("tuyo", [
        ("SKU", TEXTO, True), ("Producto", TEXTO, True), ("Categoría", TEXTO, True), ("ProveedorID", TEXTO, False),
        ("Valor palet (€)", ENTERO, False), ("Clase ABC", TEXTO, False), ("Demanda media (palets/día)", DECIMAL, False)]),
    "Camiones": ("tuyo", [
        ("CamionID", TEXTO, True), ("Tipo", TEXTO, True), ("Fecha", FECHA, False), ("MuelleID", TEXTO, True),
        ("ProveedorID", TEXTO, False), ("DestinoID", TEXTO, False), ("Palets previstos", ENTERO, False),
        ("Palets", ENTERO, False), ("Hora prevista", FECHA_HORA, False), ("Hora real", FECHA_HORA, False),
        ("Inicio operación", FECHA_HORA, True), ("Fin operación", FECHA_HORA, True),
        ("Espera (min)", DECIMAL, False), ("Retraso (min)", DECIMAL, False)]),
    "Muelles": ("derivado", [
        ("MuelleID", TEXTO, True), ("Muelle", TEXTO, True), ("Tipo", TEXTO, True), ("Orden", ENTERO, True)]),
    "Pasillos": ("derivado", [
        ("Pasillo", TEXTO, True), ("Orden pasillo", ENTERO, True), ("ZonaID", TEXTO, True),
        ("Capacidad (palets)", ENTERO, True)]),
    "Zonas": ("derivado", [
        ("ZonaID", TEXTO, True), ("Zona", TEXTO, True), ("Orden", ENTERO, True), ("Descripción", TEXTO, True),
        ("Capacidad (palets)", ENTERO, True)]),
    "Calendario": ("derivado", [
        ("Fecha", FECHA, True), ("Año", ENTERO, True), ("Mes", ENTERO, True), ("Nombre del mes", TEXTO, True),
        ("Mes corto", TEXTO, True), ("Año-mes", ENTERO, True), ("Mes y año", TEXTO, True), ("Trimestre", TEXTO, True),
        ("Semana ISO", ENTERO, True), ("Día", ENTERO, True), ("Día de la semana", TEXTO, True),
        ("Orden día semana", ENTERO, True), ("Abierto", TEXTO, True), ("Festivo", TEXTO, False), ("Temporada", TEXTO, True)]),
    "Horas": ("derivado", [("Hora", ENTERO, True), ("Hora texto", TEXTO, True), ("Turno", TEXTO, True)]),
    "OcupacionHoraria": ("derivado", [
        ("Fecha", FECHA, True), ("Hora", ENTERO, True), ("Pasillo", TEXTO, True), ("Ocupadas", ENTERO, True)]),
    "Almacen": ("derivado", [
        ("Nombre", TEXTO, True), ("Subtítulo", TEXTO, False), ("Etiqueta", TEXTO, False), ("Datos ficticios", TEXTO, True),
        ("Fecha por defecto", FECHA, True), ("Nota de la fecha", TEXTO, False)]),
    "Categorias": ("derivado", [
        ("Categoría", TEXTO, True), ("Nombre corto", TEXTO, True), ("Color", TEXTO, True), ("Tono claro", TEXTO, True),
        ("Tono oscuro", TEXTO, True), ("Orden", ENTERO, True)]),
    "StockDiario": ("opcional", [
        ("Fecha", FECHA, True), ("SKU", TEXTO, True), ("Stock final (palets)", ENTERO, True),
        ("Entradas (palets)", ENTERO, True), ("Demanda (palets)", ENTERO, True), ("Servidos (palets)", ENTERO, True),
        ("No servidos (palets)", ENTERO, True), ("Edad media (días)", DECIMAL, True), ("Valor stock (€)", ENTERO, True)]),
    "Operarios": ("opcional", [
        ("OperarioID", TEXTO, True), ("Operario", TEXTO, True), ("Turno", TEXTO, True), ("Rol", TEXTO, True)]),
    "Proveedores": ("opcional", [
        ("ProveedorID", TEXTO, True), ("Proveedor", TEXTO, True), ("Categoría", TEXTO, True),
        ("Plazo de entrega (días)", ENTERO, True)]),
    "Destinos": ("opcional", [
        ("DestinoID", TEXTO, True), ("Destino", TEXTO, True), ("Latitud", DECIMAL, True), ("Longitud", DECIMAL, True)]),
}

TIPOS_MOVIMIENTO = {"Entrada": 1, "Salida": -1, "Stock inicial": 1}


def columnas(tabla: str) -> list[str]:
    return [c for c, _, _ in TABLAS[tabla][1]]


def obligatorias(tabla: str) -> list[str]:
    return [c for c, _, o in TABLAS[tabla][1] if o]
