# components/modals.py
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional, Callable

def show_confirmation_modal(
    title: str,
    message: str,
    on_confirm: Callable,
    on_cancel: Optional[Callable] = None,
    confirm_text: str = "Confirmar",
    cancel_text: str = "Cancelar"
):
    """
    Muestra un modal de confirmación.
    
    Args:
        title: Título del modal
        message: Mensaje de confirmación
        on_confirm: Función a ejecutar al confirmar
        on_cancel: Función a ejecutar al cancelar (opcional)
        confirm_text: Texto del botón de confirmación
        cancel_text: Texto del botón de cancelación
    """
    # Usar session state para controlar la visibilidad del modal
    modal_key = f"modal_{title.replace(' ', '_').lower()}"
    
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    # Botón para abrir el modal
    if st.button(title, key=f"open_{modal_key}"):
        st.session_state[modal_key] = True
    
    # Mostrar modal si está abierto
    if st.session_state[modal_key]:
        # Crear overlay
        components.html(f"""
        <div id="modal-overlay" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 9998;
            display: flex;
            justify-content: center;
            align-items: center;
        "></div>
        """, height=0)
        
        # Crear modal
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2:
                st.markdown(f"""
                <div style="
                    background: white;
                    padding: 2rem;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    z-index: 9999;
                    position: relative;
                ">
                    <h2 style="color: #1A3B8F; margin-top: 0;">{title}</h2>
                    <p>{message}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Botones de acción
                col_confirm, col_cancel = st.columns(2)
                
                with col_confirm:
                    if st.button(confirm_text, type="primary", use_container_width=True):
                        st.session_state[modal_key] = False
                        on_confirm()
                        st.rerun()
                
                with col_cancel:
                    if st.button(cancel_text, use_container_width=True):
                        st.session_state[modal_key] = False
                        if on_cancel:
                            on_cancel()
                        st.rerun()

def show_info_modal(title: str, message: str, button_text: str = "Aceptar"):
    """
    Muestra un modal informativo.
    
    Args:
        title: Título del modal
        message: Mensaje informativo
        button_text: Texto del botón de cierre
    """
    modal_key = f"info_modal_{title.replace(' ', '_').lower()}"
    
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    # Controlar la apertura del modal desde fuera
    if st.button(f"ℹ️ {title}", key=f"open_{modal_key}"):
        st.session_state[modal_key] = True
    
    # Mostrar modal
    if st.session_state[modal_key]:
        # Usar columns para centrar
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                border-top: 5px solid #1A3B8F;
                margin: 2rem 0;
            ">
                <div style="text-align: center; margin-bottom: 1.5rem;">
                    <div style="
                        background: #1A3B8F;
                        color: white;
                        width: 60px;
                        height: 60px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 2rem;
                        margin: 0 auto 1rem auto;
                    ">
                        ℹ️
                    </div>
                    <h3 style="color: #1A3B8F; margin: 0;">{title}</h3>
                </div>
                
                <div style="
                    background: #f8f9fa;
                    padding: 1.5rem;
                    border-radius: 8px;
                    margin-bottom: 1.5rem;
                    line-height: 1.6;
                ">
                    {message}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botón para cerrar
            if st.button(button_text, type="primary", use_container_width=True):
                st.session_state[modal_key] = False
                st.rerun()

def show_error_modal(error_message: str, technical_details: str = ""):
    """
    Muestra un modal de error.
    
    Args:
        error_message: Mensaje de error para el usuario
        technical_details: Detalles técnicos (opcional)
    """
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        animation: shake 0.5s;
    ">
        <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 1rem;">
            <div style="font-size: 2.5rem;">❌</div>
            <div>
                <h3 style="margin: 0; color: white;">Error del Sistema</h3>
                <p style="margin: 0; opacity: 0.9;">{error_message}</p>
            </div>
        </div>
        
        {f'<div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 5px; font-family: monospace; font-size: 0.9rem; margin-top: 1rem;">{technical_details}</div>' if technical_details else ''}
    </div>
    
    <style>
    @keyframes shake {{
        0%, 100% {{ transform: translateX(0); }}
        10%, 30%, 50%, 70%, 90% {{ transform: translateX(-5px); }}
        20%, 40%, 60%, 80% {{ transform: translateX(5px); }}
    }}
    </style>
    """, unsafe_allow_html=True)

def show_success_toast(message: str, duration: int = 3000):
    """
    Muestra un toast de éxito.
    
    Args:
        message: Mensaje a mostrar
        duration: Duración en milisegundos
    """
    toast_id = f"toast_{hash(message)}"
    
    components.html(f"""
    <script>
    function showToast() {{
        // Crear toast si no existe
        let toast = document.getElementById('{toast_id}');
        if (!toast) {{
            toast = document.createElement('div');
            toast.id = '{toast_id}';
            toast.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 15px 25px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                animation: slideIn 0.3s ease-out;
                display: flex;
                align-items: center;
                gap: 10px;
            `;
            toast.innerHTML = `
                <span style="font-size: 1.5rem;">✅</span>
                <span>{message}</span>
            `;
            document.body.appendChild(toast);
            
            // Remover después de la duración
            setTimeout(() => {{
                toast.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => toast.remove(), 300);
            }}, {duration});
        }}
    }}
    
    // Agregar animaciones CSS
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {{
            from {{ transform: translateX(100%); opacity: 0; }}
            to {{ transform: translateX(0); opacity: 1; }}
        }}
        @keyframes slideOut {{
            from {{ transform: translateX(0); opacity: 1; }}
            to {{ transform: translateX(100%); opacity: 0; }}
        }}
    `;
    document.head.appendChild(style);
    
    // Mostrar toast
    showToast();
    </script>
    """, height=0)

def show_warning_modal(title: str, message: str, actions: list = None):
    """
    Muestra un modal de advertencia con acciones personalizadas.
    
    Args:
        title: Título del modal
        message: Mensaje de advertencia
        actions: Lista de acciones en formato [(texto, función), ...]
    """
    modal_key = f"warning_modal_{title.replace(' ', '_').lower()}"
    
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    # El modal se activa externamente
    if st.session_state[modal_key]:
        # Overlay
        st.markdown("""
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 9998;
        "></div>
        """, unsafe_allow_html=True)
        
        # Modal centrado
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.2);
                z-index: 9999;
                position: relative;
                border-left: 6px solid #ffc107;
            ">
                <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 1.5rem;">
                    <div style="
                        background: #ffc107;
                        color: white;
                        width: 50px;
                        height: 50px;
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 1.8rem;
                    ">
                        ⚠️
                    </div>
                    <h3 style="margin: 0; color: #856404;">{title}</h3>
                </div>
                
                <div style="
                    background: #fff8e1;
                    padding: 1.5rem;
                    border-radius: 8px;
                    margin-bottom: 1.5rem;
                    border: 1px solid #ffeaa7;
                ">
                    {message}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botones de acción
            if actions:
                cols = st.columns(len(actions))
                for i, (action_text, action_func) in enumerate(actions):
                    with cols[i]:
                        if st.button(action_text, use_container_width=True, 
                                   type="primary" if i == 0 else "secondary"):
                            st.session_state[modal_key] = False
                            action_func()
                            st.rerun()
            else:
                if st.button("Aceptar", type="primary", use_container_width=True):
                    st.session_state[modal_key] = False
                    st.rerun()

def render_tooltip(text: str, tooltip_text: str):
    """
    Renderiza texto con tooltip.
    
    Args:
        text: Texto visible
        tooltip_text: Texto del tooltip
    """
    st.markdown(f"""
    <div style="position: relative; display: inline-block;">
        <span style="border-bottom: 1px dotted #666; cursor: help;">{text}</span>
        <div style="
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
        ">
            {tooltip_text}
            <div style="
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                border-width: 5px;
                border-style: solid;
                border-color: #333 transparent transparent transparent;
            "></div>
        </div>
    </div>
    
    <script>
    document.currentScript.parentElement.addEventListener('mouseenter', function() {{
        this.querySelector('div').style.visibility = 'visible';
        this.querySelector('div').style.opacity = '1';
    }});
    document.currentScript.parentElement.addEventListener('mouseleave', function() {{
        this.querySelector('div').style.visibility = 'hidden';
        this.querySelector('div').style.opacity = '0';
    }});
    </script>
    """, unsafe_allow_html=True)


def show_alumno_details_modal(alumno_data: dict, on_close: Optional[Callable] = None):
    """
    Muestra un modal con los detalles de un alumno.
    
    Args:
        alumno_data: Diccionario con datos del alumno
        on_close: Función a ejecutar al cerrar el modal (opcional)
    """
    modal_key = f"alumno_modal_{alumno_data.get('id', hash(str(alumno_data)))}"
    
    # Inicializar estado del modal si no existe
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    # Esta función se llama desde fuera para abrir el modal
    # Normalmente se llamaría con: st.session_state[modal_key] = True
    
    if st.session_state[modal_key]:
        # Overlay
        st.markdown("""
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 9998;
            backdrop-filter: blur(2px);
        "></div>
        """, unsafe_allow_html=True)
        
        # Modal centrado
        col1, col2, col3 = st.columns([1, 6, 1])
        
        with col2:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1A3B8F 0%, #2c5282 100%);
                color: white;
                padding: 2rem;
                border-radius: 15px;
                box-shadow: 0 25px 50px rgba(0,0,0,0.3);
                z-index: 9999;
                position: relative;
                margin: 2rem 0;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <div style="
                            background: rgba(255,255,255,0.2);
                            width: 60px;
                            height: 60px;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 2rem;
                        ">
                            👤
                        </div>
                        <div>
                            <h2 style="margin: 0; color: white;">{alumno_data.get('nombre_completo', alumno_data.get('nombre', 'Alumno'))}</h2>
                            <p style="margin: 0; opacity: 0.8;">{alumno_data.get('curso', 'Sin curso')}</p>
                        </div>
                    </div>
                    <div style="
                        background: rgba(255,255,255,0.1);
                        padding: 5px 15px;
                        border-radius: 20px;
                        font-size: 0.9rem;
                    ">
                        {alumno_data.get('estado', 'Activo')}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Contenido principal del modal
            with st.container():
                # Tabs para diferentes secciones
                tab1, tab2, tab3, tab4 = st.tabs(["📋 Información", "📊 Académico", "📞 Contacto", "📝 Notas"])
                
                with tab1:
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.markdown("### Información Personal")
                        st.write(f"**Nombre:** {alumno_data.get('nombre', 'N/A')}")
                        st.write(f"**Apellido:** {alumno_data.get('apellido', 'N/A')}")
                        st.write(f"**Edad:** {alumno_data.get('edad', 'N/A')}")
                        st.write(f"**RUT:** {alumno_data.get('rut', 'N/A')}")
                        st.write(f"**Fecha Nacimiento:** {alumno_data.get('fecha_nacimiento', 'N/A')}")
                    
                    with col_info2:
                        st.markdown("### Información del Curso")
                        st.write(f"**Curso:** {alumno_data.get('curso', 'N/A')}")
                        st.write(f"**Sede:** {alumno_data.get('sede', 'N/A')}")
                        st.write(f"**Profesor:** {alumno_data.get('profesor', 'N/A')}")
                        st.write(f"**Fecha Inscripción:** {alumno_data.get('fecha_inscripcion', 'N/A')}")
                        st.write(f"**Asignatura:** {alumno_data.get('asignatura', 'N/A')}")
                
                with tab2:
                    col_acad1, col_acad2 = st.columns(2)
                    
                    with col_acad1:
                        st.markdown("### Rendimiento Académico")
                        
                        # Métricas (valores por defecto si no existen)
                        promedio = alumno_data.get('promedio', 0)
                        asistencia = alumno_data.get('porcentaje_asistencia', 0)
                        notas_count = alumno_data.get('notas_registradas', 0)
                        
                        col_metric1, col_metric2 = st.columns(2)
                        with col_metric1:
                            st.metric("Promedio", f"{promedio:.1f}")
                        with col_metric2:
                            st.metric("Asistencia", f"{asistencia}%")
                        
                        st.metric("Notas Registradas", notas_count)
                        
                        # Gráfico de progreso simulado
                        if 'progreso' in alumno_data:
                            st.progress(alumno_data['progreso'])
                            st.caption("Progreso general")
                    
                    with col_acad2:
                        st.markdown("### Historial")
                        st.write(f"**Última Evaluación:** {alumno_data.get('ultima_evaluacion', 'N/A')}")
                        st.write(f"**Próxima Evaluación:** {alumno_data.get('proxima_evaluacion', 'N/A')}")
                        st.write(f"**Observaciones:**")
                        st.text(alumno_data.get('observaciones', 'Sin observaciones'))
                
                with tab3:
                    st.markdown("### Información de Contacto")
                    
                    col_contact1, col_contact2 = st.columns(2)
                    
                    with col_contact1:
                        st.write("**📧 Email:**")
                        email = alumno_data.get('email', 'No registrado')
                        st.code(email if email else "No registrado")
                        
                        st.write("**📱 Teléfono:**")
                        telefono = alumno_data.get('telefono', 'No registrado')
                        st.code(telefono if telefono else "No registrado")
                    
                    with col_contact2:
                        st.write("**👥 Apoderado:**")
                        st.write(f"**Nombre:** {alumno_data.get('nombre_apoderado', 'No registrado')}")
                        st.write(f"**Email:** {alumno_data.get('email_apoderado', 'No registrado')}")
                        st.write(f"**Teléfono:** {alumno_data.get('telefono_apoderado', 'No registrado')}")
                        
                        # Botón para contactar
                        if st.button("📧 Enviar Mensaje", use_container_width=True):
                            st.session_state['contactar_alumno'] = alumno_data
                            st.session_state[modal_key] = False
                            st.rerun()
                
                with tab4:
                    st.markdown("### Historial de Notas")
                    
                    # Simular tabla de notas
                    notas_ejemplo = [
                        {"Fecha": "2024-01-15", "Evaluación": "Prueba 1", "Nota": 6.2, "Ponderación": "20%"},
                        {"Fecha": "2024-01-22", "Evaluación": "Tarea 1", "Nota": 5.8, "Ponderación": "10%"},
                        {"Fecha": "2024-02-01", "Evaluación": "Prueba 2", "Nota": 6.5, "Ponderación": "20%"},
                        {"Fecha": "2024-02-15", "Evaluación": "Proyecto", "Nota": 7.0, "Ponderación": "30%"},
                    ]
                    
                    # Mostrar tabla
                    import pandas as pd
                    notas_df = pd.DataFrame(notas_ejemplo)
                    st.dataframe(notas_df, use_container_width=True, hide_index=True)
                    
                    # Formulario para agregar nota
                    with st.expander("➕ Agregar Nueva Nota"):
                        with st.form(f"agregar_nota_{modal_key}"):
                            col_fecha, col_eval = st.columns(2)
                            with col_fecha:
                                fecha_nota = st.date_input("Fecha")
                            with col_eval:
                                tipo_eval = st.selectbox("Tipo", ["Prueba", "Tarea", "Proyecto", "Examen"])
                            
                            col_nota, col_pond = st.columns(2)
                            with col_nota:
                                nota = st.number_input("Nota", min_value=1.0, max_value=7.0, step=0.1)
                            with col_pond:
                                ponderacion = st.selectbox("Ponderación", ["10%", "20%", "30%", "40%", "50%"])
                            
                            observacion = st.text_area("Observación")
                            
                            if st.form_submit_button("💾 Guardar Nota"):
                                st.success("Nota guardada exitosamente")
                                # Aquí iría la lógica para guardar en la base de datos
            
            # Pie del modal con acciones
            st.markdown("---")
            
            col_actions1, col_actions2, col_actions3 = st.columns(3)
            
            with col_actions1:
                if st.button("📄 Generar Reporte", use_container_width=True):
                    st.success("Reporte generado exitosamente")
                    # Lógica para generar reporte
            
            with col_actions2:
                if st.button("✏️ Editar Información", use_container_width=True):
                    st.session_state['editar_alumno'] = alumno_data
                    st.session_state[modal_key] = False
                    st.rerun()
            
            with col_actions3:
                if st.button("❌ Cerrar", type="primary", use_container_width=True):
                    st.session_state[modal_key] = False
                    if on_close:
                        on_close()
                    st.rerun()


def show_user_management_modal(user_data: dict = None):
    """
    Modal para gestionar usuarios (crear/editar).
    
    Args:
        user_data: Datos del usuario a editar (None para crear nuevo)
    """
    modal_key = "user_management_modal"
    is_edit = user_data is not None
    
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    if st.session_state[modal_key]:
        title = "✏️ Editar Usuario" if is_edit else "➕ Crear Nuevo Usuario"
        
        st.markdown("""
        <div style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 9998;
        "></div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 3, 1])
        
        with col2:
            st.markdown(f"""
            <div style="
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                z-index: 9999;
                position: relative;
            ">
                <h2 style="color: #1A3B8F; margin-top: 0;">{title}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form(f"user_form_{'edit' if is_edit else 'new'}"):
                col_name, col_email = st.columns(2)
                with col_name:
                    nombre = st.text_input("Nombre", value=user_data.get('nombre', '') if is_edit else '')
                with col_email:
                    email = st.text_input("Email", value=user_data.get('email', '') if is_edit else '')
                
                col_user, col_role = st.columns(2)
                with col_user:
                    username = st.text_input("Usuario", value=user_data.get('username', '') if is_edit else '')
                with col_role:
                    role = st.selectbox("Rol", ["admin", "profesor", "secretaria", "user"], 
                                      index=["admin", "profesor", "secretaria", "user"].index(
                                          user_data.get('role', 'user')) if is_edit else 3)
                
                if not is_edit:
                    col_pass, col_confirm = st.columns(2)
                    with col_pass:
                        password = st.text_input("Contraseña", type="password")
                    with col_confirm:
                        confirm_pass = st.text_input("Confirmar Contraseña", type="password")
                
                col_submit, col_cancel = st.columns(2)
                with col_submit:
                    submit = st.form_submit_button("💾 Guardar", type="primary", use_container_width=True)
                with col_cancel:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state[modal_key] = False
                        st.rerun()
                
                if submit:
                    if not is_edit and password != confirm_pass:
                        st.error("Las contraseñas no coinciden")
                    else:
                        st.success(f"Usuario {'actualizado' if is_edit else 'creado'} exitosamente")
                        st.session_state[modal_key] = False
                        time.sleep(1)
                        st.rerun()

def show_course_management_modal(course_data: dict = None):
    """
    Modal para gestionar cursos.
    """
    modal_key = "course_management_modal"
    is_edit = course_data is not None
    
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    if st.session_state[modal_key]:
        st.info("Modal de gestión de cursos - Implementación pendiente")
        if st.button("Cerrar"):
            st.session_state[modal_key] = False
            st.rerun()

def show_financial_report_modal():
    """
    Modal para reportes financieros.
    """
    modal_key = "financial_report_modal"
    
    if modal_key not in st.session_state:
        st.session_state[modal_key] = False
    
    if st.session_state[modal_key]:
        st.info("Modal de reportes financieros - Implementación pendiente")
        if st.button("Cerrar"):
            st.session_state[modal_key] = False
            st.rerun()