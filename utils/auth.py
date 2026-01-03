"""
Módulo de autenticación y autorización para ASIS CIMMA
"""

import streamlit as st
import hashlib
import time
from functools import wraps
from typing import Optional, Dict, Any, Callable
import json
import os
from datetime import datetime, timedelta

# Configuración de sesión
SESSION_TIMEOUT = 3600  # 1 hora en segundos

def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando SHA-256
    """
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(input_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña ingresada coincide con el hash almacenado
    """
    return hash_password(input_password) == hashed_password

def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Obtiene el usuario actualmente autenticado
    """
    if 'user' not in st.session_state:
        return None
    
    # Verificar tiempo de sesión
    if 'last_activity' in st.session_state:
        last_activity = st.session_state['last_activity']
        if time.time() - last_activity > SESSION_TIMEOUT:
            logout_user()
            return None
    
    # Actualizar tiempo de actividad
    st.session_state['last_activity'] = time.time()
    
    return st.session_state.get('user')

def set_current_user(user_data: Dict[str, Any]) -> None:
    """
    Establece el usuario actual en la sesión
    """
    st.session_state['user'] = user_data
    st.session_state['last_activity'] = time.time()
    st.session_state['authenticated'] = True

def logout_user() -> None:
    """
    Cierra la sesión del usuario
    """
    keys_to_clear = ['user', 'authenticated', 'last_activity']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def is_authenticated() -> bool:
    """
    Verifica si hay un usuario autenticado
    """
    user = get_current_user()
    return user is not None and st.session_state.get('authenticated', False)

def require_login(role: Optional[str] = None):
    """
    Decorador para requerir autenticación en una función
    
    Args:
        role: Rol requerido (opcional). Si se especifica, 
              el usuario debe tener este rol para acceder.
    
    Returns:
        Función decorada que verifica autenticación
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Verificar autenticación
            if not is_authenticated():
                st.error("🔒 Debes iniciar sesión para acceder a esta página")
                st.session_state['redirect_to'] = st.experimental_get_query_params()
                show_login_form()
                return
            
            # Verificar rol si se especificó
            if role is not None:
                user = get_current_user()
                if user and user.get('role') != role:
                    st.error(f"⚠️ No tienes permisos para acceder a esta página. Se requiere rol: {role}")
                    st.stop()
            
            # Ejecutar la función original
            return func(*args, **kwargs)
        return wrapper
    return decorator

def require_any_role(roles: list):
    """
    Decorador para requerir cualquiera de los roles especificados
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                st.error("🔒 Debes iniciar sesión para acceder a esta página")
                show_login_form()
                return
            
            user = get_current_user()
            if user and user.get('role') not in roles:
                st.error(f"⚠️ No tienes permisos para acceder a esta página")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def show_login_form(redirect_after_login: str = None):
    """
    Muestra el formulario de inicio de sesión
    """
    st.title("🔐 Inicio de Sesión - ASIS CIMMA")
    
    with st.form("login_form"):
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("assets/LOGO.png", width=150)
        
        with col2:
            st.markdown("### Acceso al Sistema")
            
            username = st.text_input("👤 Usuario o Email")
            password = st.text_input("🔑 Contraseña", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit = st.form_submit_button("🚀 Iniciar Sesión", use_container_width=True)
            
            with col_btn2:
                if st.form_submit_button("📝 Registrarse", use_container_width=True):
                    st.session_state['show_register'] = True
                    st.rerun()
        
        if submit:
            if authenticate_user(username, password):
                st.success("✅ ¡Inicio de sesión exitoso!")
                time.sleep(1)
                
                # Redireccionar si hay una página destino
                if redirect_after_login:
                    st.experimental_set_query_params(page=redirect_after_login)
                else:
                    st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")

def authenticate_user(username: str, password: str) -> bool:
    """
    Autentica un usuario con las credenciales proporcionadas
    Ahora lee las credenciales desde secrets.toml
    """
    try:
        # Obtener usuarios desde secrets
        usuarios_secrets = st.secrets.get("usuarios", {})
        
        if not usuarios_secrets:
            st.error("No hay usuarios configurados en secrets.toml")
            return False
        
        # Verificar si el usuario existe en secrets
        if username not in usuarios_secrets:
            # También verificar por email si se proporciona como username
            # Buscar en todos los usuarios si username podría ser un email
            return False
        
        # Obtener contraseña desde secrets (en texto plano)
        password_correcta = usuarios_secrets[username]
        
        # Verificar contraseña (comparación directa, sin hash por ahora)
        # Si quieres usar hash, deberías almacenar hashes en secrets
        if password == password_correcta:
            # Determinar rol basado en el username o configuración adicional
            role = determinar_rol_usuario(username)
            
            # Determinar sede basada en el username
            sede = determinar_sede_usuario(username)
            
            # Crear datos de usuario para la sesión
            user_data = {
                "username": username,
                "nombre": username.upper(),  # O puedes tener un diccionario de nombres
                "email": f"{username}@asis-cimma.com",
                "role": role,
                "sede": sede,
                "id": hash(username) % 10000  # ID único basado en username
            }
            
            # Asignar ID específico si es admin o profesor
            if role == "admin":
                user_data["id"] = 1
            elif role == "profesor":
                user_data["id"] = 101
                user_data["id_profesor"] = 101
            
            set_current_user(user_data)
            return True
        
        return False
        
    except Exception as e:
        st.error(f"Error en autenticación: {str(e)}")
        return False

def determinar_rol_usuario(username: str) -> str:
    """
    Determina el rol del usuario basado en el username.
    Puedes personalizar esta lógica según tus necesidades.
    """
    # Lista de administradores
    admins = ["admin", "administrador", "sysadmin"]
    
    # Lista de profesores
    profesores = ["profesor", "prof", "teacher", "docente"]
    
    # Convertir a minúsculas para comparación
    username_lower = username.lower()
    
    # Verificar si es admin
    for admin_key in admins:
        if admin_key in username_lower:
            return "admin"
    
    # Verificar si es profesor
    for prof_key in profesores:
        if prof_key in username_lower:
            return "profesor"
    
    # Por defecto, es secretaria/equipo sede
    return "secretaria"

def determinar_sede_usuario(username: str) -> str:
    """
    Determina la sede del usuario basado en el username.
    """
    username_lower = username.lower()
    
    # Mapeo de sedes
    sedes_mapping = {
        'sp': 'SAN PEDRO',
        'sanpedro': 'SAN PEDRO',
        'san pedro': 'SAN PEDRO',
        'lomas': 'LOMAS',
        'chillan': 'CHILLAN',
        'chillán': 'CHILLAN',
        'pv': 'PEDRO DE VALDIVIA',
        'pedrovaldivia': 'PEDRO DE VALDIVIA',
        'pedro valdivia': 'PEDRO DE VALDIVIA',
        'conce': 'CONCEPCIÓN',
        'concepción': 'CONCEPCIÓN',
        'concepcion': 'CONCEPCIÓN'
    }
    
    # Buscar coincidencias
    for key, sede in sedes_mapping.items():
        if key in username_lower:
            return sede
    
    # Si no se encuentra, usar sede por defecto o de secrets
    try:
        # Intentar obtener desde secrets
        if "usuarios_sede" in st.secrets:
            return st.secrets["usuarios_sede"].get(username, "TODAS")
    except:
        pass
    
    return "TODAS"

def register_user(username: str, password: str, email: str, role: str = "user", 
                  extra_data: Dict[str, Any] = None) -> bool:
    """
    Registra un nuevo usuario
    """
    # Validaciones básicas
    if not username or not password or not email:
        st.error("Todos los campos son requeridos")
        return False
    
    if len(password) < 6:
        st.error("La contraseña debe tener al menos 6 caracteres")
        return False
    
    st.success(f"Usuario {username} registrado exitosamente")
    
    # Autenticar automáticamente después del registro
    return authenticate_user(username, password)

def show_register_form():
    """
    Muestra el formulario de registro
    """
    st.title("📝 Registro de Nuevo Usuario")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre Completo")
            email = st.text_input("Email")
            username = st.text_input("Nombre de Usuario")
        
        with col2:
            password = st.text_input("Contraseña", type="password")
            confirm_password = st.text_input("Confirmar Contraseña", type="password")
            role = st.selectbox("Tipo de Usuario", ["Alumno", "Profesor", "Secretaria"])
        
        col_submit, col_back = st.columns(2)
        with col_submit:
            submit = st.form_submit_button("✅ Registrar", use_container_width=True)
        
        with col_back:
            if st.form_submit_button("↩️ Volver", use_container_width=True):
                st.session_state.pop('show_register', None)
                st.rerun()
        
        if submit:
            if password != confirm_password:
                st.error("Las contraseñas no coinciden")
                return
            
            success = register_user(
                username=username,
                password=password,
                email=email,
                role=role.lower(),
                extra_data={"nombre": nombre}
            )
            
            if success:
                time.sleep(2)
                st.rerun()

def get_all_users() -> list:
    """
    Obtiene todos los usuarios del sistema desde secrets
    """
    try:
        usuarios_secrets = st.secrets.get("usuarios", {})
        
        users = []
        for i, (username, _) in enumerate(usuarios_secrets.items(), 1):
            users.append({
                "id": i,
                "username": username,
                "nombre": username.upper(),
                "email": f"{username}@asis-cimma.com",
                "role": determinar_rol_usuario(username),
                "estado": "Activo",
                "ultimo_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sede": determinar_sede_usuario(username)
            })
        
        return users
        
    except Exception as e:
        print(f"Error obteniendo usuarios: {e}")
        # Datos de ejemplo como fallback
        return [
            {
                "id": 1,
                "username": "admin",
                "nombre": "Administrador",
                "email": "admin@asis-cimma.com",
                "role": "admin",
                "estado": "Activo",
                "ultimo_login": "2024-01-15 10:30:00",
                "sede": "TODAS"
            }
        ]

def check_permission(user_role: str, required_role: str) -> bool:
    """
    Verifica si un usuario tiene el permiso requerido
    
    Jerarquía de roles: admin > secretaria > profesor > user
    """
    role_hierarchy = {
        'admin': 4,
        'secretaria': 3,
        'profesor': 2,
        'user': 1
    }
    
    user_level = role_hierarchy.get(user_role, 0)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Obtiene un usuario por su ID
    """
    users = get_all_users()
    for user in users:
        if user['id'] == user_id:
            return user
    return None

def update_user_last_login(user_id: int):
    """
    Actualiza la fecha del último login de un usuario
    """
    pass

# Para uso en desarrollo
if __name__ == "__main__":
    # Pruebas básicas
    print("🔧 Probando módulo de autenticación...")
    
    # Test hash
    test_password = "test123"
    hashed = hash_password(test_password)
    print(f"Hash de '{test_password}': {hashed[:10]}...")
    
    # Test verify
    print(f"Verificación correcta: {verify_password('test123', hashed)}")
    print(f"Verificación incorrecta: {verify_password('wrong', hashed)}")