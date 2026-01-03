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
    
    En producción, esto debería conectarse a una base de datos real.
    Por ahora usaremos datos de ejemplo.
    """
    # Datos de ejemplo (en producción, obtener de base de datos)
    users_db = {
        "admin": {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "nombre": "Administrador",
            "email": "admin@asis-cimma.com",
            "role": "admin",
            "id": 1
        },
        "profesor": {
            "username": "profesor",
            "password_hash": hash_password("profesor123"),
            "nombre": "Profesor Demo",
            "email": "profesor@demo.com",
            "role": "profesor",
            "id_profesor": 101,
            "id": 2
        },
        "secretaria": {
            "username": "secretaria",
            "password_hash": hash_password("secretaria123"),
            "nombre": "Secretaria Demo",
            "email": "secretaria@demo.com",
            "role": "secretaria",
            "id": 3
        }
    }
    
    # Buscar usuario por username o email
    user_data = None
    for user_key, user_info in users_db.items():
        if (username == user_info['username'] or 
            username == user_info.get('email', '')):
            user_data = user_info
            break
    
    if not user_data:
        return False
    
    # Verificar contraseña
    if verify_password(password, user_data['password_hash']):
        # Remover el hash de la contraseña antes de almacenar en sesión
        user_session_data = user_data.copy()
        user_session_data.pop('password_hash', None)
        
        set_current_user(user_session_data)
        return True
    
    return False

def register_user(username: str, password: str, email: str, role: str = "user", 
                  extra_data: Dict[str, Any] = None) -> bool:
    """
    Registra un nuevo usuario
    
    En producción, esto guardaría en una base de datos real.
    """
    # Validaciones básicas
    if not username or not password or not email:
        st.error("Todos los campos son requeridos")
        return False
    
    if len(password) < 6:
        st.error("La contraseña debe tener al menos 6 caracteres")
        return False
    
    # Aquí iría la lógica para guardar en base de datos
    # Por ahora solo mostramos un mensaje de éxito
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
    Obtiene todos los usuarios del sistema
    
    En producción, esto consultaría una base de datos.
    """
    # Datos de ejemplo
    return [
        {
            "id": 1,
            "username": "admin",
            "nombre": "Administrador",
            "email": "admin@asis-cimma.com",
            "role": "admin",
            "estado": "Activo",
            "ultimo_login": "2024-01-15 10:30:00"
        },
        {
            "id": 2,
            "username": "profesor",
            "nombre": "Profesor Demo",
            "email": "profesor@demo.com",
            "role": "profesor",
            "estado": "Activo",
            "ultimo_login": "2024-01-15 09:15:00"
        },
        {
            "id": 3,
            "username": "secretaria",
            "nombre": "Secretaria Demo",
            "email": "secretaria@demo.com",
            "role": "secretaria",
            "estado": "Activo",
            "ultimo_login": "2024-01-15 08:45:00"
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
    
    En producción, esto actualizaría la base de datos.
    """
    # Esta es una implementación de ejemplo
    # En producción, actualizarías la base de datos
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