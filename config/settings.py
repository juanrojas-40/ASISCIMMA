# config/settings.py
import streamlit as st
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class AppSettings:
    """Configuración centralizada de la aplicación."""
    
    # Google Sheets
    GOOGLE_SHEETS_RATE_LIMIT: int = 45
    GOOGLE_SHEETS_CACHE_TTL: int = 1800
    GOOGLE_SHEETS_RETRY_ATTEMPTS: int = 3
    
    # Email
    EMAIL_DELAY_BETWEEN_SENDS: float = 0.8
    EMAIL_BATCH_SIZE: int = 50
    
    # UI
    PAGE_SIZE: int = 50
    AUTO_REFRESH: int = 300
    DEBUG_MODE: bool = False
    
    # Features
    ENABLE_BULK_EMAILS: bool = True
    ENABLE_REPORTS_EXPORT: bool = True
    ENABLE_ATTENDANCE_NOTIFICATIONS: bool = True
    ENABLE_CACHE: bool = True
    
    # Paths
    LOGO_PATH: str = "assets/logo.png"
    EMAIL_TEMPLATES_PATH: str = "templates/emails/"
    
    @classmethod
    def load_from_secrets(cls):
        """Carga configuración desde secrets de Streamlit."""
        settings = cls()
        
        # Sobrescribir con valores de secrets si existen
        if "APP_SETTINGS" in st.secrets:
            secrets_settings = st.secrets["APP_SETTINGS"]
            for key, value in secrets_settings.items():
                key_upper = key.upper()
                if hasattr(settings, key_upper):
                    # Convertir tipos según corresponda
                    current_type = type(getattr(settings, key_upper))
                    try:
                        if current_type == bool:
                            value = str(value).lower() in ["true", "1", "yes", "si"]
                        elif current_type == int:
                            value = int(value)
                        elif current_type == float:
                            value = float(value)
                        
                        setattr(settings, key_upper, value)
                    except (ValueError, TypeError):
                        st.warning(f"⚠️ No se pudo convertir {key} a {current_type}")
        
        return settings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte configuración a diccionario."""
        return {
            "GOOGLE_SHEETS_RATE_LIMIT": self.GOOGLE_SHEETS_RATE_LIMIT,
            "GOOGLE_SHEETS_CACHE_TTL": self.GOOGLE_SHEETS_CACHE_TTL,
            "EMAIL_DELAY_BETWEEN_SENDS": self.EMAIL_DELAY_BETWEEN_SENDS,
            "DEBUG_MODE": self.DEBUG_MODE,
            "AUTO_REFRESH": self.AUTO_REFRESH
        }