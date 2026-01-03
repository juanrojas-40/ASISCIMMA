# components/headers.py
import streamlit as st
from config import constants

def render_main_header(title: str, subtitle: str = ""):
    """
    Renderiza el header principal de la página.
    
    Args:
        title: Título principal
        subtitle: Subtítulo (opcional)
    """
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="main-header">{title}</h1>
        {f'<p style="color: #666; font-size: 1.2rem;">{subtitle}</p>' if subtitle else ''}
    </div>
    """, unsafe_allow_html=True)

def render_section_header(title: str, icon: str = ""):
    """
    Renderiza un header de sección.
    
    Args:
        title: Título de la sección
        icon: Icono opcional
    """
    icon_html = f'<span style="margin-right: 10px; font-size: 1.5rem;">{icon}</span>' if icon else ""
    
    st.markdown(f"""
    <div style="margin: 2rem 0 1.5rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #1A3B8F;">
        <h2 style="color: #1A3B8F; display: flex; align-items: center;">
            {icon_html}{title}
        </h2>
    </div>
    """, unsafe_allow_html=True)

def render_metric_card(title: str, value: Any, icon: str = "", delta: Optional[str] = None):
    """
    Renderiza una tarjeta de métrica.
    
    Args:
        title: Título de la métrica
        value: Valor de la métrica
        icon: Icono opcional
        delta: Valor delta para mostrar cambio
    """
    icon_html = f'<div style="font-size: 2rem; margin-bottom: 10px;">{icon}</div>' if icon else ""
    delta_html = f'<div style="font-size: 0.9rem; color: {"#28a745" if delta and "-" not in str(delta) else "#dc3545"}">{delta}</div>' if delta else ""
    
    st.markdown(f"""
    <div class="metric-card">
        {icon_html}
        <div style="font-size: 2rem; font-weight: bold; margin: 10px 0;">{value}</div>
        <div style="font-size: 0.9rem; opacity: 0.9;">{title}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def render_info_card(title: str, content: str, type: str = "info"):
    """
    Renderiza una tarjeta de información.
    
    Args:
        title: Título de la tarjeta
        content: Contenido de la tarjeta
        type: Tipo de tarjeta (info, success, warning, error)
    """
    colors = {
        "info": {"bg": "#d1ecf1", "border": "#bee5eb", "text": "#0c5460", "icon": "ℹ️"},
        "success": {"bg": "#d4edda", "border": "#c3e6cb", "text": "#155724", "icon": "✅"},
        "warning": {"bg": "#fff3cd", "border": "#ffeaa7", "text": "#856404", "icon": "⚠️"},
        "error": {"bg": "#f8d7da", "border": "#f5c6cb", "text": "#721c24", "icon": "❌"}
    }
    
    color = colors.get(type, colors["info"])
    
    st.markdown(f"""
    <div style="
        background-color: {color['bg']};
        border: 1px solid {color['border']};
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: {color['text']};
    ">
        <div style="display: flex; align-items: flex-start; gap: 10px;">
            <div style="font-size: 1.5rem;">{color['icon']}</div>
            <div>
                <h4 style="margin: 0 0 10px 0; color: {color['text']};">{title}</h4>
                <div style="line-height: 1.6;">{content}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_breadcrumb(items: list):
    """
    Renderiza una barra de migas de pan.
    
    Args:
        items: Lista de items en formato [(nombre, icono), ...]
    """
    breadcrumb_html = '<div style="display: flex; align-items: center; margin-bottom: 1rem; font-size: 0.9rem; color: #666;">'
    
    for i, (name, icon) in enumerate(items):
        breadcrumb_html += f'<span style="margin-right: 5px;">{icon}</span>{name}'
        if i < len(items) - 1:
            breadcrumb_html += '<span style="margin: 0 10px;">›</span>'
    
    breadcrumb_html += '</div>'
    
    st.markdown(breadcrumb_html, unsafe_allow_html=True)

def render_page_title(user_role: str, user_sede: str = ""):
    """
    Renderiza el título de la página según el rol del usuario.
    
    Args:
        user_role: Rol del usuario
        user_sede: Sede del usuario
    """
    if "Equipo Sede" in user_role and user_sede and user_sede != "TODAS":
        render_main_header(f"📍 Sede {user_sede}", f"Panel de {user_role}")
    else:
        render_main_header(f"Bienvenido, {st.session_state.get('user', 'Usuario')}!", f"Rol: {user_role}")

def render_action_buttons(buttons: list):
    """
    Renderiza una fila de botones de acción.
    
    Args:
        buttons: Lista de botones en formato [(texto, tipo, key), ...]
    """
    cols = st.columns(len(buttons))
    
    for i, (text, button_type, key) in enumerate(buttons):
        with cols[i]:
            if button_type == "primary":
                st.button(text, type="primary", key=key, use_container_width=True)
            elif button_type == "secondary":
                st.button(text, type="secondary", key=key, use_container_width=True)
            else:
                st.button(text, key=key, use_container_width=True)

def render_progress_bar(current: int, total: int, label: str = "Progreso"):
    """
    Renderiza una barra de progreso personalizada.
    
    Args:
        current: Valor actual
        total: Valor total
        label: Etiqueta de la barra
    """
    percentage = (current / total) * 100 if total > 0 else 0
    
    st.markdown(f"""
    <div style="margin: 1rem 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span>{label}</span>
            <span>{current}/{total} ({percentage:.1f}%)</span>
        </div>
        <div style="
            width: 100%;
            background-color: #e9ecef;
            border-radius: 10px;
            overflow: hidden;
            height: 10px;
        ">
            <div style="
                width: {percentage}%;
                background-color: #1A3B8F;
                height: 100%;
                transition: width 0.3s ease;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)