# config/constants.py
from enum import Enum

class UserRole(str, Enum):
    """Roles de usuario del sistema."""
    PROFESOR = "profesor"
    EQUIPO_SEDE = "equipo_sede"
    ADMINISTRADOR = "administrador"

class Sede(str, Enum):
    """Sedes disponibles."""
    SAN_PEDRO = "SAN PEDRO"
    CHILLAN = "CHILLAN"
    PEDRO_DE_VALDIVIA = "PEDRO DE VALDIVIA"
    CONCEPCION = "CONCEPCIÓN"
    TODAS = "TODAS"

class AttendanceStatus(str, Enum):
    """Estados de asistencia."""
    PRESENTE = "presente"
    AUSENTE = "ausente"
    JUSTIFICADO = "justificado"

# Constantes de UI
COLORS = {
    "primary": "#1A3B8F",
    "secondary": "#2D4FA8",
    "success": "#28a745",
    "danger": "#dc3545",
    "warning": "#ffc107",
    "info": "#17a2b8"
}

ICONS = {
    "profesor": "👨‍🏫",
    "equipo_sede": "👩‍💼",
    "administrador": "👨‍💼",
    "presente": "✅",
    "ausente": "❌",
    "justificado": "⚠️",
    "curso": "📚",
    "estudiante": "👨‍🎓",
    "email": "📧",
    "reporte": "📊"
}

# Límites del sistema
MAX_STUDENTS_PER_COURSE = 100
MAX_COURSES_PER_TEACHER = 10
MAX_EMAILS_PER_BATCH = 100