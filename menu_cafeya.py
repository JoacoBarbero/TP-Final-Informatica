import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:5000"  # Asegúrate de que esta URL coincida con la de tu Flask app

usuario_actual = {
    "id": None,
    "nombre": None,
    "tipo": None
}

def mostrar_respuesta(response):
    """Muestra el código de estado y el contenido JSON/texto de una respuesta HTTP."""
    print(f"\nCódigo de estado: {response.status_code}")
    try:
        print(response.json())
    except ValueError:
        print("⚠️ La respuesta no es JSON:")
        print(response.text)

def registrar_usuario():
    """Registra un nuevo usuario."""
    nombre = input("Nombre de usuario: ")
    tipo = input("Tipo de usuario (cliente/cafeteria): ").lower()
    if tipo not in ["cliente", "cafeteria"]:
        print("Tipo de usuario inválido. Debe ser 'cliente' o 'cafeteria'.")
        return False
    data = {"nombre": nombre, "tipo": tipo}
    try:
        response = requests.post(f"{BASE_URL}/registrar_usuario", json=data)
        if response.status_code == 200:
            resultado = response.json()
            usuario_actual["id"] = resultado["usuario_id"]
            usuario_actual["nombre"] = nombre
            usuario_actual["tipo"] = tipo
            print(f"✅ Registrado como {tipo} con ID {usuario_actual['id']}")
            return True
        else:
            mostrar_respuesta(response)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor. Asegúrate de que el backend está corriendo.")
        return False

def login_usuario():
    """Inicia sesión para un usuario existente."""
    nombre = input("Nombre de usuario: ")
    data = {"nombre": nombre}
    try:
        response = requests.post(f"{BASE_URL}/login_usuario", json=data)
        if response.status_code == 200:
            resultado = response.json()
            usuario_actual["id"] = resultado["usuario_id"]
            usuario_actual["nombre"] = nombre
            usuario_actual["tipo"] = resultado["tipo"]
            print(f"🔓 Login exitoso como {usuario_actual['tipo']} (ID: {usuario_actual['id']})")
            return True
        else:
            mostrar_respuesta(response)
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor. Asegúrate de que el backend está corriendo.")
        return False

# Funciones para Clientes
def listar_productos():
    """Lista todos los productos disponibles."""
    try:
        response = requests.get(f"{BASE_URL}/productos")
        if response.status_code == 200:
            productos = response.json()
            if productos:
                df = pd.DataFrame(productos)
                print("\n☕ Productos disponibles:")
                print(df[['id', 'nombre', 'precio', 'stock', 'horario_retiro', 'categoria']].to_string(index=False))
            else:
                print("⚠️ No hay productos disponibles en este momento.")
        else:
            mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")

def hacer_pedido():
    """Permite al cliente realizar un pedido."""
    listar_productos()
    producto_id = input("ID del producto a pedir: ")
    horario_retiro = input("Horario de retiro (ej. '10:30'): ")
    data = {
        "usuario_id": usuario_actual["id"],
        "producto_id": int(producto_id),
        "horario_retiro": horario_retiro
    }
    try:
        response = requests.post(f"{BASE_URL}/pedido", json=data)
        mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")

def ver_pedidos_cliente():
    """Muestra los pedidos del cliente actual."""
    try:
        response = requests.get(f"{BASE_URL}/pedidos/{usuario_actual['id']}")
        if response.status_code == 200:
            pedidos = response.json()
            if pedidos:
                df = pd.DataFrame(pedidos)
                print(f"\n📋 Tus Pedidos ({usuario_actual['nombre']}):")
                print(df.to_string(index=False))
            else:
                print("⚠️ No tienes pedidos registrados.")
        else:
            mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")

def generar_csv_pedidos_cliente():
    """Genera un CSV con los pedidos del cliente."""
    try:
        response = requests.get(f"{BASE_URL}/csv_pedidos/{usuario_actual['id']}")
        if response.status_code == 200:
            resultado = response.json()
            print(resultado["mensaje"])
            if "archivo" in resultado:
                print(f"Archivo generado: {resultado['archivo']}")
        else:
            mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")

def ver_clima_y_recomendacion():
    """Muestra el clima actual de Buenos Aires y una recomendación de bebida."""
    try:
        response = requests.get(f"{BASE_URL}/clima_bsas")
        if response.status_code == 200:
            clima = response.json()
            print(f"\n🌡️ Clima en Buenos Aires: {clima['temperatura']}°C")
            print(f"✨ Recomendación del día: {clima['recomendacion']}")
        else:
            mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")


# Funciones para Cafeterías
def cargar_producto_cafeteria():
    """Permite a la cafetería cargar un nuevo producto."""
    nombre = input("Nombre del producto: ")
    precio = float(input("Precio: "))
    stock = int(input("Stock: "))
    horario_retiro = input("Horario de retiro (ej. '09:00-18:00'): ")
    categoria = input("Categoría del producto (ej. 'bebida', 'comida'): ")
    data = {
        "nombre": nombre,
        "precio": precio,
        "stock": stock,
        "horario_retiro": horario_retiro,
        "categoria": categoria,
        "cafeteria_id": usuario_actual["id"]
    }
    try:
        response = requests.post(f"{BASE_URL}/producto", json=data)
        mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")
#Cambio por error en sintaxis en la función ver_y_actualizar_pedidos_cafeteria
def ver_y_actualizar_pedidos_cafeteria():
    """Permite a la cafetería ver y actualizar el estado de los pedidos."""
    try:
        # ... (código existente para listar productos de la cafetería, si aplica) ...

        print("\n⚠️ Esta función asume que conoces el ID de los pedidos a actualizar.")
        print("Actualmente, el backend no expone un listado de pedidos específico para cafeterías.")

        opcion = input("¿Desea actualizar un pedido existente? (s/n): ").lower()
        if opcion == 's':
            pedido_id = input("ID del pedido a actualizar: ")
            estado = input("Nuevo estado (pendiente/completado/cancelado): ").lower()
            if estado not in ["pendiente", "completado", "cancelado"]:
                print("Estado inválido. Debe ser 'pendiente', 'completado' o 'cancelado'.")
                return
            
            # --- MODIFICACIÓN AQUÍ ---
            data = {
                "estado": estado,
                "cafeteria_id_solicitante": usuario_actual["id"] # ¡Añadir esta línea!
            }
            # -------------------------

            try:
                response = requests.put(f"{BASE_URL}/pedido/{pedido_id}", json=data)
                mostrar_respuesta(response)
            except requests.exceptions.ConnectionError:
                print("❌ Error de conexión con el servidor.")

    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")


def generar_grafico_pedidos_cafeteria():
    """Genera un gráfico de pedidos para la cafetería."""
    try:
        response = requests.get(f"{BASE_URL}/grafico_pedidos/{usuario_actual['id']}")
        if response.status_code == 200:
            resultado = response.json()
            print(resultado["mensaje"])
            if "archivo" in resultado:
                print(f"Gráfico generado: {resultado['archivo']}")
        else:
            mostrar_respuesta(response)
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión con el servidor.")


# Menús por tipo de usuario
def menu_cliente():
    """Menú para usuarios tipo cliente."""
    while True:
        print(f"\n☕ Menú del Cliente ({usuario_actual['nombre']})")
        print("1. Listar productos")
        print("2. Hacer un pedido")
        print("3. Ver mis pedidos")
        print("4. Generar CSV de mis pedidos")
        print("5. Ver clima y recomendación")
        print("6. Cerrar sesión")
        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            listar_productos()
        elif opcion == "2":
            hacer_pedido()
        elif opcion == "3":
            ver_pedidos_cliente()
        elif opcion == "4":
            generar_csv_pedidos_cliente()
        elif opcion == "5":
            ver_clima_y_recomendacion()
        elif opcion == "6":
            print("🔒 Cerrando sesión...")
            return
        else:
            print("Opción inválida. Intente de nuevo.")

def menu_cafeteria():
    """Menú para usuarios tipo cafetería."""
    while True:
        print(f"\n🏪 Menú de la Cafetería ({usuario_actual['nombre']})")
        print("1. Cargar nuevo producto")
        print("2. Ver y actualizar estado de pedidos")
        print("3. Generar gráfico de pedidos por producto")
        print("4. Cerrar sesión")
        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            cargar_producto_cafeteria()
        elif opcion == "2":
            ver_y_actualizar_pedidos_cafeteria()
        elif opcion == "3":
            generar_grafico_pedidos_cafeteria()
        elif opcion == "4":
            print("🔒 Cerrando sesión...")
            return
        else:
            print("Opción inválida. Intente de nuevo.")

# Menú de inicio
def menu_inicio():
    """Menú inicial para registrarse o iniciar sesión."""
    while True:
        print("\n👋 Bienvenido a CaféYa!")
        print("1. Registrarse")
        print("2. Iniciar sesión")
        print("0. Salir del programa")
        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            if registrar_usuario():
                break
        elif opcion == "2":
            if login_usuario():
                break
        elif opcion == "0":
            print("👋 ¡Hasta pronto!")
            exit()
        else:
            print("Opción inválida. Intente de nuevo.")

# Control general del flujo
def main():
    """Función principal para controlar el flujo de la aplicación."""
    while True:
        menu_inicio()

        if usuario_actual["tipo"] == "cliente":
            menu_cliente()
        elif usuario_actual["tipo"] == "cafeteria":
            menu_cafeteria()
        else:
            print("⚠️ Tipo de usuario no reconocido. Volviendo al menú principal.")

        # Resetear sesión
        usuario_actual["id"] = None
        usuario_actual["nombre"] = None
        usuario_actual["tipo"] = None

if __name__ == "__main__":
    main()