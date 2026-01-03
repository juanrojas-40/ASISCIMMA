"""
Dashboard del Profesor - Página principal para profesores
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.auth import require_login, get_current_user
from utils.google_sheets import get_alumnos_data, get_cursos_data
from components.headers import render_main_header, render_section_header
from components.modals import show_alumno_details_modal

@require_login(role="profesor")
def show_profesor_dashboard():
    """
    Renderiza el dashboard principal para profesores
    """
    # Obtener usuario actual
    user = get_current_user()
    
    # Configurar página
    st.set_page_config(
        page_title=f"Dashboard Profesor - {user.get('nombre', '')}",
        page_icon="👨‍🏫",
        layout="wide"
    )
    
    # Header principal
    render_main_header(
        title=f"Bienvenido, Profesor {user.get('nombre', '')}",
        subtitle="Gestión de cursos y alumnos asignados"
    )
    
    # Obtener datos
    alumnos_df = get_alumnos_data()
    cursos_df = get_cursos_data()
    
    # Filtrar alumnos del profesor actual
    if 'id_profesor' in user:
        alumnos_profesor = alumnos_df[alumnos_df['id_profesor'] == user['id_profesor']]
        cursos_profesor = cursos_df[cursos_df['id_profesor'] == user['id_profesor']]
    else:
        alumnos_profesor = alumnos_df
        cursos_profesor = cursos_df
    
    # Sidebar con filtros
    with st.sidebar:
        st.markdown("### 📊 Filtros")
        
        # Filtro por curso
        cursos_list = cursos_profesor['nombre_curso'].unique().tolist()
        curso_seleccionado = st.selectbox(
            "Seleccionar Curso",
            ["Todos"] + cursos_list
        )
        
        # Filtro por estado
        estado = st.selectbox(
            "Estado del Alumno",
            ["Todos", "Activo", "Inactivo", "Graduado"]
        )
        
        # Filtro por fecha
        fecha_inicio = st.date_input("Desde", datetime.now().replace(day=1))
        fecha_fin = st.date_input("Hasta", datetime.now())
    
    # Layout principal
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_section_header("📈 Resumen General")
        
        # Métricas
        total_alumnos = len(alumnos_profesor)
        alumnos_activos = len(alumnos_profesor[alumnos_profesor['estado'] == 'Activo'])
        cursos_count = len(cursos_profesor)
        
        st.metric("Total Alumnos", total_alumnos)
        st.metric("Alumnos Activos", alumnos_activos)
        st.metric("Cursos Asignados", cursos_count)
    
    with col2:
        render_section_header("📋 Lista de Alumnos")
        
        # Aplicar filtros
        alumnos_filtrados = alumnos_profesor.copy()
        
        if curso_seleccionado != "Todos":
            alumnos_filtrados = alumnos_filtrados[
                alumnos_filtrados['nombre_curso'] == curso_seleccionado
            ]
        
        if estado != "Todos":
            alumnos_filtrados = alumnos_filtrados[
                alumnos_filtrados['estado'] == estado
            ]
        
        # Mostrar tabla de alumnos
        if not alumnos_filtrados.empty:
            # Seleccionar columnas para mostrar
            columnas_mostrar = ['nombre', 'apellido', 'curso', 'estado', 'fecha_inscripcion']
            st.dataframe(
                alumnos_filtrados[columnas_mostrar],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay alumnos que coincidan con los filtros")
    
    with col3:
        render_section_header("🚨 Acciones Rápidas")
        
        # Botones de acción
        if st.button("📤 Exportar Reporte", use_container_width=True):
            exportar_reporte(alumnos_filtrados)
        
        if st.button("📧 Enviar Comunicado", use_container_width=True):
            enviar_comunicado(alumnos_filtrados)
        
        if st.button("📅 Agendar Reunión", use_container_width=True):
            agendar_reunion()
        
        if st.button("📝 Registrar Asistencia", use_container_width=True):
            registrar_asistencia()
    
    # Sección de detalles expandidos
    st.markdown("---")
    render_section_header("👥 Detalle por Alumno")
    
    # Mostrar detalles expandidos
    if not alumnos_filtrados.empty:
        for idx, alumno in alumnos_filtrados.iterrows():
            with st.expander(f"👤 {alumno['nombre']} {alumno['apellido']} - {alumno['curso']}"):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("**Información Personal:**")
                    st.write(f"📧 Email: {alumno.get('email', 'N/A')}")
                    st.write(f"📞 Teléfono: {alumno.get('telefono', 'N/A')}")
                    st.write(f"📅 Fecha Inscripción: {alumno.get('fecha_inscripcion', 'N/A')}")
                
                with col_b:
                    st.write("**Información Académica:**")
                    st.write(f"📊 Estado: {alumno.get('estado', 'N/A')}")
                    st.write(f"🏆 Promedio: {alumno.get('promedio', 'N/A')}")
                    st.write(f"📚 Asistencias: {alumno.get('asistencias', 'N/A')}")
                
                # Botones de acción por alumno
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button("📊 Ver Notas", key=f"notas_{idx}"):
                        mostrar_notas(alumno)
                
                with col_btn2:
                    if st.button("📝 Registrar Nota", key=f"registrar_{idx}"):
                        registrar_nota(alumno)
                
                with col_btn3:
                    if st.button("💬 Contactar", key=f"contactar_{idx}"):
                        contactar_alumno(alumno)
    
    # Footer
    st.markdown("---")
    st.caption(f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# Funciones auxiliares
def exportar_reporte(alumnos_df):
    """Exporta un reporte de alumnos"""
    if not alumnos_df.empty:
        csv = alumnos_df.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"reporte_alumnos_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No hay datos para exportar")

def enviar_comunicado(alumnos_df):
    """Abre modal para enviar comunicado"""
    with st.form("enviar_comunicado"):
        st.write("### 📧 Enviar Comunicado")
        asunto = st.text_input("Asunto")
        mensaje = st.text_area("Mensaje")
        enviar = st.form_submit_button("Enviar")
        
        if enviar and alumnos_df is not None:
            # Implementar lógica de envío
            emails = alumnos_df['email'].dropna().tolist()
            st.success(f"Comunicado enviado a {len(emails)} alumnos")

def agendar_reunion():
    """Abre modal para agendar reunión"""
    st.session_state['show_agendar_reunion'] = True
    # La lógica completa iría en un modal

def registrar_asistencia():
    """Abre modal para registrar asistencia"""
    st.session_state['show_registrar_asistencia'] = True
    # La lógica completa iría en un modal

def mostrar_notas(alumno):
    """Muestra notas del alumno"""
    st.session_state['alumno_seleccionado'] = alumno
    st.session_state['show_notas'] = True

def registrar_nota(alumno):
    """Abre modal para registrar nota"""
    st.session_state['alumno_seleccionado'] = alumno
    st.session_state['show_registrar_nota'] = True

def contactar_alumno(alumno):
    """Abre modal para contactar alumno"""
    st.session_state['alumno_seleccionado'] = alumno
    st.session_state['show_contactar'] = True

# Para ejecutar directamente (solo para pruebas)
if __name__ == "__main__":
    # Para pruebas, simular un usuario
    st.session_state['user'] = {
        'id': 1,
        'nombre': 'Profesor Demo',
        'email': 'profesor@demo.com',
        'role': 'profesor',
        'id_profesor': 101
    }
    show_profesor_dashboard()