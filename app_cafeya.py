from flask import Flask, request, jsonify
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import requests
import os # Importamos os para gestionar la eliminación de archivos de gráficos

app = Flask(__name__)

# --------------------- Inicializar Base de Datos ---------------------
def crear_base_datos():
    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()

    # Tabla usuarios: id, nombre, tipo (cliente/cafeteria)
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE, -- Añadido UNIQUE para nombres de usuario
        tipo TEXT NOT NULL
    )''')

    # Tabla productos: id, nombre, precio, stock, horario_retiro, cafeteria_id, categoria
    cursor.execute('''CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL,
        horario_retiro TEXT,
        cafeteria_id INTEGER NOT NULL,
        categoria TEXT,
        FOREIGN KEY (cafeteria_id) REFERENCES usuarios(id)
    )''')

    # Tabla pedidos: id, usuario_id (cliente), producto_id, estado, horario_retiro, cantidad_pedida, precio_unitario_al_comprar
    cursor.execute('''CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        estado TEXT NOT NULL DEFAULT 'pendiente', -- Estado por defecto
        horario_retiro TEXT,
        cantidad_pedida INTEGER NOT NULL,
        precio_unitario_al_comprar REAL NOT NULL, -- Para registrar el precio exacto de compra
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY (producto_id) REFERENCES productos(id)
    )''')

    conn.commit()
    conn.close()

crear_base_datos()

# ------------------------- Rutas de la API --------------------------

@app.route('/')
def home():
    return '<h2>API CaféYa - Gestión de Pedidos en Cafeterías</h2>'

@app.route('/registrar_usuario', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    nombre = data.get('nombre')
    tipo = data.get('tipo')

    if not nombre or not tipo:
        return jsonify({"error": "Nombre y tipo son requeridos"}), 400
    if tipo not in ['cliente', 'cafeteria']:
        return jsonify({"error": "Tipo de usuario inválido. Debe ser 'cliente' o 'cafeteria'"}), 400

    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO usuarios (nombre, tipo) VALUES (?, ?)", (nombre, tipo))
        conn.commit()
        id_nuevo = cursor.lastrowid
        return jsonify({"mensaje": "Usuario registrado", "usuario_id": id_nuevo}), 200
    except sqlite3.IntegrityError:
        return jsonify({"error": "El nombre de usuario ya existe"}), 409 # Conflict
    except Exception as e:
        return jsonify({"error": f"Error al registrar usuario: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/login_usuario', methods=['POST'])
def login_usuario():
    data = request.get_json()
    nombre = data.get('nombre')

    if not nombre:
        return jsonify({"error": "El nombre es requerido para iniciar sesión"}), 400

    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, tipo FROM usuarios WHERE nombre = ?", (nombre,))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"mensaje": "Login exitoso", "usuario_id": user[0], "tipo": user[1]}), 200
    else:
        return jsonify({"error": "Usuario no encontrado"}), 404

@app.route('/producto', methods=['POST'])
def cargar_producto():
    data = request.get_json()
    nombre = data.get('nombre')
    precio = data.get('precio')
    stock = data.get('stock')
    horario_retiro = data.get('horario_retiro')
    cafeteria_id = data.get('cafeteria_id')
    categoria = data.get('categoria', 'Bebida') # Valor por defecto 'Bebida' si no se especifica

    if not all([nombre, precio is not None, stock is not None, horario_retiro, cafeteria_id is not None]):
        return jsonify({"error": "Datos incompletos para el producto"}), 400
    if not isinstance(precio, (int, float)) or precio <= 0:
        return jsonify({"error": "El precio debe ser un número positivo"}), 400
    if not isinstance(stock, int) or stock < 0:
        return jsonify({"error": "El stock debe ser un número entero no negativo"}), 400

    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    try:
        # Verificar que el cafeteria_id existe y es de tipo 'cafeteria'
        cursor.execute("SELECT tipo FROM usuarios WHERE id = ?", (cafeteria_id,))
        user_type = cursor.fetchone()
        if not user_type or user_type[0] != 'cafeteria':
            return jsonify({"error": "Solo las cafeterías pueden cargar productos o el ID de cafetería no es válido"}), 403 # Forbidden

        cursor.execute("""
            INSERT INTO productos (nombre, precio, stock, horario_retiro, cafeteria_id, categoria)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (nombre, precio, stock, horario_retiro, cafeteria_id, categoria))
        conn.commit()
        return jsonify({"mensaje": "Producto cargado", "categoria": categoria}), 201 # Created
    except Exception as e:
        return jsonify({"error": f"Error al cargar producto: {str(e)}"}), 500
    finally:
        conn.close()

@app.route('/productos', methods=['GET'])
def listar_productos():
    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, precio, stock, horario_retiro, cafeteria_id, categoria FROM productos WHERE stock > 0") # Solo productos con stock > 0
    productos = cursor.fetchall()
    conn.close()

    if not productos:
        return jsonify([]), 200 # Devolver una lista vacía si no hay productos con stock

    return jsonify([{
        'id': p[0], 'nombre': p[1], 'precio': p[2], 'stock': p[3],
        'horario_retiro': p[4], 'cafeteria_id': p[5], 'categoria': p[6]
    } for p in productos]), 200

@app.route('/pedido', methods=['POST'])
def hacer_pedido():
    data = request.get_json()
    usuario_id = data.get('usuario_id')
    producto_id = data.get('producto_id')
    horario_retiro = data.get('horario_retiro')
    cantidad = data.get('cantidad', 1) # Añadimos cantidad, por defecto 1

    if not all([usuario_id, producto_id, horario_retiro, cantidad is not None]):
        return jsonify({"error": "Datos incompletos para el pedido"}), 400
    if not isinstance(cantidad, int) or cantidad <= 0:
        return jsonify({"error": "La cantidad debe ser un número entero positivo"}), 400

    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    try:
        # 1. Verificar si el producto existe y tiene stock suficiente
        cursor.execute("SELECT nombre, stock, precio FROM productos WHERE id = ?", (producto_id,))
        producto = cursor.fetchone()
        if not producto:
            return jsonify({"error": "Producto no encontrado"}), 404
        
        nombre_producto, stock_actual, precio_unitario = producto

        if stock_actual < cantidad:
            return jsonify({"error": f"Stock insuficiente para {nombre_producto}. Stock disponible: {stock_actual}"}), 400

        # 2. Reducir el stock del producto
        nuevo_stock = stock_actual - cantidad
        cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, producto_id))

        # 3. Registrar el pedido
        cursor.execute("INSERT INTO pedidos (usuario_id, producto_id, estado, horario_retiro, cantidad_pedida, precio_unitario_al_comprar) VALUES (?, ?, ?, ?, ?, ?)",
                       (usuario_id, producto_id, 'pendiente', horario_retiro, cantidad, precio_unitario))
        
        conn.commit()
        return jsonify({"mensaje": "Pedido registrado y stock actualizado"}), 201 # Created
    except Exception as e:
        conn.rollback() # Revertir cualquier cambio si hay un error
        return jsonify({"error": f"Error al hacer el pedido: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/pedidos/<int:usuario_id>', methods=['GET'])
def ver_pedidos_cliente(usuario_id):
    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            pedidos.id,
            productos.nombre,
            pedidos.cantidad_pedida,
            pedidos.precio_unitario_al_comprar,
            pedidos.estado,
            pedidos.horario_retiro,
            usuarios_cafeteria.nombre as nombre_cafeteria
        FROM pedidos
        JOIN productos ON pedidos.producto_id = productos.id
        JOIN usuarios AS usuarios_cafeteria ON productos.cafeteria_id = usuarios_cafeteria.id
        WHERE pedidos.usuario_id = ?
        ORDER BY pedidos.id DESC''', (usuario_id,))
    pedidos = cursor.fetchall()
    conn.close()

    if not pedidos:
        return jsonify({"mensaje": "No hay pedidos para este usuario"}), 200 # No 404, solo informamos que no hay

    return jsonify([{
        'id': p[0],
        'producto': p[1],
        'cantidad': p[2],
        'precio_unitario': p[3],
        'estado': p[4],
        'horario_retiro': p[5],
        'cafeteria': p[6]
    } for p in pedidos]), 200

# NUEVO ENDPOINT: Ver pedidos para una cafetería
@app.route('/pedidos_cafeteria/<int:cafeteria_id>', methods=['GET'])
def ver_pedidos_cafeteria(cafeteria_id):
    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()

    # Verificar que el cafeteria_id existe y es de tipo 'cafeteria'
    cursor.execute("SELECT tipo FROM usuarios WHERE id = ?", (cafeteria_id,))
    user_type = cursor.fetchone()
    if not user_type or user_type[0] != 'cafeteria':
        conn.close()
        return jsonify({"error": "ID de cafetería no válido o no autorizado"}), 403 # Forbidden

    cursor.execute('''
        SELECT
            pedidos.id,
            usuarios_cliente.nombre as nombre_cliente,
            productos.nombre as nombre_producto,
            pedidos.cantidad_pedida,
            pedidos.precio_unitario_al_comprar,
            pedidos.estado,
            pedidos.horario_retiro
        FROM pedidos
        JOIN productos ON pedidos.producto_id = productos.id
        JOIN usuarios AS usuarios_cliente ON pedidos.usuario_id = usuarios_cliente.id
        WHERE productos.cafeteria_id = ?
        ORDER BY pedidos.id DESC''', (cafeteria_id,))
    pedidos = cursor.fetchall()
    conn.close()

    if not pedidos:
        return jsonify({"mensaje": "No hay pedidos para esta cafetería"}), 200

    return jsonify([{
        'id': p[0],
        'cliente': p[1],
        'producto': p[2],
        'cantidad': p[3],
        'precio_unitario': p[4],
        'estado': p[5],
        'horario_retiro': p[6]
    } for p in pedidos]), 200


@app.route('/pedido/<int:pedido_id>', methods=['PUT'])
def actualizar_estado_pedido(pedido_id): # Renombrado para mayor claridad
    data = request.get_json()
    estado = data.get('estado')
    cafeteria_id_solicitante = data.get('cafeteria_id_solicitante') # Añadimos este para verificación

    if not estado:
        return jsonify({"error": "El estado es requerido"}), 400
    if estado not in ['pendiente', 'completado', 'cancelado']:
        return jsonify({"error": "Estado inválido. Debe ser 'pendiente', 'completado' o 'cancelado'"}), 400
    if not cafeteria_id_solicitante:
        return jsonify({"error": "ID de cafetería solicitante es requerido"}), 400

    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()
    try:
        # Verificar que el pedido existe y pertenece a la cafetería solicitante
        cursor.execute('''
            SELECT p.id
            FROM pedidos p
            JOIN productos pr ON p.producto_id = pr.id
            WHERE p.id = ? AND pr.cafeteria_id = ?''', (pedido_id, cafeteria_id_solicitante))
        pedido_existente = cursor.fetchone()

        if not pedido_existente:
            return jsonify({"error": "Pedido no encontrado o no autorizado para esta cafetería"}), 404 # Not Found o Forbidden

        cursor.execute("UPDATE pedidos SET estado = ? WHERE id = ?", (estado, pedido_id))
        conn.commit()
        return jsonify({"mensaje": "Estado del pedido actualizado"}), 200
    except Exception as e:
        return jsonify({"error": f"Error al actualizar pedido: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/csv_pedidos/<int:usuario_id>', methods=['GET'])
def generar_csv_cliente(usuario_id): # Renombrado para mayor claridad
    conn = sqlite3.connect('cafeya.db')
    # Consulta más robusta para incluir nombre del producto y cafetería
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            usuarios_cliente.nombre as cliente,
            productos.nombre as producto,
            pedidos.cantidad_pedida,
            pedidos.precio_unitario_al_comprar,
            pedidos.estado,
            pedidos.horario_retiro,
            usuarios_cafeteria.nombre as cafeteria
        FROM pedidos
        JOIN productos ON pedidos.producto_id = productos.id
        JOIN usuarios AS usuarios_cliente ON pedidos.usuario_id = usuarios_cliente.id
        JOIN usuarios AS usuarios_cafeteria ON productos.cafeteria_id = usuarios_cafeteria.id
        WHERE pedidos.usuario_id = ?
        ORDER BY pedidos.id DESC''', (usuario_id,))
    data = cursor.fetchall()
    conn.close()

    if not data:
        return jsonify({"mensaje": "No hay pedidos para este usuario"}), 200 # Cambiado a 200

    df = pd.DataFrame(data, columns=["Cliente", "Producto", "Cantidad", "Precio Unitario", "Estado", "Horario Retiro", "Cafeteria"])
    archivo = f"pedidos_cliente_{usuario_id}.csv"
    df.to_csv(archivo, index=False)
    return jsonify({"mensaje": "CSV generado", "archivo": archivo}), 200

# NUEVO ENDPOINT: Generar CSV de ventas para una cafetería
@app.route('/csv_ventas_cafeteria/<int:cafeteria_id>', methods=['GET'])
def generar_csv_cafeteria(cafeteria_id):
    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()

    # Verificar que el cafeteria_id existe y es de tipo 'cafeteria'
    cursor.execute("SELECT tipo FROM usuarios WHERE id = ?", (cafeteria_id,))
    user_type = cursor.fetchone()
    if not user_type or user_type[0] != 'cafeteria':
        conn.close()
        return jsonify({"error": "ID de cafetería no válido o no autorizado"}), 403

    cursor.execute('''
        SELECT
            productos.nombre as producto,
            pedidos.cantidad_pedida,
            pedidos.precio_unitario_al_comprar,
            pedidos.cantidad_pedida * pedidos.precio_unitario_al_comprar AS precio_total,
            pedidos.estado,
            pedidos.horario_retiro,
            usuarios_cliente.nombre as cliente
        FROM pedidos
        JOIN productos ON pedidos.producto_id = productos.id
        JOIN usuarios AS usuarios_cliente ON pedidos.usuario_id = usuarios_cliente.id
        WHERE productos.cafeteria_id = ?
        ORDER BY pedidos.id DESC''', (cafeteria_id,))
    data = cursor.fetchall()
    conn.close()

    if not data:
        return jsonify({"mensaje": "No hay ventas registradas para esta cafetería"}), 200

    df = pd.DataFrame(data, columns=["Producto", "Cantidad Vendida", "Precio Unitario", "Precio Total", "Estado Pedido", "Horario Retiro", "Cliente"])
    archivo = f"ventas_cafeteria_{cafeteria_id}.csv"
    df.to_csv(archivo, index=False)
    return jsonify({"mensaje": "CSV de ventas generado", "archivo": archivo}), 200


@app.route('/grafico_pedidos/<int:cafeteria_id>', methods=['GET'])
def grafico_pedidos_cafeteria(cafeteria_id): # Renombrado para mayor claridad
    conn = sqlite3.connect('cafeya.db')
    cursor = conn.cursor()

    # Verificar que el cafeteria_id existe y es de tipo 'cafeteria'
    cursor.execute("SELECT tipo FROM usuarios WHERE id = ?", (cafeteria_id,))
    user_type = cursor.fetchone()
    if not user_type or user_type[0] != 'cafeteria':
        conn.close()
        return jsonify({"error": "ID de cafetería no válido o no autorizado"}), 403

    query = '''
        SELECT pr.nombre, SUM(p.cantidad_pedida) AS cantidad_total_pedida
        FROM pedidos p
        JOIN productos pr ON p.producto_id = pr.id
        WHERE pr.cafeteria_id = ?
        GROUP BY pr.nombre
        ORDER BY cantidad_total_pedida DESC
    '''
    df = pd.read_sql_query(query, conn, params=(cafeteria_id,))
    conn.close()

    if df.empty:
        return jsonify({"mensaje": "No hay pedidos para generar el gráfico"}), 200 # Cambiado a 200

    plt.figure(figsize=(10, 6))
    plt.barh(df['nombre'], df['cantidad_total_pedida'], color='skyblue')
    plt.xlabel("Cantidad Total Pedida")
    plt.ylabel("Producto")
    plt.title(f"Total de Pedidos por Producto para Cafetería {cafeteria_id}")
    plt.tight_layout()

    nombre_archivo = f"grafico_pedidos_cafeteria_{cafeteria_id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(nombre_archivo)
    plt.close()

    return jsonify({"mensaje": "Gráfico de pedidos generado", "archivo": nombre_archivo}), 200

@app.route('/clima_bsas', methods=['GET'])
def clima_bsas():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast?latitude=-34.6&longitude=-58.4&current_weather=true")
        r.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        datos = r.json()
        temp = datos["current_weather"]["temperature"]
        recomendacion = "Una bebida fría como un licuado 🍹" if temp > 22 else "Un café caliente ☕"
        return jsonify({"temperatura": temp, "recomendacion": recomendacion}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error al obtener datos del clima: {str(e)}"}), 500
    except KeyError:
        return jsonify({"error": "Datos de clima incompletos o en formato inesperado"}), 500
    except Exception as e:
        return jsonify({"error": f"Ocurrió un error inesperado al obtener el clima: {str(e)}"}), 500

if __name__ == '__main__':
    # Eliminar gráficos antiguos al iniciar la aplicación (opcional, para limpieza)
    for file in os.listdir('.'):
        if file.startswith('grafico_cafeteria_') and file.endswith('.png'):
            os.remove(file)
    app.run(debug=True)