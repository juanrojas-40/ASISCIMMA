# utils/auth.py
import streamlit as st
from typing import Dict, Optional

class AuthManager:
    """Manejador de autenticación usando secrets de Streamlit"""

    def __init__(self):
        self.role_mapping = {
            "👨‍🏫 Profesor": "profesor",
            "👩‍💼 Equipo Sede": "equipo_sede",
            "👨‍💼 Administrador": "admin"
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

        for category, key in required_secrets:
            try:
                if category not in st.secrets:
                    return False
                if key and key not in st.secrets[category]:
                    return False
            except:
                return False

        return True

    def login(self, username: str, password: str, role_display: str) -> bool:
        """Autentica un usuario usando secrets de Streamlit"""
        try:
            # Obtener rol real del mapeo
            role = self.role_mapping.get(role_display, "profesor")

            # Verificar credenciales en secrets
            # Nota: En producción, usar hash de contraseñas
            usuarios = st.secrets.get("usuarios", {})
            # Verificar usuario y contraseña
            if username in usuarios and usuarios[username] == password:
                # Guardar en sesión
                st.session_state.user = username
                st.session_state.role = role_display
                st.session_state.role_type = role
                st.session_state.authenticated = True
                return True

            return False

        except Exception as e:
            st.error(f"Error en autenticación: {e}")
            return False

    def logout(self):
        """Cierra la sesión del usuario"""
        for key in ['authenticated', 'user', 'role', 'role_type', 'sede']:
            if key in st.session_state:
                del st.session_state[key]

    def get_current_user(self) -> Optional[Dict]:
        """Obtiene información del usuario actual"""
        if not st.session_state.get("authenticated", False):
            return None

        return {
            "username": st.session_state.get("user"),
            "role": st.session_state.get("role"),
            "role_type": st.session_state.get("role_type")
        }

    def require_auth(self):
        """Decorador para requerir autenticación"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if not st.session_state.get("authenticated", False):
                    st.warning("Debe iniciar sesión para acceder a esta página")
                    st.stop()
                return func(*args, **kwargs)
            return wrapper
        return decorator