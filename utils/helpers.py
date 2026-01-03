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

def get_user_role_display(role_type: str) -> str:
    """Convierte el tipo de rol a formato de visualización"""
    role_mapping = {
        "profesor": "👨‍🏫 Profesor",
        "equipo_sede": "👩‍💼 Equipo Sede", 
        "admin": "👨‍💼 Administrador"
    }
    return role_mapping.get(role_type, role_type)

def validate_email(email: str) -> bool:
    """Valida formato básico de email"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) if email else False

def safe_divide(numerator: float, denominator: float) -> float:
    """División segura evitando división por cero"""
    return numerator / denominator if denominator != 0 else 0

def truncate_text(text: str, max_length: int = 100) -> str:
    """Trunca texto y agrega '...' si es muy largo"""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def format_currency(amount: float) -> str:
    """Formatea un monto como moneda chilena"""
    return f"${amount:,.0f}".replace(",", ".")

def get_time_ago(timestamp: datetime) -> str:
    """Calcula hace cuánto tiempo fue una fecha"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"Hace {years} año{'s' if years > 1 else ''}"
    elif diff.days > 30:
        months = diff.days // 30
        return f"Hace {months} mes{'es' if months > 1 else ''}"
    elif diff.days > 0:
        return f"Hace {diff.days} día{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"Hace {hours} hora{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"Hace {minutes} minuto{'s' if minutes > 1 else ''}"
    else:
        return "Hace unos segundos"

def generate_password(length: int = 8) -> str:
    """Genera una contraseña aleatoria"""
    import random
    import string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def sanitize_filename(filename: str) -> str:
    """Limpia un nombre de archivo para que sea seguro"""
    import re
    # Remover caracteres no permitidos
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Reemplazar espacios por guiones bajos
    filename = filename.replace(' ', '_')
    # Limitar longitud
    if len(filename) > 100:
        filename = filename[:100]
    return filename