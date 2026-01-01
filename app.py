import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Agregar la carpeta utils al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

# Importar módulos propios
try:
    from utils.google_sheets import GoogleSheetsManager
    from utils.email_sender import EmailManager
    from utils.auth import AuthManager
    from utils.helpers import setup_page, display_footer
except ImportError as e:
    st.error(f"❌ Error importando módulos: {e}")
    st.info("💡 Asegúrate de que la carpeta 'utils' existe y tiene los archivos correctos")

# Configuración de página
def main():
    # Configurar página
    st.set_page_config(
        page_title="Sistema de Asistencia CIMMA",
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializar managers
    auth_manager = AuthManager()
    sheets_manager = GoogleSheetsManager()
    email_manager = EmailManager()
    
    # CSS personalizado
    st.markdown("""
    <style>
    .main-header {
        color: #1A3B8F;
        font-size: 2.5rem;
        text-align: center;
        margin-bottom: 1rem;
    }
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Verificar si los secrets están configurados
    if not auth_manager.check_secrets():
        st.error("""
        ❌ **Secrets no configurados**
        
        Por favor, configura los secrets en Streamlit Cloud:
        
        1. Ve a [share.streamlit.io](https://share.streamlit.io)
        2. Selecciona tu app
        3. Haz clic en "Settings" (engranaje)
        4. Ve a "Secrets"
        5. Pega el contenido de secrets.toml
        
        **Estructura requerida:**
        ```toml
        [google]
        credentials = '{"type": "service_account", ...}'
        asistencia_sheet_id = "tu_id_aquí"
        clases_sheet_id = "tu_id_aquí"
        
        [EMAIL]
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "tu_email@gmail.com"
        sender_password = "tu_password"
        
        [usuarios]
        admin = "admin123"
        profesor1 = "clave123"
        secretaria1 = "clave456"
        ```
        """)
        return
    
    # Autenticación
    if not st.session_state.get("authenticated", False):
        show_login_page(auth_manager)
    else:
        show_main_dashboard(auth_manager, sheets_manager, email_manager)
    
    # Footer
    display_footer()

def show_login_page(auth_manager):
    """Mostrar página de login"""
    st.markdown('<h1 class="main-header">🎓 Sistema de Asistencia CIMMA</h1>', unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="card">
                <h2 style="text-align: center; color: #1A3B8F;">🔐 Iniciar Sesión</h2>
            """, unsafe_allow_html=True)
            
            role = st.radio("Selecciona tu rol:", 
                           ["👨‍🏫 Profesor", "👩‍💼 Secretaria", "👑 Administrador"],
                           horizontal=True)
            
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("🚀 Ingresar al Sistema", type="primary", use_container_width=True):
                if auth_manager.login(username, password, role):
                    st.session_state.authenticated = True
                    st.session_state.user = username
                    st.session_state.role = role
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
            
            st.markdown("</div>", unsafe_allow_html=True)

def show_main_dashboard(auth_manager, sheets_manager, email_manager):
    """Mostrar dashboard principal"""
    # Sidebar con info de usuario
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1A3B8F/FFFFFF?text=CIMMA+LOGO", width=200)
        st.markdown(f"### 👤 {st.session_state.user}")
        st.markdown(f"**Rol:** {st.session_state.role}")
        
        if st.button("🚪 Cerrar Sesión"):
            auth_manager.logout()
            st.rerun()
    
    # Menú principal
    st.markdown(f'<h1 class="main-header">Bienvenido, {st.session_state.user}!</h1>', unsafe_allow_html=True)
    
    # Contenido según rol
    if "Profesor" in st.session_state.role:
        show_profesor_dashboard(sheets_manager, email_manager)
    elif "Secretaria" in st.session_state.role:
        show_secretaria_dashboard(sheets_manager, email_manager)
    else:
        show_admin_dashboard(sheets_manager, email_manager)

def show_profesor_dashboard(sheets_manager, email_manager):
    """Dashboard para profesores"""
    st.header("📋 Registrar Asistencia")
    
    try:
        # Cargar cursos del profesor
        cursos = sheets_manager.load_courses_for_teacher(st.session_state.user)
        
        if not cursos:
            st.info("📚 No tienes cursos asignados")
            return
        
        curso = st.selectbox("Selecciona tu curso:", list(cursos.keys()))
        
        if curso:
            curso_data = cursos[curso]
            
            # Mostrar info del curso
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📅 Fechas", len(curso_data["fechas"]))
            with col2:
                st.metric("👥 Estudiantes", len(curso_data["estudiantes"]))
            with col3:
                st.metric("🏫 Sede", curso_data.get("sede", "No especificada"))
            
            # Registrar asistencia
            fecha = st.selectbox("Fecha de clase:", curso_data["fechas"])
            
            st.subheader("Marcar asistencia:")
            
            asistencia = {}
            for estudiante in curso_data["estudiantes"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{estudiante}**")
                with col2:
                    presente = st.checkbox("Presente", value=True, key=estudiante)
                    asistencia[estudiante] = presente
            
            if st.button("💾 Guardar Asistencia", type="primary"):
                if sheets_manager.save_attendance(curso, fecha, asistencia, st.session_state.user):
                    st.success("✅ Asistencia guardada")
                    
                    # Opción de enviar emails
                    if st.checkbox("📧 Enviar notificaciones a apoderados"):
                        email_manager.send_attendance_emails(curso, fecha, asistencia)
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

def show_secretaria_dashboard(sheets_manager, email_manager):
    """Dashboard para secretarias"""
    st.header("👩‍💼 Panel de Secretaría")
    
    tab1, tab2, tab3 = st.tabs(["📋 Registro Rápido", "📊 Reportes", "📧 Comunicaciones"])
    
    with tab1:
        st.subheader("Registro Rápido de Asistencia")
        # Similar a profesor pero con acceso a todos los cursos
    
    with tab2:
        st.subheader("Generar Reportes")
        # Funcionalidades de reportes
    
    with tab3:
        st.subheader("Envío Masivo de Emails")
        # Funcionalidades de comunicación

def show_admin_dashboard(sheets_manager, email_manager):
    """Dashboard para administradores"""
    st.header("👑 Panel de Administración")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👥 Usuarios", "⚙️ Configuración", "🔧 Sistema"])
    
    with tab1:
        st.subheader("Estadísticas del Sistema")
        # Métricas generales
    
    with tab2:
        st.subheader("Gestión de Usuarios")
        # CRUD de usuarios
    
    with tab3:
        st.subheader("Configuración del Sistema")
        # Configuración general
    
    with tab4:
        st.subheader("Estado del Sistema")
        # Logs y monitoreo

if __name__ == "__main__":
    main()