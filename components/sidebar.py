# components/sidebar.py
import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional
from config import constants
from utils.google_sheets import GoogleSheetsManager

def render_sidebar(auth_manager, sheets_manager: Optional[GoogleSheetsManager] = None):
    """
    Renderiza la barra lateral con información del usuario y controles.
    
    Args:
        auth_manager: Manager de autenticación
        sheets_manager: Manager de Google Sheets (opcional para estadísticas)
    """
    with st.sidebar:
        # Logo de la aplicación
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color: #1A3B8F;">🔄 CIMMA</h2>
            <p style="color: #666; font-size: 0.9rem;">Sistema de Asistencia</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Información del usuario
        render_user_info()
        
        st.markdown("---")
        
        # Estadísticas rápidas (solo para Equipo Sede)
        if "Equipo Sede" in st.session_state.role and sheets_manager:
            render_quick_stats(sheets_manager)
            st.markdown("---")
        
        # Navegación principal
        st.markdown("### 🧭 Navegación")
        
        # Botón para cerrar sesión
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            auth_manager.logout()
            st.rerun()
        
        # Información del sistema
        st.markdown("---")
        st.markdown("### ℹ️ Sistema")
        
        # Mostrar versión si está disponible
        if "version" in st.secrets.get("APP_SETTINGS", {}):
            st.caption(f"Versión: {st.secrets['APP_SETTINGS']['version']}")
        
        # Mostrar última actualización
        st.caption(f"Última actividad: {st.session_state.get('last_activity', datetime.now()).strftime('%H:%M:%S')}")
        
        # Botón de ayuda
        if st.button("❓ Ayuda", use_container_width=True):
            st.session_state.show_help = True
            st.rerun()

def render_user_info():
    """
    Renderiza la información del usuario en el sidebar.
    """
    # Icono según rol
    role_icon = constants.ICONS.get(
        st.session_state.get("role_type", "").lower(),
        "👤"
    )
    
    # Información del usuario
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1A3B8F 0%, #2D4FA8 100%); 
                color: white; 
                padding: 1rem; 
                border-radius: 10px; 
                margin-bottom: 1rem;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <div style="font-size: 1.5rem;">{role_icon}</div>
            <div>
                <h4 style="margin: 0;">{st.session_state.get('user', 'Usuario')}</h4>
                <p style="margin: 0; font-size: 0.8rem; opacity: 0.9;">{st.session_state.get('role', 'Sin rol')}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Información de sede si existe
    sede = st.session_state.get("sede", "")
    if sede and sede != "TODAS":
        st.markdown(f"""
        <div style="background: #f0f2f6; 
                    padding: 0.5rem; 
                    border-radius: 5px; 
                    margin-top: 0.5rem;
                    text-align: center;">
            <p style="margin: 0; color: #1A3B8F; font-weight: bold;">
                📍 Sede: {sede}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def render_quick_stats(sheets_manager: GoogleSheetsManager):
    """
    Renderiza estadísticas rápidas para el equipo sede.
    
    Args:
        sheets_manager: Manager de Google Sheets
    """
    try:
        sede = st.session_state.get("sede", "")
        if not sede or sede == "TODAS":
            return
        
        st.markdown("### 📊 Estadísticas Rápidas")
        
        # Cargar cursos de la sede
        cursos_sede = sheets_manager.load_courses_by_sede(sede)
        
        if cursos_sede:
            total_estudiantes = sum(len(c.get("estudiantes", [])) for c in cursos_sede.values())
            total_cursos = len(cursos_sede)
            
            # Calcular asistencia promedio
            total_asistencia = 0
            conteo_asistencia = 0
            
            for curso_data in cursos_sede.values():
                asistencias = curso_data.get("asistencias", {})
                estudiantes = curso_data.get("estudiantes", [])
                fechas = curso_data.get("fechas", [])
                
                if asistencias and estudiantes and fechas:
                    for estudiante in estudiantes:
                        asist_est = asistencias.get(estudiante, {})
                        presentes = sum(1 for estado in asist_est.values() if estado)
                        if fechas:
                            porcentaje = (presentes / len(fechas)) * 100
                            total_asistencia += porcentaje
                            conteo_asistencia += 1
            
            asistencia_promedio = (total_asistencia / conteo_asistencia) if conteo_asistencia > 0 else 0
            
            # Mostrar métricas
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📚 Cursos", total_cursos)
            with col2:
                st.metric("👨‍🎓 Estudiantes", total_estudiantes)
            
            # Mostrar asistencia promedio si hay datos
            if asistencia_promedio > 0:
                st.metric("📈 Asistencia Prom.", f"{asistencia_promedio:.1f}%")
            
            # Botón para actualizar estadísticas
            if st.button("🔄 Actualizar", key="refresh_stats", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
                
    except Exception as e:
        # Silenciar errores en el sidebar para no interrumpir la experiencia
        pass

def render_course_selector(cursos: Dict[str, Any], label: str = "Selecciona tu curso:") -> Optional[str]:
    """
    Renderiza un selector de cursos.
    
    Args:
        cursos: Diccionario de cursos
        label: Etiqueta para el selector
    
    Returns:
        Nombre del curso seleccionado o None
    """
    if not cursos:
        st.info("No hay cursos disponibles")
        return None
    
    curso_nombres = list(cursos.keys())
    
    # Agregar información adicional a las opciones
    opciones = []
    for nombre in curso_nombres:
        curso_data = cursos[nombre]
        estudiantes = len(curso_data.get("estudiantes", []))
        sede = curso_data.get("sede", "")
        opciones.append(f"{nombre} ({estudiantes} estudiantes, {sede})")
    
    # Selector
    opcion_seleccionada = st.selectbox(
        label,
        options=opciones,
        key="course_selector"
    )
    
    # Extraer nombre del curso de la opción seleccionada
    if opcion_seleccionada:
        # Buscar el nombre original
        for nombre in curso_nombres:
            if nombre in opcion_seleccionada:
                return nombre
    
    return None

def render_date_selector(fechas: list, label: str = "Fecha de clase:") -> Optional[str]:
    """
    Renderiza un selector de fechas.
    
    Args:
        fechas: Lista de fechas disponibles
        label: Etiqueta para el selector
    
    Returns:
        Fecha seleccionada o None
    """
    if not fechas:
        st.info("No hay fechas disponibles")
        return None
    
    # Ordenar fechas de más reciente a más antigua
    fechas_ordenadas = sorted(fechas, reverse=True)
    
    fecha_seleccionada = st.selectbox(
        label,
        options=fechas_ordenadas,
        key="date_selector"
    )
    
    return fecha_seleccionada

def render_attendance_checkboxes(estudiantes: list, fecha: str) -> Dict[str, bool]:
    """
    Renderiza checkboxes para marcar asistencia.
    
    Args:
        estudiantes: Lista de nombres de estudiantes
        fecha: Fecha de la clase (para keys únicos)
    
    Returns:
        Diccionario con {estudiante: presente}
    """
    asistencia = {}
    
    st.markdown("### 📝 Marcar Asistencia")
    
    # Dividir estudiantes en columnas para mejor visualización
    num_columns = 2 if len(estudiantes) > 10 else 1
    cols = st.columns(num_columns)
    
    for i, estudiante in enumerate(estudiantes):
        col_idx = i % num_columns
        with cols[col_idx]:
            # Crear un contenedor para cada estudiante
            with st.container():
                st.markdown(f"**{estudiante}**")
                
                # Usar radio buttons para mejor UX
                estado = st.radio(
                    f"Estado para {estudiante}",
                    options=["✅ Presente", "❌ Ausente"],
                    horizontal=True,
                    key=f"attendance_{estudiante}_{fecha}",
                    label_visibility="collapsed"
                )
                
                asistencia[estudiante] = estado == "✅ Presente"
    
    return asistencia

def render_loading_spinner(message: str = "Cargando..."):
    """
    Renderiza un spinner de carga elegante.
    
    Args:
        message: Mensaje a mostrar
    """
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem;">
        <div style="
            border: 4px solid #f3f3f3;
            border-top: 4px solid #1A3B8F;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 1rem auto;
        "></div>
        <p style="color: #666;">{message}</p>
    </div>
    
    <style>
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>
    """, unsafe_allow_html=True)