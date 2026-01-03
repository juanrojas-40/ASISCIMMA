"""
Utils package for ASIS CIMMA
"""

# Importaciones principales
from .google_sheets import GoogleSheetsManager
from .email_sender import EmailManager
from .send_apoderados import enviar_comunicado_apoderados, ApoderadosEmailSender
from .auth import (
    require_login, 
    get_current_user, 
    authenticate_user,
    logout_user,
    is_authenticated,
    show_login_form,
    require_any_role,
    get_all_users,
    check_permission
)
from .helpers import format_date, calculate_age, validate_email, parse_date
from .error_handler import handle_error, log_error, display_error_message
from .cache_manager import CacheManager

__all__ = [
    # Google Sheets
    'GoogleSheetsManager',
    
    # Email
    'EmailManager',
    'enviar_comunicado_apoderados',
    'ApoderadosEmailSender',
    
    # Autenticación
    'require_login',
    'get_current_user',
    'authenticate_user',
    'logout_user',
    'is_authenticated',
    'show_login_form',
    'require_any_role',
    'get_all_users',
    'check_permission',
    
    # Helpers
    'format_date',
    'calculate_age',
    'validate_email',
    'parse_date',
    
    # Error Handling
    'handle_error',
    'log_error',
    'display_error_message',
    
    # Cache
    'CacheManager'
]