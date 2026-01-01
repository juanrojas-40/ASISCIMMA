import streamlit as st
from datetime import datetime

def setup_page(title: str = None, icon: str = None):
    """Configuración básica de la página"""
    if title:
        st.set_page_config(
            page_title=title,
            page_icon=icon or "🎓",
            layout="wide",
            initial_sidebar_state="expanded"
        )

def display_footer():
    """Muestra el footer de la aplicación"""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; font-size: 0.9rem;'>
        <p>© 2026 Preuniversitario CIMMA | Sistema de Asistencia v1.0</p>
        <p style='font-size: 0.8rem;'>🚀 Desarrollado con Streamlit | 🔒 Credenciales seguras en la nube</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def get_chile_time():
    """Obtiene la hora actual de Chile"""
    from pytz import timezone
    chile_tz = timezone("America/Santiago")
    return datetime.now(chile_tz)

def format_date(date_obj, format_str="%d/%m/%Y"):
    """Formatea una fecha"""
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime(format_str)

def validate_email(email: str) -> bool:
    """Valida formato de email básico"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))