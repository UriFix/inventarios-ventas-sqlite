"""Sistema de inventario y ventas (Python + SQLite).

Idea central: el stock NO se guarda como un numero que editamos.
Se calcula sumando los movimientos (igual que tu ejercicio stock_actual).
Asi siempre hay historial de que paso y por que.
"""
import sqlite3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS productos (
    id           INTEGER PRIMARY KEY,
    nombre       TEXT NOT NULL,
    talla        TEXT NOT NULL,
    color        TEXT NOT NULL,
    precio       REAL NOT NULL CHECK (precio >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0,
    UNIQUE (nombre, talla, color)
);

CREATE TABLE IF NOT EXISTS clientes (
    id       INTEGER PRIMARY KEY,
    nombre   TEXT NOT NULL,
    telefono TEXT
);

CREATE TABLE IF NOT EXISTS ventas (
    id         INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id),
    fecha      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Una venta tiene varias lineas. Guardamos el precio del momento:
-- si el precio cambia manana, las ventas viejas no se alteran.
CREATE TABLE IF NOT EXISTS detalle_venta (
    id              INTEGER PRIMARY KEY,
    venta_id        INTEGER NOT NULL REFERENCES ventas(id),
    producto_id     INTEGER NOT NULL REFERENCES productos(id),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS movimientos (
    id          INTEGER PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo        TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida', 'devolucion')),
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
    fecha       TEXT NOT NULL DEFAULT (datetime('now')),
    venta_id    INTEGER REFERENCES ventas(id)
);
"""


def conectar(ruta=":memory:"):
    """Abre la base y activa las llaves foraneas (SQLite las trae apagadas)."""
    conn = sqlite3.connect(ruta)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def crear_tablas(conn):
    conn.executescript(ESQUEMA)


def agregar_producto(conn, nombre, talla, color, precio, stock_minimo=0):
    cur = conn.execute(
        "INSERT INTO productos (nombre, talla, color, precio, stock_minimo) "
        "VALUES (?, ?, ?, ?, ?)",
        (nombre, talla, color, precio, stock_minimo),
    )
    conn.commit()
    return cur.lastrowid


def agregar_cliente(conn, nombre, telefono=None):
    cur = conn.execute(
        "INSERT INTO clientes (nombre, telefono) VALUES (?, ?)", (nombre, telefono)
    )
    conn.commit()
    return cur.lastrowid


def registrar_movimiento(conn, producto_id, tipo, cantidad, venta_id=None):
    conn.execute(
        "INSERT INTO movimientos (producto_id, tipo, cantidad, venta_id) "
        "VALUES (?, ?, ?, ?)",
        (producto_id, tipo, cantidad, venta_id),
    )


def registrar_entrada(conn, producto_id, cantidad):
    registrar_movimiento(conn, producto_id, "entrada", cantidad)
    conn.commit()


def stock_actual(conn, producto_id):
    """entrada y devolucion suman, salida resta."""
    fila = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN tipo = 'salida' THEN -cantidad "
        "ELSE cantidad END), 0) AS stock "
        "FROM movimientos WHERE producto_id = ?",
        (producto_id,),
    ).fetchone()
    return fila["stock"]


def registrar_venta(conn, cliente_id, items):
    """items = [(producto_id, cantidad), ...]

    Es todo-o-nada: si UN producto no alcanza, no se guarda NADA.
    Eso se llama transaccion.
    """
    if not items:
        raise ValueError("La venta no tiene productos")
    try:
        venta_id = conn.execute(
            "INSERT INTO ventas (cliente_id) VALUES (?)", (cliente_id,)
        ).lastrowid
        total = 0.0
        for producto_id, cantidad in items:
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a 0")
            producto = conn.execute(
                "SELECT precio, nombre, talla, color FROM productos WHERE id = ?",
                (producto_id,),
            ).fetchone()
            if producto is None:
                raise ValueError(f"No existe el producto {producto_id}")
            if stock_actual(conn, producto_id) < cantidad:
                raise ValueError(
                    f"Stock insuficiente de {producto['nombre']} "
                    f"{producto['talla']} {producto['color']}"
                )
            conn.execute(
                "INSERT INTO detalle_venta "
                "(venta_id, producto_id, cantidad, precio_unitario) "
                "VALUES (?, ?, ?, ?)",
                (venta_id, producto_id, cantidad, producto["precio"]),
            )
            registrar_movimiento(conn, producto_id, "salida", cantidad, venta_id)
            total += producto["precio"] * cantidad
        conn.commit()
        return venta_id, total
    except Exception:
        conn.rollback()  # deshace todo lo de esta venta
        raise


def registrar_devolucion(conn, venta_id, producto_id, cantidad):
    """Devuelve piezas de una venta: el stock sube de nuevo.

    Reglas: el producto debe estar en esa venta y no se puede devolver
    mas de lo que se vendio (contando devoluciones anteriores).
    """
    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    vendido = conn.execute(
        "SELECT COALESCE(SUM(cantidad), 0) AS n FROM detalle_venta "
        "WHERE venta_id = ? AND producto_id = ?",
        (venta_id, producto_id),
    ).fetchone()["n"]
    if vendido == 0:
        raise ValueError("Ese producto no esta en esa venta")
    ya_devuelto = conn.execute(
        "SELECT COALESCE(SUM(cantidad), 0) AS n FROM movimientos "
        "WHERE venta_id = ? AND producto_id = ? AND tipo = 'devolucion'",
        (venta_id, producto_id),
    ).fetchone()["n"]
    if cantidad > vendido - ya_devuelto:
        raise ValueError(
            f"Solo se pueden devolver {vendido - ya_devuelto} pieza(s) mas"
        )
    registrar_movimiento(conn, producto_id, "devolucion", cantidad, venta_id)
    conn.commit()


# ---------------- Reportes ----------------

def productos_bajo_stock(conn):
    """Productos cuyo stock es menor o igual a su stock_minimo."""
    filas = conn.execute("SELECT id, nombre, talla, color, stock_minimo FROM productos")
    resultado = []
    for p in filas.fetchall():
        stock = stock_actual(conn, p["id"])
        if stock <= p["stock_minimo"]:
            resultado.append((p["id"], p["nombre"], p["talla"], p["color"], stock))
    return resultado


def producto_mas_vendido(conn):
    """Devuelve una lista (por si hay empate) de (nombre, talla, color, piezas)."""
    filas = conn.execute(
        "SELECT p.nombre, p.talla, p.color, SUM(d.cantidad) AS piezas "
        "FROM detalle_venta d JOIN productos p ON p.id = d.producto_id "
        "GROUP BY p.id ORDER BY piezas DESC"
    ).fetchall()
    if not filas:
        return []
    maximo = filas[0]["piezas"]
    return [(f["nombre"], f["talla"], f["color"], f["piezas"])
            for f in filas if f["piezas"] == maximo]


def total_por_cliente(conn):
    """Cuanto ha gastado cada cliente (usa el precio guardado en cada venta)."""
    filas = conn.execute(
        "SELECT c.nombre, SUM(d.cantidad * d.precio_unitario) AS total "
        "FROM clientes c "
        "JOIN ventas v ON v.cliente_id = c.id "
        "JOIN detalle_venta d ON d.venta_id = v.id "
        "GROUP BY c.id ORDER BY total DESC"
    ).fetchall()
    return [(f["nombre"], f["total"]) for f in filas]


# ---------------- Listados para el menu ----------------

def listar_productos_con_stock(conn):
    """[(id, nombre, talla, color, precio, stock), ...]"""
    filas = conn.execute(
        "SELECT id, nombre, talla, color, precio FROM productos ORDER BY id"
    ).fetchall()
    return [(f["id"], f["nombre"], f["talla"], f["color"], f["precio"],
             stock_actual(conn, f["id"])) for f in filas]


def listar_clientes(conn):
    """[(id, nombre, telefono), ...]"""
    filas = conn.execute(
        "SELECT id, nombre, telefono FROM clientes ORDER BY id"
    ).fetchall()
    return [(f["id"], f["nombre"], f["telefono"]) for f in filas]


def historial_ventas(conn, limite=10):
    """Ultimas ventas: [(venta_id, cliente, fecha, total), ...]"""
    filas = conn.execute(
        "SELECT v.id, c.nombre, v.fecha, "
        "SUM(d.cantidad * d.precio_unitario) AS total "
        "FROM ventas v "
        "JOIN clientes c ON c.id = v.cliente_id "
        "JOIN detalle_venta d ON d.venta_id = v.id "
        "GROUP BY v.id ORDER BY v.id DESC LIMIT ?",
        (limite,),
    ).fetchall()
    return [(f["id"], f["nombre"], f["fecha"], f["total"]) for f in filas]
