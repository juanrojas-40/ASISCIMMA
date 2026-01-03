import streamlit as st
import logging
import traceback
from typing import Optional, Callable, Any
from config.settings import AppSettings

logger = logging.getLogger(__name__)

class ErrorHandler:
    """Manejador centralizado de errores de la aplicación."""
    
    @staticmethod
    def handle_google_sheets_error(error: Exception, context: str = ""):
        """Maneja errores específicos de Google Sheets."""
        error_msg = str(error)
        
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            ErrorHandler._show_rate_limit_error(context)
        elif "401" in error_msg or "403" in error_msg:
            ErrorHandler._show_auth_error(context)
        elif "404" in error_msg:
            ErrorHandler._show_not_found_error(context)
        else:
            ErrorHandler._show_generic_error(error, context)
        
        # Log para debugging
        logger.error(f"Google Sheets Error ({context}): {error_msg}")
    
    @staticmethod
    def handle_email_error(error: Exception, context: str = ""):
        """Maneja errores de envío de emails."""
        error_msg = str(error)
        
        if "authentication" in error_msg.lower():
            st.error("""
            🔐 **Error de autenticación de email**
            
            No se pudo autenticar con el servidor SMTP. Verifique:
            1. El email y contraseña en secrets.toml
            2. Que el email tenga habilitada la autenticación de aplicaciones
            3. Que no esté bloqueado por medidas de seguridad
            """)
        elif "connection" in error_msg.lower():
            st.error("""
            🔌 **Error de conexión SMTP**
            
            No se pudo conectar al servidor de email. Verifique:
            1. La configuración del servidor SMTP
            2. El puerto SMTP (generalmente 587 para TLS)
            3. Su conexión a internet
            """)
        else:
            ErrorHandler._show_generic_error(error, context)
        
        logger.error(f"Email Error ({context}): {error_msg}")
    
    @staticmethod
    def handle_auth_error(message: str = ""):
        """Maneja errores de autenticación."""
        st.error(f"""
        🔐 **Error de autenticación**
        
        {message if message else 'Credenciales incorrectas o usuario no autorizado.'}
        
        Verifique:
        1. Su nombre de usuario y contraseña
        2. Que tenga permisos para acceder al sistema
        3. Su rol seleccionado
        """)
    
    @staticmethod
    def handle_critical_error(error: Exception, context: str = ""):
        """Maneja errores críticos de la aplicación."""
        logger.critical(f"Critical Error ({context}): {str(error)}")
        
        st.error(f"""
        💥 **Error crítico en la aplicación**
        
        Contexto: {context}
        
        **Qué hacer:**
        1. Recargue la página (F5)
        2. Intente nuevamente en unos minutos
        3. Contacte al administrador si el error persiste
        
        **Detalles técnicos (para administrador):**
        ```python
        {str(error)[:500]}
        ```
        """)
    
    @staticmethod
    def _show_rate_limit_error(context: str):
        """Muestra error de límite de tasa."""
        st.error(f"""
        ⚠️ **Límite de API alcanzado**
        
        Google Sheets API ha alcanzado su límite de solicitudes por minuto.
        
        Contexto: {context}
        
        **Solución:**
        1. Espere 1-2 minutos y reintente
        2. Reduzca la frecuencia de actualización
        3. Contacte al administrador para aumentar el quota
        
        💡 **Nota:** Los datos se cachean automáticamente por 30 minutos
        """)
    
    @staticmethod
    def _show_auth_error(context: str):
        """Muestra error de autenticación."""
        st.error(f"""
        🔐 **Error de autenticación con Google Sheets**
        
        Contexto: {context}
        
        **Verifique:**
        1. Las credenciales en secrets.toml
        2. Que la hoja esté compartida con el service account
        3. Los permisos de la hoja (lectura/escritura)
        
        🔧 **Configuración requerida:**
        - Service account con permisos de editor
        - Hoja compartida con el email del service account
        """)
    
    @staticmethod
    def _show_not_found_error(context: str):
        """Muestra error de recurso no encontrado."""
        st.error(f"""
        🔍 **Recurso no encontrado**
        
        Contexto: {context}
        
        **Posibles causas:**
        1. El ID de la hoja es incorrecto
        2. La hoja fue eliminada o movida
        3. No tiene acceso a la hoja
        
        **Solución:**
        1. Verifique el ID de la hoja en secrets.toml
        2. Confirme que la hoja existe y está accesible
        """)
    
    @staticmethod
    def _show_generic_error(error: Exception, context: str):
        """Muestra error genérico."""
        st.error(f"""
        ❌ **Error en el sistema**
        
        Contexto: {context}
        
        **Detalles:**
        {str(error)[:200]}
        
        **Acciones recomendadas:**
        1. Intente la operación nuevamente
        2. Verifique la conexión a internet
        3. Contacte al administrador
        """)
    
    @staticmethod
    def log_operation(operation: str, success: bool, details: dict = None):
        """Registra operaciones del sistema."""
        status = "✅ ÉXITO" if success else "❌ FALLO"
        details_str = f" - Detalles: {details}" if details else ""
        
        logger.info(f"{status} - Operación: {operation}{details_str}")
        
        # Mostrar notificación en modo debug
        if AppSettings.load_from_secrets().DEBUG_MODE:
            if success:
                st.toast(f"✅ {operation} completado", icon="✅")
            else:
                st.toast(f"❌ {operation} falló", icon="❌")

# Funciones de conveniencia para uso directo
def handle_error(func: Optional[Callable] = None, context: str = ""):
    """
    Decorador para manejar errores en funciones.
    
    Args:
        func: Función a decorar
        context: Contexto del error
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error en {f.__name__} ({context}): {str(e)}")
                ErrorHandler._show_generic_error(e, f"{context} - {f.__name__}")
                return None
        return wrapper
    
    if func:
        return decorator(func)
    return decorator

def log_error(error: Exception, context: str = ""):
    """Función conveniente para loguear errores."""
    logger.error(f"Error ({context}): {str(error)}")
    logger.debug(traceback.format_exc())

def display_error_message(error: Exception, context: str = ""):
    """Función conveniente para mostrar errores."""
    ErrorHandler._show_generic_error(error, context)