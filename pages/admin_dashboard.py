"""
Dashboard del Administrador - Panel de control completo del sistema
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.auth import require_login, get_current_user, get_all_users
from utils.google_sheets import (
    get_alumnos_data, 
    get_cursos_data, 
    get_profesores_data,
    get_usuarios_data,
    get_finanzas_data
)
from components.headers import render_main_header, render_section_header, render_metric_card
from components.modals import (
    show_user_management_modal,
    show_course_management_modal,
    show_financial_report_modal
)

@require_login(role="admin")
def show_admin_dashboard():
    """
    Renderiza el dashboard de administración completo
    """
    # Obtener usuario actual
    user = get_current_user()
    
    # Configurar página
    st.set_page_config(
        page_title="Admin Dashboard - ASIS CIMMA",
        page_icon="👑",
        layout="wide"
    )
    
    # Header principal
    render_main_header(
        title="Panel de Administración",
        subtitle="Gestión completa del sistema ASIS CIMMA"
    )
    
    # Cargar todos los datos
    with st.spinner("Cargando datos del sistema..."):
        alumnos_df = get_alumnos_data()
        cursos_df = get_cursos_data()
        profesores_df = get_profesores_data()
        usuarios_df = get_usuarios_data()
        finanzas_df = get_finanzas_data()
    
    # Sidebar con navegación
    with st.sidebar:
        st.markdown("### 🎛️ Panel de Control")
        
        # Navegación por secciones
        seccion = st.radio(
            "Seleccionar módulo:",
            ["📊 Dashboard", "👥 Usuarios", "📚 Cursos", "💰 Finanzas", "⚙️ Configuración"]
        )
        
        st.markdown("---")
        st.markdown("### 🔍 Filtros Globales")
        
        # Filtro por fecha
        fecha_inicio = st.date_input(
            "Fecha inicio",
            datetime.now() - timedelta(days=30)
        )
        fecha_fin = st.date_input(
            "Fecha fin",
            datetime.now()
        )
        
        # Filtro por estado
        estado_sistema = st.selectbox(
            "Estado del sistema",
            ["Todos", "Activo", "Mantenimiento", "Pruebas"]
        )
        
        st.markdown("---")
        st.markdown(f"**Usuario:** {user.get('nombre', 'Admin')}")
        st.caption(f"Rol: {user.get('role', 'admin').upper()}")
    
    # Dashboard principal
    if seccion == "📊 Dashboard":
        mostrar_dashboard_principal(
            alumnos_df, cursos_df, profesores_df, usuarios_df, finanzas_df
        )
    
    elif seccion == "👥 Usuarios":
        mostrar_gestion_usuarios(usuarios_df, alumnos_df, profesores_df)
    
    elif seccion == "📚 Cursos":
        mostrar_gestion_cursos(cursos_df, alumnos_df, profesores_df)
    
    elif seccion == "💰 Finanzas":
        mostrar_gestion_finanzas(finanzas_df, alumnos_df, cursos_df)
    
    elif seccion == "⚙️ Configuración":
        mostrar_configuracion_sistema()

def mostrar_dashboard_principal(alumnos_df, cursos_df, profesores_df, usuarios_df, finanzas_df):
    """Muestra el dashboard principal con métricas y gráficos"""
    
    # Métricas principales en la parte superior
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_alumnos = len(alumnos_df)
        nuevos_hoy = len(alumnos_df[
            alumnos_df['fecha_inscripcion'].dt.date == datetime.now().date()
        ])
        render_metric_card(
            "👥 Total Alumnos",
            total_alumnos,
            icon="👥",
            delta=f"+{nuevos_hoy} hoy"
        )
    
    with col2:
        total_cursos = len(cursos_df)
        cursos_activos = len(cursos_df[cursos_df['estado'] == 'Activo'])
        render_metric_card(
            "📚 Cursos Activos",
            cursos_activos,
            icon="📚",
            delta=f"{cursos_activos}/{total_cursos}"
        )
    
    with col3:
        total_profesores = len(profesores_df)
        profesores_activos = len(profesores_df[profesores_df['estado'] == 'Activo'])
        render_metric_card(
            "👨‍🏫 Profesores",
            profesores_activos,
            icon="👨‍🏫",
            delta=f"{profesores_activos}/{total_profesores}"
        )
    
    with col4:
        if not finanzas_df.empty:
            ingresos_mes = finanzas_df[
                finanzas_df['fecha'].dt.month == datetime.now().month
            ]['monto'].sum()
            render_metric_card(
                "💰 Ingresos Mes",
                f"${ingresos_mes:,.0f}",
                icon="💰",
                delta="+12.5%"
            )
    
    # Gráficos principales
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        render_section_header("📈 Evolución de Matrículas")
        if not alumnos_df.empty:
            # Agrupar por mes
            alumnos_df['mes'] = alumnos_df['fecha_inscripcion'].dt.to_period('M')
            matricula_mensual = alumnos_df.groupby('mes').size().reset_index(name='count')
            matricula_mensual['mes'] = matricula_mensual['mes'].astype(str)
            
            fig = px.line(
                matricula_mensual,
                x='mes',
                y='count',
                markers=True,
                line_shape='spline'
            )
            fig.update_layout(
                xaxis_title="Mes",
                yaxis_title="Nuevos Alumnos",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col_chart2:
        render_section_header("🎯 Distribución por Curso")
        if not cursos_df.empty and not alumnos_df.empty:
            # Contar alumnos por curso
            alumnos_por_curso = alumnos_df['id_curso'].value_counts().reset_index()
            alumnos_por_curso.columns = ['id_curso', 'alumnos']
            
            # Merge con nombres de cursos
            distribucion = pd.merge(
                alumnos_por_curso,
                cursos_df[['id_curso', 'nombre_curso']],
                on='id_curso',
                how='left'
            )
            
            fig = px.pie(
                distribucion,
                values='alumnos',
                names='nombre_curso',
                hole=0.4
            )
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de actividad reciente
    st.markdown("---")
    render_section_header("📋 Actividad Reciente del Sistema")
    
    # Simular actividad (en producción vendría de un log)
    actividad_data = {
        'Fecha': [datetime.now() - timedelta(hours=i) for i in range(10)],
        'Usuario': ['Admin', 'Prof. García', 'Secretaria', 'Admin', 'Prof. López'] * 2,
        'Acción': [
            'Actualizó configuración',
            'Registró notas',
            'Envió comunicado',
            'Creó nuevo curso',
            'Actualizó perfil',
            'Generó reporte',
            'Matriculó alumno',
            'Actualizó finanzas',
            'Revisó asistencias',
            'Exportó datos'
        ],
        'Detalle': ['Sistema', 'Matemáticas 101', 'Padres 5°', 'Física Avanzada'] * 2 + ['General']
    }
    
    actividad_df = pd.DataFrame(actividad_data)
    st.dataframe(
        actividad_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha": st.column_config.DatetimeColumn(format="DD/MM/YY HH:mm"),
            "Acción": st.column_config.TextColumn(width="medium"),
            "Detalle": st.column_config.TextColumn(width="small")
        }
    )

def mostrar_gestion_usuarios(usuarios_df, alumnos_df, profesores_df):
    """Muestra la gestión de usuarios"""
    render_section_header("👥 Gestión de Usuarios")
    
    # Tabs para diferentes tipos de usuarios
    tab1, tab2, tab3, tab4 = st.tabs([
        "👑 Administradores", 
        "👨‍🏫 Profesores", 
        "👨‍🎓 Alumnos", 
        "➕ Nuevo Usuario"
    ])
    
    with tab1:
        admins_df = usuarios_df[usuarios_df['role'] == 'admin']
        if not admins_df.empty:
            st.dataframe(
                admins_df[['nombre', 'email', 'ultimo_login', 'estado']],
                use_container_width=True
            )
        else:
            st.info("No hay administradores registrados")
    
    with tab2:
        if not profesores_df.empty:
            # Merge con datos de usuarios
            profesores_completo = pd.merge(
                profesores_df,
                usuarios_df[['id', 'email', 'ultimo_login']],
                left_on='id_usuario',
                right_on='id',
                how='left'
            )
            
            st.dataframe(
                profesores_completo[['nombre', 'email', 'especialidad', 'estado', 'ultimo_login']],
                use_container_width=True
            )
        else:
            st.info("No hay profesores registrados")
    
    with tab3:
        if not alumnos_df.empty:
            st.dataframe(
                alumnos_df[['nombre', 'apellido', 'email', 'curso', 'estado', 'fecha_inscripcion']],
                use_container_width=True
            )
        else:
            st.info("No hay alumnos registrados")
    
    with tab4:
        st.write("### Crear Nuevo Usuario")
        
        col_type, col_role = st.columns(2)
        with col_type:
            tipo_usuario = st.selectbox(
                "Tipo de Usuario",
                ["Alumno", "Profesor", "Administrador", "Secretaria"]
            )
        
        with col_role:
            rol = st.selectbox(
                "Rol en el sistema",
                ["user", "profesor", "admin", "secretaria"]
            )
        
        # Formulario de creación
        with st.form("crear_usuario"):
            col_name, col_email = st.columns(2)
            with col_name:
                nombre = st.text_input("Nombre completo")
            
            with col_email:
                email = st.text_input("Email")
            
            col_pass, col_confirm = st.columns(2)
            with col_pass:
                password = st.text_input("Contraseña", type="password")
            
            with col_confirm:
                confirm_password = st.text_input("Confirmar contraseña", type="password")
            
            # Campos específicos por tipo
            if tipo_usuario == "Alumno":
                curso = st.selectbox("Curso", ["Matemáticas", "Ciencias", "Historia", "Literatura"])
            
            elif tipo_usuario == "Profesor":
                especialidad = st.text_input("Especialidad")
            
            crear = st.form_submit_button("✨ Crear Usuario")
            
            if crear:
                if password == confirm_password:
                    st.success(f"Usuario {tipo_usuario} creado exitosamente")
                    # Aquí iría la lógica para guardar en la base de datos
                else:
                    st.error("Las contraseñas no coinciden")

def mostrar_gestion_cursos(cursos_df, alumnos_df, profesores_df):
    """Muestra la gestión de cursos"""
    render_section_header("📚 Gestión de Cursos")
    
    col_stats, col_actions = st.columns([2, 1])
    
    with col_stats:
        # Estadísticas de cursos
        if not cursos_df.empty:
            st.metric("Cursos Totales", len(cursos_df))
            st.metric("Cursos Activos", len(cursos_df[cursos_df['estado'] == 'Activo']))
            st.metric("Capacidad Promedio", f"{cursos_df['capacidad_maxima'].mean():.0f} alumnos")
    
    with col_actions:
        st.button("➕ Crear Nuevo Curso", use_container_width=True)
        st.button("📊 Generar Reporte", use_container_width=True)
        st.button("🔄 Actualizar Todos", use_container_width=True)
    
    # Lista de cursos
    st.markdown("### Lista de Cursos")
    
    if not cursos_df.empty:
        for idx, curso in cursos_df.iterrows():
            with st.expander(f"📘 {curso['nombre_curso']} - {curso.get('codigo', 'N/A')}"):
                col_info, col_alumnos = st.columns(2)
                
                with col_info:
                    st.write(f"**Profesor:** {curso.get('nombre_profesor', 'No asignado')}")
                    st.write(f"**Horario:** {curso.get('horario', 'No definido')}")
                    st.write(f"**Aula:** {curso.get('aula', 'Virtual')}")
                    st.write(f"**Estado:** {curso['estado']}")
                
                with col_alumnos:
                    # Contar alumnos en este curso
                    if not alumnos_df.empty and 'id_curso' in alumnos_df.columns:
                        alumnos_curso = alumnos_df[alumnos_df['id_curso'] == curso['id_curso']]
                        st.metric("Alumnos Inscritos", len(alumnos_curso))
                        st.metric("Capacidad", f"{len(alumnos_curso)}/{curso.get('capacidad_maxima', 0)}")
                
                # Botones de acción
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    if st.button("✏️ Editar", key=f"edit_curso_{idx}"):
                        st.session_state['editar_curso_id'] = curso['id_curso']
                
                with col_btn2:
                    if st.button("👥 Ver Alumnos", key=f"view_alumnos_{idx}"):
                        st.session_state['ver_alumnos_curso'] = curso['id_curso']
                
                with col_btn3:
                    estado_btn = "✅ Activar" if curso['estado'] != 'Activo' else "⏸️ Pausar"
                    if st.button(estado_btn, key=f"toggle_curso_{idx}"):
                        # Cambiar estado
                        pass

def mostrar_gestion_finanzas(finanzas_df, alumnos_df, cursos_df):
    """Muestra la gestión financiera"""
    render_section_header("💰 Gestión Financiera")
    
    # Métricas financieras
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if not finanzas_df.empty:
            ingresos_totales = finanzas_df['monto'].sum()
            st.metric("Ingresos Totales", f"${ingresos_totales:,.0f}")
    
    with col2:
        if not finanzas_df.empty:
            ingresos_mes = finanzas_df[
                finanzas_df['fecha'].dt.month == datetime.now().month
            ]['monto'].sum()
            st.metric("Ingresos Mes Actual", f"${ingresos_mes:,.0f}")
    
    with col3:
        if not alumnos_df.empty:
            deudas = alumnos_df[alumnos_df['estado_pago'] == 'Pendiente']
            st.metric("Deudas Pendientes", len(deudas))
    
    with col4:
        if not finanzas_df.empty:
            promedio_mensual = finanzas_df.groupby(
                finanzas_df['fecha'].dt.to_period('M')
            )['monto'].sum().mean()
            st.metric("Promedio Mensual", f"${promedio_mensual:,.0f}")
    
    # Gráfico de ingresos
    st.markdown("### 📈 Evolución de Ingresos")
    
    if not finanzas_df.empty:
        # Agrupar por mes
        finanzas_df['mes'] = finanzas_df['fecha'].dt.to_period('M')
        ingresos_mensual = finanzas_df.groupby('mes')['monto'].sum().reset_index()
        ingresos_mensual['mes'] = ingresos_mensual['mes'].astype(str)
        
        fig = px.bar(
            ingresos_mensual,
            x='mes',
            y='monto',
            title="Ingresos Mensuales"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de transacciones
    st.markdown("### 💳 Últimas Transacciones")
    
    if not finanzas_df.empty:
        # Ordenar por fecha más reciente
        finanzas_recientes = finanzas_df.sort_values('fecha', ascending=False).head(10)
        
        st.dataframe(
            finanzas_recientes[['fecha', 'descripcion', 'monto', 'tipo', 'estado']],
            use_container_width=True,
            column_config={
                "fecha": st.column_config.DatetimeColumn(format="DD/MM/YY"),
                "monto": st.column_config.NumberColumn(
                    format="$%.0f",
                    help="Monto en pesos chilenos"
                )
            }
        )

def mostrar_configuracion_sistema():
    """Muestra la configuración del sistema"""
    render_section_header("⚙️ Configuración del Sistema")
    
    # Tabs de configuración
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔧 General", 
        "📧 Notificaciones", 
        "🔐 Seguridad", 
        "🔄 Integraciones"
    ])
    
    with tab1:
        st.write("### Configuración General")
        
        with st.form("config_general"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_institucion = st.text_input(
                    "Nombre de la Institución",
                    value="ASIS CIMMA"
                )
                zona_horaria = st.selectbox(
                    "Zona Horaria",
                    ["America/Santiago", "UTC", "America/New_York"]
                )
            
            with col2:
                idioma = st.selectbox(
                    "Idioma del Sistema",
                    ["Español", "English", "Português"]
                )
                formato_fecha = st.selectbox(
                    "Formato de Fecha",
                    ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]
                )
            
            guardar = st.form_submit_button("💾 Guardar Configuración")
            if guardar:
                st.success("Configuración guardada exitosamente")
    
    with tab2:
        st.write("### Configuración de Notificaciones")
        
        # Opciones de notificación
        notif_email = st.checkbox("📧 Notificaciones por Email", value=True)
        notif_push = st.checkbox("🔔 Notificaciones Push", value=False)
        notif_sms = st.checkbox("📱 Notificaciones por SMS", value=False)
        
        if notif_email:
            st.text_input("Email de notificaciones")
        
        st.text_area("Plantilla de notificaciones", height=150)
    
    with tab3:
        st.write("### Configuración de Seguridad")
        
        col_sec1, col_sec2 = st.columns(2)
        
        with col_sec1:
            st.checkbox("Requerir autenticación de dos factores", value=False)
            st.checkbox("Forzar cambio de contraseña cada 90 días", value=True)
            st.checkbox("Registrar todos los accesos al sistema", value=True)
        
        with col_sec2:
            st.number_input("Intentos fallidos permitidos", min_value=1, max_value=10, value=3)
            st.number_input("Tiempo de expiración de sesión (minutos)", min_value=5, max_value=240, value=30)
            st.selectbox("Política de contraseñas", ["Baja", "Media", "Alta"])
    
    with tab4:
        st.write("### Integraciones")
        
        st.checkbox("🔗 Google Sheets", value=True)
        st.checkbox("📧 Servicio de Email", value=True)
        st.checkbox("💳 Pasarela de Pagos", value=False)
        st.checkbox("📅 Calendario Google", value=False)

# Para ejecutar directamente (solo para pruebas)
if __name__ == "__main__":
    # Para pruebas, simular un usuario admin
    st.session_state['user'] = {
        'id': 1,
        'nombre': 'Administrador',
        'email': 'admin@asis-cimma.com',
        'role': 'admin'
    }
    show_admin_dashboard()