# utils/helpers.py
import streamlit as st
import pandas as pd
import io
from typing import Dict, List
import json

def export_to_excel(df: pd.DataFrame, filename: str = "reporte"):
    """Exporta DataFrame a Excel en memoria"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Reporte', index=False)
    return output.getvalue()

def get_sede_from_username(username: str) -> str:
    """Obtiene la sede del usuario desde secrets"""
    try:
        if "usuarios_sede" in st.secrets:
            for user_key, sede in st.secrets["usuarios_sede"].items():
                if user_key.lower() == username.lower():
                    return sede.upper()
        
        # Fallback al mapeo interno
        username_lower = username.lower()
        if 'sp' in username_lower:
            return 'SAN PEDRO'
        elif 'chillan' in username_lower:
            return 'CHILLAN'
        elif 'valdivia' in username_lower or 'pdv' in username_lower:
            return 'PEDRO DE VALDIVIA'
        elif 'conce' in username_lower:
            return 'CONCEPCIÓN'
        
        return 'TODAS'
        
    except:
        return 'TODAS'