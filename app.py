import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import io

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
    .stProgress > div > div > div > div {
        background-color: #1A3B8F;
    }
    .metric-card {
        background: linear-gradient(135deg, #1A3B8F 0%, #2D4FA8 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
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
        
        [usuarios_sede]
        sp_user = "SAN PEDRO"
        sp_admin = "SAN PEDRO"
        chillan_user = "CHILLAN"
        pdv_user = "PEDRO DE VALDIVIA"
        
        [usuarios]
        admin = "admin123"
        profesor1 = "clave123"
        secretaria1 = "clave456"
        ```
        """)
        return
    
    # Inicializar estado de sesión
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = ""
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "sede" not in st.session_state:
        st.session_state.sede = ""
    
    # Autenticación
    if not st.session_state.get("authenticated", False):
        show_login_page(auth_manager)
    else:
        show_main_dashboard(auth_manager, sheets_manager, email_manager)
    
    # Footer
    display_footer()

def get_user_sede(username: str) -> str:
    """Determina la sede del usuario basado en su nombre de usuario"""
    try:
        # Intentar obtener desde secrets primero
        if "usuarios_sede" in st.secrets:
            for user_key, sede in st.secrets["usuarios_sede"].items():
                if user_key.lower() == username.lower():
                    return sede.upper()
    except:
        pass
    
    # Mapeo interno como fallback
    username_lower = username.lower().strip()
    
    sedes_mapping = {
        'sp': 'SAN PEDRO',
        'san pedro': 'SAN PEDRO',
        'chillan': 'CHILLAN',
        'chillán': 'CHILLAN',
        'pdv': 'PEDRO DE VALDIVIA',
        'valdivia': 'PEDRO DE VALDIVIA',
        'conce': 'CONCEPCIÓN',
        'concepción': 'CONCEPCIÓN',
        'admin': 'TODAS'
    }
    
    # Buscar coincidencias
    for key, sede in sedes_mapping.items():
        if key in username_lower:
            return sede
    
    # Buscar por patrones
    if 'sp' in username_lower:
        return 'SAN PEDRO'
    elif 'chillan' in username_lower or 'chillán' in username_lower:
        return 'CHILLAN'
    elif 'valdivia' in username_lower or 'pdv' in username_lower:
        return 'PEDRO DE VALDIVIA'
    elif 'conce' in username_lower or 'concepción' in username_lower:
        return 'CONCEPCIÓN'
    
    # Por defecto o para administradores
    return 'TODAS'

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
                           ["👨‍🏫 Profesor", "👩‍💼 Equipo Sede", "👑 Administrador"],
                           horizontal=True)
            
            username = st.text_input("Usuario", key="login_username")
            password = st.text_input("Contraseña", type="password", key="login_password")
            
            if st.button("🚀 Ingresar al Sistema", type="primary", use_container_width=True):
                if auth_manager.login(username, password, role):
                    st.session_state.authenticated = True
                    st.session_state.user = username
                    st.session_state.role = role
                    st.session_state.sede = get_user_sede(username)
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas o usuario no autorizado")
            
            # Info de acceso de prueba
            with st.expander("ℹ️ Información de acceso de prueba"):
                st.markdown("""
                **Usuarios de prueba:**
                - Profesor: `profesor1` / `clave123`
                - Equipo Sede SP: `sp_user` / `clave456`
                - Administrador: `admin` / `admin123`
                """)
            
            st.markdown("</div>", unsafe_allow_html=True)

def show_main_dashboard(auth_manager, sheets_manager, email_manager):
    """Mostrar dashboard principal"""
    # Sidebar con info de usuario
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1A3B8F/FFFFFF?text=CIMMA+LOGO", width=200)
        st.markdown(f"### 👤 {st.session_state.user}")
        st.markdown(f"**Rol:** {st.session_state.role}")
        
        if st.session_state.sede and st.session_state.sede != "TODAS":
            st.markdown(f"**🏫 Sede:** {st.session_state.sede}")
        
        st.markdown("---")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            auth_manager.logout()
            st.rerun()
        
        # Información del sistema
        st.markdown("---")
        st.markdown("**📊 Estadísticas rápidas:**")
        
        try:
            if "Equipo Sede" in st.session_state.role:
                cursos_sede = sheets_manager.load_courses_by_sede(st.session_state.sede)
                if cursos_sede:
                    total_estudiantes = sum(len(c["estudiantes"]) for c in cursos_sede.values())
                    total_cursos = len(cursos_sede)
                    st.metric("📚 Cursos", total_cursos)
                    st.metric("👥 Estudiantes", total_estudiantes)
        except:
            pass
    
    # Menú principal
    if "Equipo Sede" in st.session_state.role:
        st.markdown(f'<h1 class="main-header">🏫 Sede {st.session_state.sede}</h1>', unsafe_allow_html=True)
    else:
        st.markdown(f'<h1 class="main-header">Bienvenido, {st.session_state.user}!</h1>', unsafe_allow_html=True)
    
    # Contenido según rol
    if "Profesor" in st.session_state.role:
        show_profesor_dashboard(sheets_manager, email_manager)
    elif "Equipo Sede" in st.session_state.role:
        show_secretaria_dashboard(sheets_manager, email_manager)
    elif "Administrador" in st.session_state.role:
        show_admin_dashboard(sheets_manager, email_manager)
    else:
        st.warning("⚠️ Rol no reconocido. Contacte al administrador.")

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
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📅 Fechas", len(curso_data["fechas"]))
            with col2:
                st.metric("👥 Estudiantes", len(curso_data["estudiantes"]))
            with col3:
                st.metric("🏫 Sede", curso_data.get("sede", "No especificada"))
            with col4:
                st.metric("👨‍🏫 Profesor", curso_data.get("profesor", ""))
            
            # Registrar asistencia
            fecha = st.selectbox("Fecha de clase:", curso_data["fechas"])
            
            st.subheader("Marcar asistencia:")
            
            asistencia = {}
            for estudiante in curso_data["estudiantes"]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{estudiante}**")
                with col2:
                    presente = st.checkbox("Presente", value=True, key=f"check_{estudiante}_{fecha}")
                    asistencia[estudiante] = presente
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar Asistencia", type="primary", use_container_width=True):
                    if sheets_manager.save_attendance(curso, fecha, asistencia, st.session_state.user):
                        st.success("✅ Asistencia guardada correctamente")
                        
                        # Opción de enviar emails
                        if st.checkbox("📧 Enviar notificaciones a apoderados"):
                            with st.spinner("Enviando emails..."):
                                resultados = email_manager.send_attendance_emails(curso, fecha, asistencia)
                                if resultados["sent"] > 0:
                                    st.success(f"✅ {resultados['sent']} emails enviados")
                                if resultados["failed"] > 0:
                                    st.warning(f"⚠️ {resultados['failed']} emails fallaron")
                    else:
                        st.error("❌ Error al guardar asistencia")
            
            with col2:
                if st.button("🔄 Reiniciar Selección", use_container_width=True):
                    st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.info("ℹ️ Si el error persiste, contacte al administrador del sistema.")

def show_secretaria_dashboard(sheets_manager, email_manager):
    """Dashboard para Equipo Sede"""
    user_sede = st.session_state.sede
    
    if user_sede == "TODAS":
        st.warning("⚠️ Usuario de Equipo Sede sin sede asignada. Contacte al administrador.")
        return
    
    st.header(f"👩‍💼 Panel de Equipo Sede - {user_sede}")
    
    tab1, tab2, tab3 = st.tabs(["📋 Cursos de Sede", "📊 Reportes", "📧 Comunicaciones Masivas"])
    
    with tab1:
        st.subheader(f"🏫 Cursos de Sede: {user_sede}")
        
        try:
            # Cargar cursos de la sede
            with st.spinner("Cargando cursos..."):
                cursos_sede = sheets_manager.load_courses_by_sede(user_sede)
            
            if not cursos_sede:
                st.info(f"📚 No se encontraron cursos para la sede {user_sede}")
                return
            
            # Selector de curso
            curso_seleccionado = st.selectbox(
                "Selecciona un curso para ver detalles:", 
                list(cursos_sede.keys()),
                key="curso_sede_select"
            )
            
            if curso_seleccionado:
                curso_data = cursos_sede[curso_seleccionado]
                
                # Mostrar información del curso
                with st.expander("📊 Información del Curso", expanded=True):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("👥 Estudiantes", len(curso_data.get("estudiantes", [])))
                    with col2:
                        st.metric("📅 Clases", len(curso_data.get("fechas", [])))
                    with col3:
                        profesor = curso_data.get("profesor", "No asignado")
                        st.metric("👨‍🏫 Profesor", profesor)
                    with col4:
                        asignatura = curso_data.get("asignatura", "No especificada")
                        st.metric("📚 Asignatura", asignatura)
                
                # Mostrar asistencia detallada
                st.subheader("📝 Asistencia por Estudiante")
                
                # Opciones de visualización
                vista = st.radio(
                    "Vista:",
                    ["📋 Lista Completa", "📊 Resumen Estadístico", "⚠️ Baja Asistencia (<70%)"],
                    horizontal=True
                )
                
                if curso_data.get("estudiantes"):
                    data = []
                    
                    for estudiante in curso_data["estudiantes"]:
                        # Calcular estadísticas de asistencia
                        asistencias_est = curso_data.get("asistencias", {}).get(estudiante, {})
                        total_clases = len(curso_data["fechas"])
                        presentes = sum(1 for estado in asistencias_est.values() if estado)
                        ausentes = total_clases - presentes
                        porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0
                        
                        data.append({
                            "Estudiante": estudiante,
                            "Presente": presentes,
                            "Ausente": ausentes,
                            "Total Clases": total_clases,
                            "Asistencia %": porcentaje,
                            "Estado": "✅ Adecuado" if porcentaje >= 70 else "⚠️ Bajo"
                        })
                    
                    df = pd.DataFrame(data)
                    
                    if vista == "📊 Resumen Estadístico":
                        # Mostrar métricas generales
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Asistencia Promedio", f"{df['Asistencia %'].mean():.1f}%")
                        with col2:
                            st.metric("Estudiantes Críticos", len(df[df['Asistencia %'] < 70]))
                        with col3:
                            st.metric("Mejor Asistencia", f"{df['Asistencia %'].max():.1f}%")
                        
                        # Gráfico de distribución
                        st.subheader("📈 Distribución de Asistencia")
                        chart_data = df[['Estudiante', 'Asistencia %']].set_index('Estudiante')
                        st.bar_chart(chart_data, height=300)
                        
                    elif vista == "⚠️ Baja Asistencia (<70%)":
                        df_filtrado = df[df['Asistencia %'] < 70]
                        if len(df_filtrado) > 0:
                            st.warning(f"⚠️ {len(df_filtrado)} estudiantes con baja asistencia")
                            st.dataframe(df_filtrado.sort_values('Asistencia %'), 
                                       use_container_width=True, 
                                       height=400,
                                       column_config={
                                           "Asistencia %": st.column_config.ProgressColumn(
                                               "Asistencia %",
                                               format="%.1f%%",
                                               min_value=0,
                                               max_value=100,
                                           )
                                       })
                        else:
                            st.success("✅ Todos los estudiantes tienen asistencia adecuada")
                    
                    else:  # Lista Completa
                        st.dataframe(df.sort_values('Estudiante'), 
                                   use_container_width=True, 
                                   height=400,
                                   column_config={
                                       "Asistencia %": st.column_config.ProgressColumn(
                                           "Asistencia %",
                                           format="%.1f%%",
                                           min_value=0,
                                           max_value=100,
                                       )
                                   })
                    
                    # Opciones de exportación
                    st.subheader("📥 Exportar Datos")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📄 Exportar a CSV", use_container_width=True):
                            csv = df.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Descargar CSV",
                                data=csv,
                                file_name=f"asistencia_{curso_seleccionado}_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    
                    with col2:
                        if st.button("📊 Exportar a Excel", use_container_width=True):
                            excel_data = export_to_excel(df, curso_seleccionado)
                            st.download_button(
                                label="Descargar Excel",
                                data=excel_data,
                                file_name=f"asistencia_{curso_seleccionado}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
        
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("ℹ️ Verifique que la hoja de clases tenga el formato correcto.")
    
    with tab2:
        st.subheader("📊 Reportes de Asistencia")
        
        col1, col2 = st.columns(2)
        with col1:
            reporte_tipo = st.selectbox(
                "Tipo de Reporte",
                ["Resumen General", "Asistencia Detallada", "Estudiantes Críticos (<70%)", "Top 10 Mejor Asistencia"]
            )
        
        with col2:
            periodo = st.selectbox(
                "Período",
                ["Todo el Año", "Último Mes", "Última Semana"]
            )
        
        if st.button("📄 Generar Reporte", type="primary", use_container_width=True):
            with st.spinner("Generando reporte..."):
                try:
                    if reporte_tipo == "Resumen General":
                        reporte = generar_reporte_general(user_sede, sheets_manager)
                        titulo = "📋 Resumen General de Sede"
                    elif reporte_tipo == "Estudiantes Críticos (<70%)":
                        reporte_data = sheets_manager.get_low_attendance_students(user_sede, threshold=70)
                        reporte = pd.DataFrame(reporte_data) if reporte_data else []
                        titulo = "⚠️ Estudiantes con Baja Asistencia"
                    elif reporte_tipo == "Top 10 Mejor Asistencia":
                        reporte = generar_top_asistencia(user_sede, sheets_manager)
                        titulo = "🏆 Top 10 Mejor Asistencia"
                    else:
                        reporte = generar_reporte_detallado(user_sede, sheets_manager)
                        titulo = "📝 Asistencia Detallada"
                    
                    if len(reporte) > 0:
                        st.success(f"✅ Reporte generado: {len(reporte)} registros")
                        st.subheader(titulo)
                        
                        if isinstance(reporte, pd.DataFrame):
                            st.dataframe(reporte, use_container_width=True, height=500)
                        else:
                            df_reporte = pd.DataFrame(reporte)
                            st.dataframe(df_reporte, use_container_width=True, height=500)
                        
                        # Opción de exportación
                        if st.button("📥 Exportar Reporte", use_container_width=True):
                            csv = pd.DataFrame(reporte).to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="Descargar Reporte",
                                data=csv,
                                file_name=f"reporte_{user_sede}_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    else:
                        st.warning("⚠️ No hay datos para el reporte solicitado")
                        
                except Exception as e:
                    st.error(f"❌ Error generando reporte: {e}")
    
    with tab3:
        st.subheader("📧 Comunicaciones Masivas")
        st.info("Envío de correos a apoderados de la sede. Personalice el mensaje según necesidad.")
        
        # Paso 1: Seleccionar destinatarios
        st.markdown("### Paso 1: Seleccionar Destinatarios")
        
        opcion_envio = st.radio(
            "🔘 Destinatarios:",
            ["📋 Todos los cursos de la sede", 
             "🎯 Curso específico", 
             "⚠️ Solo estudiantes con baja asistencia (<70%)",
             "✅ Solo estudiantes con buena asistencia (≥85%)"],
            key="opcion_envio"
        )
        
        if opcion_envio == "🎯 Curso específico":
            cursos_sede = sheets_manager.load_courses_by_sede(user_sede)
            if cursos_sede:
                curso_especifico = st.selectbox("Seleccionar curso:", list(cursos_sede.keys()))
            else:
                st.warning("No hay cursos disponibles")
                return
        
        # Paso 2: Personalizar mensaje
        st.markdown("### Paso 2: Personalizar Mensaje")
        
        asunto = st.text_input("Asunto del email:", 
                               value=f"Información de Asistencia - Sede {user_sede}",
                               key="email_asunto")
        
        plantilla_base = f"""Estimado/a apoderado/a,

Le informamos sobre la situación de asistencia de {{estudiante}} en el curso {{curso}} de la sede {user_sede}.

**Resumen de asistencia:**
- Porcentaje de asistencia: {{porcentaje}}%
- Total de clases: {{total_clases}}
- Clases presentes: {{presentes}}
- Clases ausentes: {{ausentes}}

**Recomendaciones:**
{{recomendacion}}

Le recordamos la importancia de la asistencia regular para el éxito académico.

Quedamos a su disposición para cualquier consulta.

Saludos cordiales,
Equipo Sede {user_sede}
Preuniversitario CIMMA
📞 Contacto: +56 9 XXXX XXXX
✉️ Email: contacto@cimma.cl
"""
        
        mensaje = st.text_area("Contenido del email (use {variable} para personalizar):", 
                               value=plantilla_base, 
                               height=300,
                               key="email_contenido")
        
        # Variables disponibles
        with st.expander("📌 Variables disponibles para personalización"):
            st.markdown("""
            **Variables que se reemplazarán automáticamente:**
            - `{estudiante}`: Nombre del estudiante
            - `{curso}`: Nombre del curso
            - `{porcentaje}`: Porcentaje de asistencia
            - `{total_clases}`: Total de clases programadas
            - `{presentes}`: Clases presentes
            - `{ausentes}`: Clases ausentes
            - `{sede}`: Nombre de la sede
            - `{recomendacion}`: Recomendación según asistencia
            """)
        
        # Paso 3: Previsualizar
        st.markdown("### Paso 3: Previsualizar")
        
        if st.button("👁️ Ver Previsualización", key="btn_preview"):
            with st.expander("📧 Previsualización del Email", expanded=True):
                st.markdown("**Asunto:** " + asunto)
                st.markdown("**Contenido:**")
                contenido_preview = mensaje.replace("{estudiante}", "Juan Pérez") \
                                          .replace("{curso}", "Matemáticas Avanzadas") \
                                          .replace("{porcentaje}", "85.5") \
                                          .replace("{total_clases}", "20") \
                                          .replace("{presentes}", "17") \
                                          .replace("{ausentes}", "3") \
                                          .replace("{sede}", user_sede) \
                                          .replace("{recomendacion}", "¡Excelente asistencia! Continúe así.")
                st.markdown(contenido_preview)
        
        # Paso 4: Confirmar y enviar
        st.markdown("### Paso 4: Confirmar y Enviar")
        
        confirmar = st.checkbox("✅ Confirmo que deseo enviar estos emails", 
                                key="confirmar_envio")
        
        if confirmar and st.button("📤 Iniciar Envío Masivo", type="primary", use_container_width=True):
            with st.spinner("Preparando envío masivo..."):
                try:
                    # Obtener destinatarios según opción
                    destinatarios = []
                    
                    if opcion_envio == "📋 Todos los cursos de la sede":
                        destinatarios = sheets_manager.get_all_emails_by_sede(user_sede)
                    
                    elif opcion_envio == "🎯 Curso específico":
                        todos = sheets_manager.get_all_emails_by_sede(user_sede)
                        destinatarios = [d for d in todos if d.get("curso") == curso_especifico]
                    
                    elif opcion_envio == "⚠️ Solo estudiantes con baja asistencia (<70%)":
                        estudiantes_bajos = sheets_manager.get_low_attendance_students(user_sede, threshold=70)
                        destinatarios = [
                            {
                                "estudiante": d["estudiante"],
                                "email": d["email"],
                                "curso": d["curso"],
                                "porcentaje": d["porcentaje"],
                                "total_clases": d["total_clases"],
                                "presentes": d["presentes"],
                                "ausentes": d["total_clases"] - d["presentes"],
                                "sede": user_sede,
                                "recomendacion": "Le recomendamos mejorar la asistencia para un mejor rendimiento académico."
                            }
                            for d in estudiantes_bajos if d.get("email") and d["email"] != "No registrado"
                        ]
                    
                    else:  # Buena asistencia
                        # Implementar lógica similar para buena asistencia
                        pass
                    
                    if not destinatarios:
                        st.warning("⚠️ No se encontraron destinatarios con emails registrados")
                        return
                    
                    st.info(f"📧 Se enviarán {len(destinatarios)} emails")
                    
                    # Agregar recomendaciones personalizadas
                    for d in destinatarios:
                        porcentaje = d.get("porcentaje", 0)
                        if porcentaje < 70:
                            d["recomendacion"] = "Le recomendamos mejorar la asistencia para un mejor rendimiento académico."
                        elif porcentaje < 85:
                            d["recomendacion"] = "Su asistencia es buena, pero puede mejorar."
                        else:
                            d["recomendacion"] = "¡Excelente asistencia! Continúe así."
                    
                    # Realizar envío
                    resultados = email_manager.send_bulk_emails(
                        destinatarios=destinatarios,
                        subject=asunto,
                        body_template=mensaje,
                        is_html=False
                    )
                    
                    # Mostrar resultados
                    st.success("✅ Envío completado")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📤 Enviados", resultados.get("sent", 0))
                    with col2:
                        st.metric("❌ Fallidos", resultados.get("failed", 0))
                    with col3:
                        st.metric("📊 Total", resultados.get("total", 0))
                    
                    # Mostrar detalles si hay fallos
                    if resultados.get("failed", 0) > 0:
                        with st.expander("📋 Ver detalles de fallos"):
                            for detalle in resultados.get("details", []):
                                if "❌" in detalle.get("status", "") or "Error" in detalle.get("status", ""):
                                    st.write(f"**{detalle.get('estudiante', 'N/A')}**: {detalle.get('status', '')}")
                
                except Exception as e:
                    st.error(f"❌ Error en envío masivo: {str(e)}")
                    st.info("ℹ️ Verifique la configuración de email en secrets.toml")

def show_admin_dashboard(sheets_manager, email_manager):
    """Dashboard para administradores"""
    st.header("👑 Panel de Administración")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👥 Usuarios", "⚙️ Configuración", "🔧 Sistema"])
    
    with tab1:
        st.subheader("Estadísticas del Sistema")
        
        try:
            # Cargar todos los cursos
            all_courses = sheets_manager.load_courses()
            
            if all_courses:
                # Calcular métricas generales
                total_cursos = len(all_courses)
                total_estudiantes = sum(len(c["estudiantes"]) for c in all_courses.values())
                
                # Contar por sede
                sedes = {}
                for curso_data in all_courses.values():
                    sede = curso_data.get("sede", "Sin sede")
                    sedes[sede] = sedes.get(sede, 0) + 1
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📚 Total Cursos", total_cursos)
                with col2:
                    st.metric("👥 Total Estudiantes", total_estudiantes)
                with col3:
                    st.metric("🏫 Total Sedes", len(sedes))
                
                # Mostrar distribución por sede
                st.subheader("📊 Distribución por Sede")
                df_sedes = pd.DataFrame(list(sedes.items()), columns=["Sede", "Cursos"])
                st.bar_chart(df_sedes.set_index("Sede"))
                
                # Lista de cursos
                with st.expander("📋 Ver todos los cursos"):
                    cursos_lista = []
                    for nombre, datos in all_courses.items():
                        cursos_lista.append({
                            "Curso": nombre,
                            "Sede": datos.get("sede", ""),
                            "Profesor": datos.get("profesor", ""),
                            "Estudiantes": len(datos.get("estudiantes", [])),
                            "Clases": len(datos.get("fechas", []))
                        })
                    
                    df_cursos = pd.DataFrame(cursos_lista)
                    st.dataframe(df_cursos, use_container_width=True, height=400)
            
        except Exception as e:
            st.error(f"❌ Error cargando estadísticas: {e}")
    
    with tab2:
        st.subheader("Gestión de Usuarios")
        st.info("Funcionalidad en desarrollo...")
        
        # Aquí iría la lógica CRUD de usuarios
        st.write("Próximamente: Crear, editar y eliminar usuarios")
    
    with tab3:
        st.subheader("Configuración del Sistema")
        
        st.markdown("### Configuración de Google Sheets")
        sheet_ids = sheets_manager.get_sheet_ids()
        
        if sheet_ids:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📊 Hoja Asistencia", "Configurada" if sheet_ids.get("asistencia") else "No configurada")
            with col2:
                st.metric("📚 Hoja Clases", "Configurada" if sheet_ids.get("clases") else "No configurada")
        
        st.markdown("### Configuración de Email")
        if email_manager.smtp_config:
            st.success("✅ Configuración de email activa")
            st.code(f"Servidor: {email_manager.smtp_config.get('server', 'N/A')}")
        else:
            st.error("❌ Configuración de email no disponible")
    
    with tab4:
        st.subheader("Estado del Sistema")
        
        st.markdown("### Verificación de Componentes")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            try:
                sheets_manager._init_client()
                st.success("✅ Google Sheets")
            except:
                st.error("❌ Google Sheets")
        
        with col2:
            if email_manager.smtp_config:
                st.success("✅ Email Service")
            else:
                st.error("❌ Email Service")
        
        with col3:
            st.info("🔄 Sistema Principal")
        
        st.markdown("### Logs del Sistema")
        st.code(f"""
        Usuario actual: {st.session_state.user}
        Rol: {st.session_state.role}
        Sede: {st.session_state.sede}
        Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)

def export_to_excel(df, curso_nombre):
    """Exportar DataFrame a Excel en memoria"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=curso_nombre[:31], index=False)
    
    output.seek(0)
    return output.read()

def generar_reporte_general(sede_nombre, sheets_manager):
    """Genera un reporte general de la sede"""
    try:
        cursos = sheets_manager.load_courses_by_sede(sede_nombre)
        
        if not cursos:
            return []
        
        reporte = []
        for curso_nombre, curso_data in cursos.items():
            total_estudiantes = len(curso_data.get("estudiantes", []))
            total_clases = len(curso_data.get("fechas", []))
            
            # Calcular asistencia promedio
            if total_estudiantes > 0 and total_clases > 0:
                asistencias = curso_data.get("asistencias", {})
                if asistencias:
                    total_asistencias = sum(
                        sum(1 for estado in est.values() if estado)
                        for est in asistencias.values()
                    )
                    porcentaje_promedio = (total_asistencias / (total_estudiantes * total_clases)) * 100
                else:
                    porcentaje_promedio = 0
            else:
                porcentaje_promedio = 0
            
            # Contar estudiantes con baja asistencia
            baja_asistencia = 0
            if curso_data.get("estudiantes"):
                for estudiante in curso_data["estudiantes"]:
                    asistencias_est = curso_data.get("asistencias", {}).get(estudiante, {})
                    presentes = sum(1 for estado in asistencias_est.values() if estado)
                    porcentaje_est = (presentes / total_clases * 100) if total_clases > 0 else 0
                    if porcentaje_est < 70:
                        baja_asistencia += 1
            
            reporte.append({
                "Curso": curso_nombre,
                "Estudiantes": total_estudiantes,
                "Clases Programadas": total_clases,
                "Asistencia Promedio": f"{porcentaje_promedio:.1f}%",
                "Baja Asistencia (<70%)": baja_asistencia,
                "Profesor": curso_data.get("profesor", "N/A"),
                "Asignatura": curso_data.get("asignatura", "N/A")
            })
        
        return reporte
        
    except Exception as e:
        st.error(f"Error generando reporte: {e}")
        return []

def generar_reporte_detallado(sede_nombre, sheets_manager):
    """Genera un reporte detallado de asistencia"""
    try:
        cursos = sheets_manager.load_courses_by_sede(sede_nombre)
        
        if not cursos:
            return []
        
        reporte = []
        for curso_nombre, curso_data in cursos.items():
            for estudiante in curso_data.get("estudiantes", []):
                asistencias_est = curso_data.get("asistencias", {}).get(estudiante, {})
                total_clases = len(curso_data.get("fechas", []))
                presentes = sum(1 for estado in asistencias_est.values() if estado)
                ausentes = total_clases - presentes
                porcentaje = (presentes / total_clases * 100) if total_clases > 0 else 0
                
                reporte.append({
                    "Curso": curso_nombre,
                    "Estudiante": estudiante,
                    "Clases Totales": total_clases,
                    "Presente": presentes,
                    "Ausente": ausentes,
                    "Asistencia %": porcentaje,
                    "Estado": "✅ Adecuado" if porcentaje >= 70 else "⚠️ Bajo" if porcentaje >= 50 else "❌ Crítico"
                })
        
        return reporte
        
    except Exception as e:
        st.error(f"Error generando reporte detallado: {e}")
        return []

def generar_top_asistencia(sede_nombre, sheets_manager):
    """Genera top 10 mejor asistencia de la sede"""
    try:
        reporte_detallado = generar_reporte_detallado(sede_nombre, sheets_manager)
        
        if not reporte_detallado:
            return []
        
        # Convertir a DataFrame para ordenar
        df = pd.DataFrame(reporte_detallado)
        
        # Ordenar por porcentaje de asistencia (descendente)
        df_sorted = df.sort_values("Asistencia %", ascending=False)
        
        # Tomar top 10
        top_10 = df_sorted.head(10)
        
        # Formatear resultado
        resultado = []
        for idx, row in top_10.iterrows():
            resultado.append({
                "Posición": idx + 1,
                "Estudiante": row["Estudiante"],
                "Curso": row["Curso"],
                "Asistencia %": f"{row['Asistencia %']:.1f}%",
                "Presente/Ausente": f"{row['Presente']}/{row['Ausente']}",
                "Estado": row["Estado"]
            })
        
        return resultado
        
    except Exception as e:
        st.error(f"Error generando top asistencia: {e}")
        return []

if __name__ == "__main__":
    main()