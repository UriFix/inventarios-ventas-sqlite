"""Menu de terminal del sistema de inventario y ventas.

Correr:  python main.py
"""
import sqlite3

from db import (
    conectar, crear_tablas, agregar_producto, agregar_cliente,
    registrar_entrada, registrar_venta, registrar_devolucion,
    listar_productos_con_stock, listar_clientes, historial_ventas,
    productos_bajo_stock, producto_mas_vendido, total_por_cliente,
)

RUTA_DB = "negocio.db"


# ---------- Ayudas para pedir datos sin que el programa truene ----------

def pedir_texto(mensaje, obligatorio=True):
    while True:
        valor = input(mensaje).strip()
        if valor or not obligatorio:
            return valor
        print("  Este dato es obligatorio.")


def pedir_entero(mensaje, minimo=0):
    while True:
        try:
            numero = int(input(mensaje).strip())
        except ValueError:
            print("  Escribe un numero entero.")
            continue
        if numero < minimo:
            print(f"  Debe ser {minimo} o mas.")
            continue
        return numero


def pedir_precio(mensaje):
    while True:
        try:
            precio = float(input(mensaje).strip())
        except ValueError:
            print("  Escribe un numero, por ejemplo 250 o 249.90")
            continue
        if precio < 0:
            print("  El precio no puede ser negativo.")
            continue
        return precio


def dinero(cantidad):
    return f"${cantidad:,.2f}"


# ---------- Opciones del menu ----------

def ver_inventario(conn):
    productos = listar_productos_con_stock(conn)
    if not productos:
        print("\n  Todavia no hay productos.")
        return
    print(f"\n  {'ID':<4}{'Producto':<24}{'Talla':<7}{'Color':<10}"
          f"{'Precio':>10}{'Stock':>8}")
    print("  " + "-" * 63)
    for pid, nombre, talla, color, precio, stock in productos:
        print(f"  {pid:<4}{nombre:<24}{talla:<7}{color:<10}"
              f"{dinero(precio):>10}{stock:>8}")


def ver_clientes(conn):
    clientes = listar_clientes(conn)
    if not clientes:
        print("\n  Todavia no hay clientes.")
        return False
    print("\n  Clientes:")
    for cid, nombre, telefono in clientes:
        print(f"  {cid}. {nombre} {('(' + telefono + ')') if telefono else ''}")
    return True


def opcion_agregar_producto(conn):
    print("\n--- Agregar producto ---")
    nombre = pedir_texto("Nombre (ej. Playera dry-fit): ")
    talla = pedir_texto("Talla (ej. M): ").upper()
    color = pedir_texto("Color: ").lower()
    precio = pedir_precio("Precio: ")
    minimo = pedir_entero("Stock minimo para avisarte (0 si no quieres aviso): ")
    try:
        pid = agregar_producto(conn, nombre, talla, color, precio, minimo)
        print(f"  Listo. Producto creado con ID {pid}.")
    except sqlite3.IntegrityError:
        print("  Ya existe ese producto con esa talla y color.")


def opcion_agregar_cliente(conn):
    print("\n--- Agregar cliente ---")
    nombre = pedir_texto("Nombre: ")
    telefono = pedir_texto("Telefono (Enter para omitir): ", obligatorio=False)
    cid = agregar_cliente(conn, nombre, telefono or None)
    print(f"  Listo. Cliente creado con ID {cid}.")


def opcion_entrada(conn):
    print("\n--- Registrar entrada de mercancia ---")
    ver_inventario(conn)
    if not listar_productos_con_stock(conn):
        return
    pid = pedir_entero("ID del producto: ", minimo=1)
    cantidad = pedir_entero("Cuantas piezas llegaron: ", minimo=1)
    try:
        registrar_entrada(conn, pid, cantidad)
        print("  Entrada registrada.")
    except sqlite3.IntegrityError:
        print("  Ese producto no existe.")


def opcion_venta(conn):
    print("\n--- Registrar venta ---")
    if not ver_clientes(conn):
        print("  Primero agrega un cliente (opcion 2).")
        return
    cliente_id = pedir_entero("ID del cliente: ", minimo=1)
    ver_inventario(conn)
    items = []
    print("\n  Agrega productos. Escribe 0 en el ID para terminar.")
    while True:
        pid = pedir_entero("ID del producto (0 = terminar): ")
        if pid == 0:
            break
        cantidad = pedir_entero("Cantidad: ", minimo=1)
        items.append((pid, cantidad))
    if not items:
        print("  No agregaste productos, venta cancelada.")
        return
    try:
        venta_id, total = registrar_venta(conn, cliente_id, items)
        print(f"  Venta #{venta_id} registrada. Total: {dinero(total)}")
    except (ValueError, sqlite3.IntegrityError) as error:
        print(f"  No se pudo registrar la venta: {error}")
        print("  (No se guardo nada.)")


def opcion_devolucion(conn):
    print("\n--- Registrar devolucion ---")
    ventas = historial_ventas(conn, limite=10)
    if not ventas:
        print("  Todavia no hay ventas.")
        return
    print("  Ultimas ventas:")
    for vid, cliente, fecha, total in ventas:
        print(f"  Venta #{vid}  {cliente}  {fecha}  {dinero(total)}")
    venta_id = pedir_entero("Numero de venta: ", minimo=1)
    producto_id = pedir_entero("ID del producto a devolver: ", minimo=1)
    cantidad = pedir_entero("Cuantas piezas: ", minimo=1)
    try:
        registrar_devolucion(conn, venta_id, producto_id, cantidad)
        print("  Devolucion registrada, el stock ya subio.")
    except ValueError as error:
        print(f"  No se pudo: {error}")


def opcion_reportes(conn):
    print("\n--- Reportes ---")
    print("\n  Productos con stock bajo:")
    bajos = productos_bajo_stock(conn)
    if not bajos:
        print("   Ninguno, todo bien.")
    for pid, nombre, talla, color, stock in bajos:
        print(f"   - {nombre} {talla} {color}: quedan {stock}")

    print("\n  Producto mas vendido:")
    ganadores = producto_mas_vendido(conn)
    if not ganadores:
        print("   Todavia no hay ventas.")
    for nombre, talla, color, piezas in ganadores:
        print(f"   - {nombre} {talla} {color}: {piezas} pieza(s)")

    print("\n  Cuanto ha comprado cada cliente:")
    totales = total_por_cliente(conn)
    if not totales:
        print("   Todavia no hay ventas.")
    for nombre, total in totales:
        print(f"   - {nombre}: {dinero(total)}")


def opcion_historial(conn):
    print("\n--- Ultimas ventas ---")
    ventas = historial_ventas(conn, limite=10)
    if not ventas:
        print("  Todavia no hay ventas.")
    for vid, cliente, fecha, total in ventas:
        print(f"  Venta #{vid}  {cliente}  {fecha}  {dinero(total)}")


MENU = """
==============================
   INVENTARIO Y VENTAS
==============================
 1. Agregar producto
 2. Agregar cliente
 3. Registrar entrada de mercancia
 4. Registrar venta
 5. Registrar devolucion
 6. Ver inventario
 7. Reportes
 8. Historial de ventas
 0. Salir
"""

ACCIONES = {
    "1": opcion_agregar_producto,
    "2": opcion_agregar_cliente,
    "3": opcion_entrada,
    "4": opcion_venta,
    "5": opcion_devolucion,
    "6": lambda conn: ver_inventario(conn),
    "7": opcion_reportes,
    "8": opcion_historial,
}


def main():
    conn = conectar(RUTA_DB)
    crear_tablas(conn)
    try:
        while True:
            print(MENU)
            opcion = input("Elige una opcion: ").strip()
            if opcion == "0":
                break
            accion = ACCIONES.get(opcion)
            if accion is None:
                print("  Opcion no valida.")
                continue
            accion(conn)
    except (EOFError, KeyboardInterrupt):
        print()
    finally:
        conn.close()
        print("Hasta luego.")


if __name__ == "__main__":
    main()
