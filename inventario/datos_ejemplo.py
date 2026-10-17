"""Carga datos de ejemplo en negocio.db para probar el menu.

Correr UNA vez:  python datos_ejemplo.py
Son datos inventados (no son del negocio real).
"""
from db import (conectar, crear_tablas, agregar_producto, agregar_cliente,
                registrar_entrada, registrar_venta, registrar_devolucion)

RUTA_DB = "negocio.db"


def main():
    conn = conectar(RUTA_DB)
    crear_tablas(conn)
    ya_hay = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]
    if ya_hay:
        print("negocio.db ya tiene productos. Borra el archivo si quieres empezar de cero.")
        return

    playera_m = agregar_producto(conn, "Playera dry-fit", "M", "negro", 250, 3)
    playera_l = agregar_producto(conn, "Playera dry-fit", "L", "blanco", 250, 3)
    short = agregar_producto(conn, "Short deportivo", "M", "azul", 320, 2)
    leggin = agregar_producto(conn, "Leggin deportivo", "S", "gris", 380, 2)

    ana = agregar_cliente(conn, "Ana Lopez", "2221234567")
    luis = agregar_cliente(conn, "Luis Perez")

    for producto, piezas in ((playera_m, 10), (playera_l, 8), (short, 6), (leggin, 5)):
        registrar_entrada(conn, producto, piezas)

    registrar_venta(conn, ana, [(playera_m, 2), (leggin, 1)])
    venta_luis, _ = registrar_venta(conn, luis, [(playera_m, 3), (short, 2)])
    registrar_devolucion(conn, venta_luis, short, 1)

    print("Datos de ejemplo cargados. Ahora corre: python main.py")


if __name__ == "__main__":
    main()
