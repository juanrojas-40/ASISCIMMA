# utils/helpers.py
import streamlit as st
import pandas as pd
import io
from typing import Dict, List, Any
from datetime import datetime

def setup_page():
    """Configuración básica de la página - no se necesita si usamos set_page_config en app.py"""
    pass

def display_footer():
    """Muestra el pie de página"""
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>© 2026 Preuniversitario CIMMA | Sistema de Asistencia v2.0</p>
        <p>Desarrollado con Streamlit | Credenciales seguras en la nube</p>
    </div>
    """, unsafe_allow_html=True)

def export_to_excel(df: pd.DataFrame, filename: str = "reporte") -> bytes:
    """Exporta DataFrame a Excel en memoria"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Reporte', index=False)
    
    output.seek(0)
    return output.read()

def get_sede_from_username(username: str) -> str:
    """Obtiene la sede del usuario desde secrets o por patrones"""
    try:
        if "usuarios_sede" in st.secrets:
            for user_key, sede in st.secrets["usuarios_sede"].items():
                if user_key.lower() == username.lower():
                    return sede.upper()
    except:
        pass
    
    # Fallback al mapeo interno
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

def format_porcentaje(valor: float) -> str:
    """Formatea un porcentaje con 1 decimal"""
    return f"{valor:.1f}%"

def get_current_datetime() -> str:
    """Obtiene la fecha y hora actual formateada"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_date_only() -> str:
    """Obtiene solo la fecha actual"""
    return datetime.now().strftime("%Y-%m-%d")

def create_progress_bar(total: int, current: int, label: str = "Procesando"):
    """Crea y actualiza una barra de progreso"""
    if total > 0:
        progress = current / total
        st.progress(progress)
        st.caption(f"{label}: {current}/{total}")