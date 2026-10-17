# Inventario y Ventas (Python + SQLite)

Sistema de inventario y ventas para un negocio pequeno (ej. ropa deportiva), hecho con Python y SQLite. Se usa desde la terminal con un menu.

Proyecto personal para practicar bases de datos relacionales, transacciones y pruebas automaticas.

## Que hace

- Agregar productos (nombre, talla, color, precio, stock minimo) y clientes
- Registrar entradas de mercancia
- Registrar ventas con varios productos (todo-o-nada: si un producto no alcanza, no se guarda nada)
- Registrar devoluciones (el stock vuelve a subir; no se puede devolver mas de lo vendido)
- Ver inventario con stock actual
- Reportes: productos con stock bajo, producto mas vendido, total comprado por cliente
- Historial de las ultimas ventas

## Como correrlo

Necesitas Python 3.8 o mas nuevo. No hay que instalar nada extra (`sqlite3` ya viene con Python).

```bash
python datos_ejemplo.py   # opcional: carga datos inventados para probar
python main.py            # abre el menu
python test_db.py         # corre las pruebas
```

La base de datos se guarda en `negocio.db` (se crea sola).

## Como esta hecho

Tablas: `productos`, `clientes`, `ventas`, `detalle_venta`, `movimientos`.

Decisiones de diseno:

- **El stock se calcula, no se edita.** Se suma entradas y devoluciones y se resta las salidas de la tabla `movimientos`, asi siempre hay historial.
- **Relacion 1 a muchos:** una venta tiene varias lineas en `detalle_venta`.
- **Precio historico:** cada linea guarda el precio del momento, asi cambiar el precio hoy no altera ventas pasadas.
- **Transacciones:** `registrar_venta` hace `commit` si todo sale bien y `rollback` si algo falla.
- **Consultas parametrizadas (`?`)** para evitar SQL injection.
- **Restricciones en la base:** `UNIQUE(nombre, talla, color)`, `CHECK (precio >= 0)`, `CHECK (cantidad > 0)`, llaves foraneas activadas.

## Archivos

| Archivo | Para que sirve |
|---|---|
| `db.py` | Toda la logica y las consultas a la base |
| `main.py` | Menu de terminal |
| `datos_ejemplo.py` | Carga datos de ejemplo |
| `test_db.py` | Pruebas con `assert` |

## Limitaciones conocidas

- `total_por_cliente` no resta las devoluciones (cuenta lo que se vendio originalmente).
- No hay usuarios ni contrasenas.
- Interfaz solo de terminal; no hay edicion ni borrado de productos.

## Ideas para mejorar

- Restar devoluciones en los reportes
- Exportar reportes a CSV
- Interfaz web sencilla (Flask)
