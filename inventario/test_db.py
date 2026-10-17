"""Pruebas simples con assert. Correr: python test_db.py"""
from db import (conectar, crear_tablas, agregar_producto, agregar_cliente,
                registrar_entrada, stock_actual, registrar_venta,
                productos_bajo_stock, producto_mas_vendido, total_por_cliente,
                registrar_devolucion, listar_productos_con_stock,
                listar_clientes, historial_ventas)


def nueva_base():
    conn = conectar()
    crear_tablas(conn)
    return conn


def test_stock_con_entradas_y_venta():
    conn = nueva_base()
    p = agregar_producto(conn, "Playera dry-fit", "M", "negro", 250)
    c = agregar_cliente(conn, "Ana")
    registrar_entrada(conn, p, 10)
    assert stock_actual(conn, p) == 10
    registrar_venta(conn, c, [(p, 3)])
    assert stock_actual(conn, p) == 7


def test_venta_sin_stock_no_guarda_nada():
    conn = nueva_base()
    a = agregar_producto(conn, "Playera", "M", "negro", 250)
    b = agregar_producto(conn, "Short", "L", "azul", 300)
    c = agregar_cliente(conn, "Ana")
    registrar_entrada(conn, a, 5)
    registrar_entrada(conn, b, 1)
    try:
        registrar_venta(conn, c, [(a, 2), (b, 2)])  # b no alcanza
        assert False, "debio fallar"
    except ValueError:
        pass
    # Nada quedo a medias: el stock de 'a' sigue en 5 y no hay ventas
    assert stock_actual(conn, a) == 5
    assert conn.execute("SELECT COUNT(*) FROM ventas").fetchone()[0] == 0


def test_precio_historico_no_cambia():
    conn = nueva_base()
    p = agregar_producto(conn, "Playera", "M", "negro", 250)
    c = agregar_cliente(conn, "Ana")
    registrar_entrada(conn, p, 10)
    registrar_venta(conn, c, [(p, 2)])
    conn.execute("UPDATE productos SET precio = 400 WHERE id = ?", (p,))
    assert total_por_cliente(conn) == [("Ana", 500.0)]


def test_reportes():
    conn = nueva_base()
    a = agregar_producto(conn, "Playera", "M", "negro", 250, stock_minimo=2)
    b = agregar_producto(conn, "Short", "L", "azul", 300, stock_minimo=1)
    ana = agregar_cliente(conn, "Ana")
    luis = agregar_cliente(conn, "Luis")
    registrar_entrada(conn, a, 5)
    registrar_entrada(conn, b, 5)
    registrar_venta(conn, ana, [(a, 3), (b, 1)])
    registrar_venta(conn, luis, [(a, 1)])
    assert producto_mas_vendido(conn) == [("Playera", "M", "negro", 4)]
    assert [x[0] for x in productos_bajo_stock(conn)] == [a]  # a quedo en 1 <= 2
    assert total_por_cliente(conn) == [("Ana", 1050.0), ("Luis", 250.0)]


def test_producto_inexistente_y_cantidad_invalida():
    conn = nueva_base()
    c = agregar_cliente(conn, "Ana")
    for items in ([(999, 1)], []):
        try:
            registrar_venta(conn, c, items)
            assert False, "debio fallar"
        except ValueError:
            pass


def _venta_de_prueba():
    conn = nueva_base()
    p = agregar_producto(conn, "Playera", "M", "negro", 250)
    c = agregar_cliente(conn, "Ana")
    registrar_entrada(conn, p, 10)
    venta_id, _ = registrar_venta(conn, c, [(p, 4)])
    return conn, p, venta_id


def test_devolucion_sube_el_stock():
    conn, p, venta = _venta_de_prueba()
    assert stock_actual(conn, p) == 6
    registrar_devolucion(conn, venta, p, 1)
    assert stock_actual(conn, p) == 7


def test_devolucion_no_puede_pasarse_de_lo_vendido():
    conn, p, venta = _venta_de_prueba()
    registrar_devolucion(conn, venta, p, 3)
    for cantidad in (2, 0, -1):  # solo queda 1 por devolver
        try:
            registrar_devolucion(conn, venta, p, cantidad)
            assert False, "debio fallar"
        except ValueError:
            pass
    assert stock_actual(conn, p) == 9  # 10 - 4 + 3


def test_devolucion_de_producto_que_no_esta_en_la_venta():
    conn, p, venta = _venta_de_prueba()
    otro = agregar_producto(conn, "Short", "L", "azul", 300)
    try:
        registrar_devolucion(conn, venta, otro, 1)
        assert False, "debio fallar"
    except ValueError:
        pass


def test_listados_e_historial():
    conn, p, venta = _venta_de_prueba()
    assert listar_productos_con_stock(conn) == [(p, "Playera", "M", "negro", 250, 6)]
    assert listar_clientes(conn) == [(1, "Ana", None)]
    historial = historial_ventas(conn)
    assert len(historial) == 1 and historial[0][1] == "Ana" and historial[0][3] == 1000.0


if __name__ == "__main__":
    pruebas = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print("OK ", prueba.__name__)
    print(f"\nPasaron {len(pruebas)} pruebas")
