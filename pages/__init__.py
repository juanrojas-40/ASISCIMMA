# pages/__init__.py
from .profesor_dashboard import show_profesor_dashboard
from .secretaria_dashboard import show_secretaria_dashboard
from .admin_dashboard import show_admin_dashboard

__all__ = [
    'show_profesor_dashboard',
    'show_secretaria_dashboard', 
    'show_admin_dashboard'
]