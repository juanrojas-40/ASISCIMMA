"""
Funciones helper para ASIS CIMMA
"""

import streamlit as st
import pandas as pd
import io
import re
import random
import string
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, date, timedelta

def setup_page():
    """Configuración básica de la página"""
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

# ===== FUNCIONES DE FECHA (las que necesitas importar) =====

def format_date(date_obj: Union[datetime, date, str], format_str: str = "%d/%m/%Y") -> str:
    """
    Formatea una fecha a string.
    
    Args:
        date_obj: Objeto datetime, date o string de fecha
        format_str: Formato de salida (default: dd/mm/yyyy)
    
    Returns:
        String formateado
    """
    if isinstance(date_obj, (datetime, date)):
        return date_obj.strftime(format_str)
    elif isinstance(date_obj, str):
        try:
            # Intentar parsear si es string
            parsed_date = parse_date(date_obj)
            if parsed_date:
                return parsed_date.strftime(format_str)
            return date_obj
        except:
            return date_obj
    else:
        return str(date_obj)

def parse_date(date_str: str, format_str: str = "%d/%m/%Y") -> Optional[datetime]:
    """
    Parsea un string a datetime.
    
    Args:
        date_str: String de fecha
        format_str: Formato esperado (default: dd/mm/yyyy)
    
    Returns:
        Objeto datetime o None si no se puede parsear
    """
    if not date_str:
        return None
    
    # Lista de formatos comunes a probar
    formats_to_try = [
        format_str,
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y"
    ]
    
    for fmt in formats_to_try:
        try:
            return datetime.strptime(str(date_str).strip(), fmt)
        except:
            continue
    
    # Si no funciona con ninguno, devolver None
    return None

def calculate_age(birth_date: Union[datetime, date, str]) -> Optional[int]:
    """
    Calcula la edad a partir de la fecha de nacimiento.
    
    Args:
        birth_date: Fecha de nacimiento
    
    Returns:
        Edad en años o None si no se puede calcular
    """
    try:
        if isinstance(birth_date, str):
            birth_date = parse_date(birth_date)
            if not birth_date:
                return None
        
        today = date.today()
        
        # Si ya es datetime.date, usarlo directamente
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date()
        elif isinstance(birth_date, date):
            pass  # Ya es date
        else:
            return None
        
        age = today.year - birth_date.year
        # Ajustar si aún no ha pasado el cumpleaños este año
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    except:
        return None

def validate_email(email: str) -> bool:
    """
    Valida formato de email.
    
    Args:
        email: String con email a validar
    
    Returns:
        True si el formato es válido
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

# ===== FUNCIONES EXISTENTES (las que ya tenías) =====

def get_sede_from_username(username: str) -> str:  
    """Obtiene la sede del usuario desde secrets o por patrones"""  
    try:  
        if "usuarios_sede" in st.secrets:  
            for user_key, sede in st.secrets["usuarios_sede"].items():  
                if user_key.lower() == username.lower():  
                    return sede.upper()  
    except:  
        pass  
    
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
    
    for key, sede in sedes_mapping.items():  
        if key in username_lower:  
            return sede  
    
    if 'sp' in username_lower:
        return 'SAN PEDRO'
    elif 'chillan' in username_lower or 'chillán' in username_lower:
        return 'CHILLAN'
    elif 'valdivia' in username_lower or 'pdv' in username_lower:
        return 'PEDRO DE VALDIVIA'
    elif 'conce' in username_lower or 'concepción' in username_lower:
        return 'CONCEPCIÓN'
    
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
        "admin": "👨‍💼 Administrador",
        "secretaria": "👩‍💼 Secretaria",
        "user": "👤 Usuario"
    }
    return role_mapping.get(role_type, role_type)

def safe_divide(numerator: float, denominator: float) -> float:
    """División segura evitando división por cero"""
    return numerator / denominator if denominator != 0 else 0

def truncate_text(text: str, max_length: int = 100) -> str:
    """Trunca texto y agrega '...' si es muy largo"""
    if not text:
        return ""
    
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text

def format_currency(amount: float) -> str:
    """Formatea un monto como moneda chilena"""
    if amount is None:
        return "$0"
    return f"${amount:,.0f}".replace(",", ".")

def get_time_ago(timestamp: datetime) -> str:
    """Calcula hace cuánto tiempo fue una fecha"""
    if not timestamp:
        return "Nunca"
    
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
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def sanitize_filename(filename: str) -> str:
    """Limpia un nombre de archivo para que sea seguro"""
    if not filename:
        return "archivo"
    
    # Remover caracteres no permitidos
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Reemplazar espacios por guiones bajos
    filename = filename.replace(' ', '_')
    # Limitar longitud
    if len(filename) > 100:
        filename = filename[:100]
    
    # Asegurar que tenga extensión
    if '.' not in filename:
        filename += '.xlsx'
    
    return filename

def export_to_excel(df: pd.DataFrame, filename: str = "reporte") -> bytes:  
    """Exporta DataFrame a Excel en memoria"""  
    output = io.BytesIO()  
    with pd.ExcelWriter(output, engine='openpyxl') as writer:  
        df.to_excel(writer, sheet_name='Reporte', index=False)  
    
    output.seek(0)  
    return output.read()

def days_between(date1: Union[datetime, date, str], date2: Union[datetime, date, str]) -> int:
    """
    Calcula días entre dos fechas.
    
    Args:
        date1, date2: Fechas a comparar
    
    Returns:
        Días de diferencia (absoluto)
    """
    try:
        if isinstance(date1, str):
            date1 = parse_date(date1)
        if isinstance(date2, str):
            date2 = parse_date(date2)
        
        if isinstance(date1, datetime):
            date1 = date1.date()
        if isinstance(date2, datetime):
            date2 = date2.date()
        
        if not date1 or not date2:
            return 0
        
        return abs((date2 - date1).days)
    except:
        return 0

def is_date_in_range(check_date: Union[datetime, date, str], 
                     start_date: Union[datetime, date, str], 
                     end_date: Union[datetime, date, str]) -> bool:
    """
    Verifica si una fecha está dentro de un rango.
    """
    try:
        if isinstance(check_date, str):
            check_date = parse_date(check_date)
        if isinstance(start_date, str):
            start_date = parse_date(start_date)
        if isinstance(end_date, str):
            end_date = parse_date(end_date)
        
        if not all([check_date, start_date, end_date]):
            return False
        
        if isinstance(check_date, datetime):
            check_date = check_date.date()
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        
        return start_date <= check_date <= end_date
    except:
        return False