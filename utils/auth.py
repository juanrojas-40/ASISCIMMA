# utils/auth.py
import streamlit as st
import time
import random
from typing import Dict, Optional


class AuthManager:
    """Manejador de autenticación usando secrets de Streamlit"""
    
    def __init__(self):
        self.role_mapping = {
            "👨‍🏫 Profesor": "profesor",
            "👩‍💼 Equipo Sede": "Equipo Sede", 
            "👑 Administrador": "admin"
        }
    
    def check_secrets(self) -> bool:
        """Verifica que todos los secrets necesarios estén configurados"""
        required_secrets = [
            ("google", "credentials"),
            ("google", "asistencia_sheet_id"),
            ("google", "clases_sheet_id"),
            ("EMAIL", "smtp_server"),
            ("EMAIL", "smtp_port"),
            ("EMAIL", "sender_email"),
            ("EMAIL", "sender_password"),
            ("usuarios", None)  # Solo verificar que existe la sección
        ]
        
        missing = []
        for category, key in required_secrets:
            try:
                if category not in st.secrets:
                    missing.append(f"Sección [{category}]")
                    continue
                if key and key not in st.secrets[category]:
                    missing.append(f"{category}.{key}")
            except Exception:
                missing.append(f"{category}.{key or 'sección completa'}")
        
        if missing:
            st.error("❌ **Faltan configuraciones en secrets.toml**")
            for item in missing:
                st.write(f"- {item}")
            st.info("💡 Revisa la guía de configuración en la página de login")
            return False
        
        return True
    
    def login(self, username: str, password: str, role_display: str) -> bool:
        """Autentica un usuario usando secrets de Streamlit"""
        try:
            # Validación básica de entrada
            if not username or not password or not role_display:
                st.error("❌ Todos los campos son obligatorios")
                time.sleep(1)
                return False

            username = username.strip()
            password = password.strip()

            if len(username) > 50 or len(password) > 100:
                st.error("❌ Credenciales inválidas (demasiado largas)")
                time.sleep(2)
                return False

            # Obtener rol interno
            role = self.role_mapping.get(role_display)
            if not role:
                st.error("❌ Rol seleccionado no válido")
                time.sleep(1)
                return False

            # Cargar usuarios desde secrets
            usuarios = st.secrets.get("usuarios", {})
            if not usuarios:
                st.error("❌ No hay usuarios configurados en secrets")
                return False

            # Verificación de credenciales
            stored_password = usuarios.get(username)

            if stored_password is not None and stored_password == password:
                # Login exitoso
                st.session_state.authenticated = True
                st.session_state.user = username
                st.session_state.role = role_display
                st.session_state.role_type = role
                
                st.success(f"✅ Bienvenido/a, {username}!")
                time.sleep(0.5)
                st.rerun()
                return True
            else:
                # Login fallido - medida anti-fuerza bruta
                delay = random.uniform(1.5, 3.0)
                time.sleep(delay)
                st.error("❌ Credenciales incorrectas o usuario no autorizado")
                
                # Mensaje sutil de ayuda
                with st.expander("¿Problemas para ingresar?"):
                    st.markdown("""
                    - Verifica mayúsculas/minúsculas
                    - Usa las credenciales de prueba si estás evaluando
                    - Contacta al administrador si olvidaste tu contraseña
                    """)
                return False

        except Exception as e:
            # Nunca exponer detalles del error
            st.error("❌ Error en el sistema de autenticación. Intenta nuevamente.")
            time.sleep(2)
            return False
    
    def logout(self):
        """Cierra la sesión del usuario de forma segura"""
        keys_to_clear = ['authenticated', 'user', 'role', 'role_type', 'sede']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.success("👋 Sesión cerrada correctamente")
        time.sleep(0.8)
        st.rerun()
    
    def get_current_user(self) -> Optional[Dict]:
        """Obtiene información del usuario actual de forma segura"""
        if not st.session_state.get("authenticated", False):
            return None
        
        return {
            "username": st.session_state.get("user"),
            "role": st.session_state.get("role"),
            "role_type": st.session_state.get("role_type")
        }
    
    def require_auth(self):
        """Decorador para requerir autenticación en páginas"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not st.session_state.get("authenticated", False):
                    st.warning("🔒 Debes iniciar sesión para acceder a esta sección")
                    st.stop()
                return func(*args, **kwargs)
            return wrapper
        return decorator