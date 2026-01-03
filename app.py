# app.py - Punto de entrada principal del sistema de asistencia CIMMA
import streamlit as st

# ============================================================================
# CONFIGURACIÓN INICIAL - DEBE SER EL PRIMER COMANDO DE STREAMLIT
# ============================================================================
st.set_page_config(
    page_title="Sistema de Asistencia CIMMA",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS PERSONALIZADO
# ============================================================================
st.markdown("""
<style>
.main-header {
    color: #1A3B8F;
    font-size: 2.5rem;
    text-align: center;
    margin-bottom: 1rem;
}
.sub-header {
    color: #2D4FA8;
    font-size: 1.8rem;
    margin: 1.5rem 0 1rem 0;
    border-bottom: 2px solid #1A3B8F;
    padding-bottom: 0.5rem;
}
.card {
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    margin: 1rem 0;
}
.metric-card {
    background: linear-gradient(135deg, #1A3B8F 0%, #2D4FA8 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    text-align: center;
}
.stProgress > div > div > div > div {
    background-color: #1A3B8F;
}
.success-message {
    background-color: #d4edda;
    color: #155724;
    padding: 12px;
    border-radius: 5px;
    border: 1px solid #c3e6cb;
    margin: 10px 0;
}
.warning-message {
    background-color: #fff3cd;
    color: #856404;
    padding: 12px;
    border-radius: 5px;
    border: 1px solid #ffeaa7;
    margin: 10px 0;
}
.error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 12px;
    border-radius: 5px;
    border: 1px solid #f5c6cb;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

import sys
import os
import pandas as pd
from datetime import datetime
import io
import time

# ============================================================================
# CONFIGURACIÓN DE PATH E IMPORTS
# ============================================================================
# Agregar directorios al path
current_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(current_dir, 'utils'))
sys.path.append(os.path.join(current_dir, 'components'))
sys.path.append(os.path.join(current_dir, 'config'))

# ============================================================================
# IMPORTS DE MÓDULOS PERSONALIZADOS
# ============================================================================
try:
    # Configuración
    from config.settings import AppSettings
    
    # Utils principales
    from utils.google_sheets import GoogleSheetsManager
    from utils.email_sender import EmailManager
    from utils.send_apoderados import ApoderadosEmailSender
    from utils.auth import (
        require_login, 
        get_current_user, 
        authenticate_user,
        logout_user,
        is_authenticated,
        show_login_form,
        require_any_role,
        get_all_users,
        check_permission
    )
    from utils.error_handler import ErrorHandler
    from utils.cache_manager import CacheManager
    
    # Helpers
    from utils.helpers import (
        display_footer,
        export_to_excel,
        get_sede_from_username,
        format_porcentaje,
        get_current_datetime,
        get_date_only,
        create_progress_bar
    )
    
    # Components
    from components.sidebar import (
        render_sidebar,
        render_user_info,
        render_quick_stats
    )
    from components.headers import (
        render_main_header,
        render_section_header,
        render_metric_card
    )
    from components.modals import (
        show_confirmation_modal,
        show_info_modal,
        show_error_modal
    )
    
    # Páginas (modularizadas)
    from pages.profesor_dashboard import show_profesor_dashboard
    from pages.secretaria_dashboard import show_secretaria_dashboard
    from pages.admin_dashboard import show_admin_dashboard
    
    # Inicializar configuración
    settings = AppSettings.load_from_secrets()
    
except ImportError as e:
    st.error(f"✗ Error importando módulos: {e}")
    st.info("🔧 Asegúrate de que la estructura de carpetas sea correcta:")
    st.code("""
    app.py
    ├── config/
    │   ├── __init__.py
    │   ├── settings.py
    │   └── constants.py
    ├── utils/
    │   ├── __init__.py
    │   ├── google_sheets.py
    │   ├── email_sender.py
    │   ├── send_apoderados.py
    │   ├── auth.py
    │   ├── helpers.py
    │   ├── error_handler.py
    │   └── cache_manager.py
    ├── components/
    │   ├── __init__.py
    │   ├── sidebar.py
    │   ├── headers.py
    │   └── modals.py
    └── pages/
        ├── __init__.py
        ├── profesor_dashboard.py
        ├── secretaria_dashboard.py
        └── admin_dashboard.py
    """)
    
    # Mostrar detalles del error para debugging
    st.error(f"Detalles del error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()

# ============================================================================
# FUNCIONES PRINCIPALES DE LA APLICACIÓN
# ============================================================================
def initialize_session_state():
    """Inicializa el estado de sesión con valores predeterminados."""
    defaults = {
        "authenticated": False,
        "user": "",
        "role": "",
        "sede": "",
        "last_activity": datetime.now(),
        "page_views": 0,
        "debug_mode": settings.DEBUG_MODE,
        "last_refresh": datetime.now()
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def check_secrets_configuration():
    """Verifica que los secrets estén configurados correctamente."""
    try:
        # Verificar secrets básicos
        required_secrets = [
            "google.credentials",
            "google.asistencia_sheet_id", 
            "google.clases_sheet_id"
        ]
        
        for secret in required_secrets:
            keys = secret.split('.')
            value = st.secrets
            for key in keys:
                if key in value:
                    value = value[key]
                else:
                    st.error(f"✗ Secret no encontrado: {secret}")
                    return False
        
        return True
        
    except Exception as e:
        st.error(f"✗ Error verificando secrets: {e}")
        return False

def show_login_page():
    """Muestra la página de login."""
    render_main_header("🔄 Sistema de Asistencia CIMMA")
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div class="card">
            <h2 style="text-align: center; color: #1A3B8F;">🔐 Iniciar Sesión</h2>
            """, unsafe_allow_html=True)
            
            # Campos de login
            username = st.text_input("👤 Usuario", key="login_username")
            password = st.text_input("🔒 Contraseña", type="password", key="login_password")
            
            # Botón de login
            if st.button("🚀 Ingresar al Sistema", type="primary", use_container_width=True):
                if not username or not password:
                    st.error("⚠️ Por favor, completa todos los campos")
                    return
                
                # Usar authenticate_user directamente
                if authenticate_user(username, password):
                    user = get_current_user()
                    
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user = username
                        st.session_state.role = user.get('role', 'user').capitalize()
                        st.session_state.sede = user.get('sede', 'TODAS')
                        st.session_state.page_views = 0
                        st.session_state.last_activity = datetime.now()
                        
                        st.success(f"✅ ¡Bienvenido/a {username}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        ErrorHandler.handle_auth_error("Error al obtener datos del usuario")
                else:
                    ErrorHandler.handle_auth_error("Credenciales incorrectas")
            
            # Información de acceso
            with st.expander("ℹ️ Usuarios configurados"):
                try:
                    usuarios = st.secrets.get("usuarios", {})
                    if usuarios:
                        st.write("**Usuarios disponibles:**")
                        for user in usuarios:
                            st.write(f"- `{user}`")
                    else:
                        st.warning("No hay usuarios configurados en secrets")
                except:
                    st.info("Configura usuarios en secrets.toml")
            
            st.markdown("</div>", unsafe_allow_html=True)

def show_main_dashboard(sheets_manager, email_manager, apoderados_sender):
    """Muestra el dashboard principal después del login."""
    
    # Actualizar actividad
    st.session_state.last_activity = datetime.now()
    st.session_state.page_views += 1
    
    # Renderizar sidebar
    with st.sidebar:
        render_sidebar(sheets_manager)
    
    # Renderizar contenido principal basado en rol
    try:
        role = st.session_state.get("role", "").lower()
        
        if "profesor" in role:
            show_profesor_dashboard(sheets_manager, email_manager, apoderados_sender)
        elif "secretaria" in role or "sede" in role:
            show_secretaria_dashboard(sheets_manager, email_manager, apoderados_sender)
        elif "admin" in role:
            show_admin_dashboard(sheets_manager, email_manager, apoderados_sender)
        else:
            st.warning(f"⚠️ Rol '{st.session_state.role}' no reconocido. Contacte al administrador.")
    except Exception as e:
        st.error(f"❌ Error en el dashboard: {str(e)}")
        st.info("🔄 Intente recargar la página o contacte al administrador.")

def main():
    """Función principal de la aplicación."""
    
    # Inicializar estado de sesión
    initialize_session_state()
    
    # Inicializar managers con configuración
    sheets_manager = GoogleSheetsManager(debug_mode=settings.DEBUG_MODE)
    email_manager = EmailManager()
    apoderados_sender = ApoderadosEmailSender()
    
    # Verificar configuración de secrets
    if not check_secrets_configuration():
        return
    
    # Limpiar cache si está en modo debug
    if settings.DEBUG_MODE and st.session_state.page_views == 0:
        try:
            sheets_manager.clear_cache()
            st.info("🔧 Modo debug activado - Cache limpiado")
        except Exception as e:
            st.warning(f"⚠️ No se pudo limpiar el cache: {e}")
    
    # Mostrar página de login o dashboard principal
    if not st.session_state.get("authenticated", False):
        show_login_page()
    else:
        show_main_dashboard(sheets_manager, email_manager, apoderados_sender)
    
    # Footer
    display_footer()
    
    # Auto-refresh si está configurado
    if settings.AUTO_REFRESH > 0:
        time_since_refresh = (datetime.now() - st.session_state.get("last_refresh", datetime.now())).seconds
        if time_since_refresh > settings.AUTO_REFRESH:
            st.session_state.last_refresh = datetime.now()
            st.rerun()

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Usar ErrorHandler si está disponible
        try:
            ErrorHandler.handle_critical_error(e, "Error en la aplicación principal")
        except:
            # Fallback si ErrorHandler no funciona
            st.error(f"""
            ❌ **Error crítico en la aplicación**
            
            La aplicación encontró un error inesperado. Por favor:
            
            1. Recarga la página
            2. Verifica tu conexión a internet
            3. Contacta al administrador si el error persiste
            
            **Detalles técnicos:**
            ```python
            {str(e)[:200]}
            ```
            """)
        
        # Mostrar traceback completo en modo debug
        if st.session_state.get("debug_mode", False):
            import traceback
            st.code(traceback.format_exc())