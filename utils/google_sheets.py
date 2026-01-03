# utils/google_sheets.py
import gspread
import pandas as pd
import json
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import time
from functools import wraps
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === DECORADOR DE RATE LIMITING MEJORADO ===
def rate_limited(calls_per_minute=45):
    """
    Limita las llamadas a la API para evitar el error 429.
    Versión mejorada con contador por minuto y reseteo automático.
    """
    min_interval = 60.0 / calls_per_minute
    
    def decorator(func):
        # Variables persistentes por función
        last_called = [0.0]
        request_count = [0]
        reset_time = [time.time() + 60]
        lock = False  # Para evitar llamadas concurrentes
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal lock
            
            # Evitar ejecución concurrente
            while lock:
                time.sleep(0.01)
            lock = True
            
            try:
                current_time = time.time()
                
                # Resetear contador si pasó 1 minuto
                if current_time > reset_time[0]:
                    request_count[0] = 0
                    reset_time[0] = current_time + 60
                    logger.debug(f"Contador de requests reseteado. Nuevo reset en: {reset_time[0]}")
                
                # Verificar si hemos alcanzado el límite por minuto
                if request_count[0] >= calls_per_minute:
                    wait_time = reset_time[0] - current_time
                    if wait_time > 0:
                        logger.warning(f"Límite de {calls_per_minute} requests/min alcanzado. Esperando {wait_time:.1f} segundos...")
                        time.sleep(wait_time + 0.5)  # Margen adicional
                        # Resetear después de la espera
                        request_count[0] = 0
                        reset_time[0] = time.time() + 60
                
                # Controlar intervalo mínimo entre llamadas
                elapsed = current_time - last_called[0]
                left_to_wait = min_interval - elapsed
                if left_to_wait > 0:
                    time.sleep(left_to_wait)
                
                # Incrementar contador y ejecutar
                request_count[0] += 1
                ret = func(*args, **kwargs)
                last_called[0] = time.time()
                
                # Log para debugging
                if st.secrets.get("DEBUG", False):
                    logger.info(f"Request #{request_count[0]}/{calls_per_minute} - Próximo reset en {reset_time[0] - time.time():.0f}s")
                
                return ret
                
            except Exception as e:
                logger.error(f"Error en función {func.__name__}: {str(e)}")
                raise
            finally:
                lock = False
                
        return wrapper
    return decorator

# === DECORADOR DE RETRY CON BACKOFF EXPONENCIAL ===
def retry_with_backoff(max_retries=3, initial_delay=1.5, backoff_factor=2.5, 
                      retry_exceptions=(Exception,)):
    """
    Decorador para reintentar operaciones con backoff exponencial.
    Especialmente útil para errores 429 de Google Sheets API.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 para incluir el intento inicial
                try:
                    if attempt > 0:
                        logger.warning(f"Reintento #{attempt} para {func.__name__} en {delay:.1f} segundos...")
                        time.sleep(delay)
                        delay *= backoff_factor  # Backoff exponencial
                    
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_exception = e
                    
                    # Verificar si es un error 429 que vale la pena reintentar
                    should_retry = False
                    error_str = str(e)
                    
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        should_retry = True
                        logger.warning(f"Error 429 detectado en {func.__name__}. Reintentando...")
                    
                    elif any(exc_type for exc_type in retry_exceptions if isinstance(e, exc_type)):
                        should_retry = True
                    
                    # Si no debemos reintentar o es el último intento, lanzar excepción
                    if not should_retry or attempt == max_retries:
                        if attempt > 0:
                            logger.error(f"Falló después de {attempt + 1} intentos: {str(e)}")
                        raise
                    
            # Nunca debería llegar aquí, pero por seguridad
            raise last_exception if last_exception else Exception("Error desconocido en retry")
            
        return wrapper
    return decorator

# === CLIENTE CON CACHÉ A NIVEL DE RECURSO ===
@st.cache_resource(show_spinner=False)
def _get_gsheets_client():
    """
    Inicializa y almacena en cache el cliente de Google Sheets.
    Uso interno - no llamar directamente desde el código.
    """
    try:
        if "google" not in st.secrets or "credentials" not in st.secrets["google"]:
            raise ValueError("✗ No se encontraron credenciales de Google en secrets")
        
        creds_info = json.loads(st.secrets["google"]["credentials"])
        
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
        
        creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Verificar que la conexión funciona
        logger.info("✓ Cliente de Google Sheets inicializado exitosamente")
        return client
        
    except json.JSONDecodeError as e:
        logger.error(f"✗ Error en formato JSON de credenciales: {e}")
        st.error("✗ Error en formato de credenciales JSON. Verifica secrets.toml")
        raise
    except Exception as e:
        logger.error(f"✗ Error inicializando cliente Google Sheets: {e}")
        st.error(f"✗ Error inicializando Google Sheets: {str(e)[:100]}")
        raise

# === FUNCIÓN DE CARGA DE CURSOS OPTIMIZADA ===
@st.cache_data(ttl=1800, show_spinner=False)  # 30 minutos de cache
@retry_with_backoff(max_retries=2, initial_delay=2)
@rate_limited(calls_per_minute=40)  # Más conservador que el límite real
def _load_courses_raw(clases_sheet_id: str) -> Dict[str, Any]:
    """
    Carga los cursos desde Google Sheets de forma segura y optimizada.
    Incluye manejo de errores por hoja y validación de datos.
    """
    if not clases_sheet_id:
        logger.error("✗ ID de hoja de clases no proporcionado")
        return {}
    
    try:
        client = _get_gsheets_client()
        spreadsheet = client.open_by_key(clases_sheet_id)
        worksheets = spreadsheet.worksheets()
        
        if not worksheets:
            logger.warning("△ No se encontraron hojas en el spreadsheet")
            return {}
        
        courses = {}
        successful_sheets = 0
        failed_sheets = 0
        
        for worksheet in worksheets:
            sheet_name = worksheet.title
            
            # Saltar hojas que no son cursos
            if sheet_name.upper() == "MAILS" or sheet_name.upper() == "CONFIG":
                continue
            
            try:
                # Obtener datos de forma eficiente (solo las columnas necesarias)
                all_data = worksheet.get_all_values()
                
                if not all_data or len(all_data) < 5:
                    logger.warning(f"△ Hoja '{sheet_name}' vacía o con formato incorrecto")
                    failed_sheets += 1
                    continue
                
                # Extraer metadatos del curso
                profesor = all_data[0][1] if len(all_data[0]) > 1 else "No asignado"
                sede = all_data[1][1] if len(all_data) > 1 and len(all_data[1]) > 1 else "No especificada"
                asignatura = all_data[2][1] if len(all_data) > 2 and len(all_data[2]) > 1 else "Sin asignatura"
                
                # Extraer estudiantes (filas 4-24, columna 0)
                estudiantes = []
                start_row = 4  # Fila donde empiezan los estudiantes
                end_row = min(24, len(all_data))
                
                for i in range(start_row, end_row):
                    if i < len(all_data) and all_data[i] and all_data[i][0].strip():
                        estudiante = all_data[i][0].strip()
                        if estudiante and estudiante.lower() not in ["nombre", "estudiante", "alumno"]:
                            estudiantes.append(estudiante)
                
                # Extraer fechas (filas 1-36, columna 0, después del header)
                fechas = []
                fecha_start_row = 1  # Ajustar según tu formato real
                fecha_end_row = min(36, len(all_data))
                
                for i in range(fecha_start_row, fecha_end_row):
                    if i < len(all_data) and all_data[i] and all_data[i][0].strip():
                        fecha = all_data[i][0].strip()
                        # Validar que sea una fecha (puedes ajustar esta validación)
                        if fecha and not fecha.lower() in ["fecha", "clase", "día"]:
                            fechas.append(fecha)
                
                # Validar que el curso tenga datos mínimos
                if not estudiantes:
                    logger.warning(f"△ Hoja '{sheet_name}' no tiene estudiantes")
                    failed_sheets += 1
                    continue
                
                # Almacenar datos del curso
                courses[sheet_name] = {
                    "profesor": profesor,
                    "sede": sede.upper() if sede else "NO ESPECIFICADA",
                    "asignatura": asignatura,
                    "estudiantes": estudiantes,
                    "fechas": fechas if fechas else ["Sin fechas programadas"],
                    "last_updated": datetime.now().isoformat()
                }
                
                successful_sheets += 1
                logger.debug(f"✓ Hoja '{sheet_name}' cargada: {len(estudiantes)} estudiantes, {len(fechas)} fechas")
                
            except Exception as e:
                failed_sheets += 1
                logger.warning(f"△ Error procesando hoja '{sheet_name}': {str(e)[:80]}")
                continue
        
        logger.info(f"✓ Cursos cargados: {successful_sheets} exitosos, {failed_sheets} fallados")
        return courses
        
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"✗ Spreadsheet no encontrado con ID: {clases_sheet_id}")
        st.error(f"✗ No se encontró la hoja de clases. Verifica el ID en secrets.toml")
        return {}
    except Exception as e:
        logger.error(f"✗ Error crítico cargando cursos: {str(e)}")
        if "quota" in str(e).lower() or "429" in str(e):
            st.error("⚠️ Límite de API de Google Sheets alcanzado. Espera unos minutos.")
        return {}

# === FUNCIÓN DE CARGA DE ASISTENCIA CON CACHÉ LARGO ===
@st.cache_data(ttl=3600, show_spinner=False)  # 1 hora de cache para asistencia
@retry_with_backoff(max_retries=2)
@rate_limited(calls_per_minute=35)
def _load_attendance_raw(asistencia_sheet_id: str, course_name: str = None) -> Dict[str, Dict[str, bool]]:
    """
    Carga datos de asistencia desde Google Sheets.
    Si se especifica course_name, carga solo ese curso.
    """
    if not asistencia_sheet_id:
        logger.error("✗ ID de hoja de asistencia no proporcionado")
        return {}
    
    try:
        client = _get_gsheets_client()
        spreadsheet = client.open_by_key(asistencia_sheet_id)
        asistencias = {}
        
        # Determinar qué hojas cargar
        sheets_to_load = []
        if course_name:
            sheets_to_load = [course_name]
        else:
            # Cargar todas las hojas excepto MAILS y configuraciones
            all_sheets = [ws.title for ws in spreadsheet.worksheets()]
            sheets_to_load = [sheet for sheet in all_sheets 
                            if sheet.upper() not in ["MAILS", "CONFIG", "METADATA"]]
        
        for sheet_name in sheets_to_load:
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                records = worksheet.get_all_records()
                
                if not records:
                    continue
                
                for record in records:
                    estudiante = str(record.get("Estudiante", "")).strip()
                    fecha = str(record.get("Fecha", "")).strip()
                    estado = record.get("Asistencia", 0)
                    
                    if estudiante and fecha:
                        if estudiante not in asistencias:
                            asistencias[estudiante] = {}
                        
                        # Convertir a booleano, manejando diferentes formatos
                        if isinstance(estado, bool):
                            asistencias[estudiante][fecha] = estado
                        elif isinstance(estado, (int, float)):
                            asistencias[estudiante][fecha] = bool(estado)
                        elif isinstance(estado, str):
                            estado_lower = estado.lower().strip()
                            asistencias[estudiante][fecha] = estado_lower in ["true", "1", "si", "sí", "presente", "p"]
                        else:
                            asistencias[estudiante][fecha] = False
                
                logger.debug(f"✓ Asistencia cargada para '{sheet_name}': {len(records)} registros")
                
            except gspread.exceptions.WorksheetNotFound:
                logger.debug(f"△ Hoja de asistencia '{sheet_name}' no encontrada")
                continue
            except Exception as e:
                logger.warning(f"△ Error cargando asistencia de '{sheet_name}': {str(e)[:60]}")
                continue
        
        return asistencias
        
    except Exception as e:
        logger.error(f"✗ Error cargando asistencia: {str(e)}")
        return {}

# === FUNCIÓN DE CARGA DE EMAILS OPTIMIZADA ===
@st.cache_data(ttl=3600, show_spinner=False)  # 1 hora de cache
@retry_with_backoff(max_retries=2)
@rate_limited(calls_per_minute=30)
def _load_emails_raw(asistencia_sheet_id: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Carga emails y nombres de apoderados desde la hoja MAILS.
    Retorna dos diccionarios: {estudiante: email}, {estudiante: nombre_apoderado}
    """
    if not asistencia_sheet_id:
        logger.error("✗ ID de hoja de asistencia no proporcionado para cargar emails")
        return {}, {}
    
    try:
        client = _get_gsheets_client()
        spreadsheet = client.open_by_key(asistencia_sheet_id)
        
        try:
            worksheet = spreadsheet.worksheet("MAILS")
        except gspread.exceptions.WorksheetNotFound:
            # Intentar con mayúsculas/minúsculas diferentes
            all_sheets = [ws.title.upper() for ws in spreadsheet.worksheets()]
            if "MAILS" in all_sheets or "CORREOS" in all_sheets:
                for ws in spreadsheet.worksheets():
                    if ws.title.upper() in ["MAILS", "CORREOS", "EMAILS"]:
                        worksheet = ws
                        break
                else:
                    logger.warning("△ No se encontró hoja de emails (MAILS)")
                    return {}, {}
            else:
                logger.warning("△ No se encontró hoja de emails (MAILS)")
                return {}, {}
        
        records = worksheet.get_all_records()
        
        emails = {}
        nombres_apoderados = {}
        emails_loaded = 0
        
        for record in records:
            estudiante = str(record.get("NOMBRE ESTUDIANTE", record.get("Estudiante", ""))).strip()
            apoderado = str(record.get("NOMBRE APODERADO", record.get("Apoderado", ""))).strip()
            email = str(record.get("MAIL APODERADO", record.get("Email", ""))).strip().lower()
            
            if estudiante and email and "@" in email:
                estudiante_key = estudiante.lower().strip()
                emails[estudiante_key] = email
                nombres_apoderados[estudiante_key] = apoderado if apoderado else "Apoderado/a"
                emails_loaded += 1
        
        logger.info(f"✓ Emails cargados: {emails_loaded} registros válidos")
        return emails, nombres_apoderados
        
    except Exception as e:
        logger.error(f"✗ Error cargando emails: {str(e)}")
        return {}, {}

# === MANAGER PRINCIPAL ===
class GoogleSheetsManager:
    """
    Manejador optimizado de Google Sheets con:
    - Rate limiting inteligente
    - Cache multi-nivel
    - Retry con backoff exponencial
    - Manejo robusto de errores
    """
    
    def __init__(self, debug_mode: bool = False):
        """Inicializa el manager con configuración opcional de debug."""
        self.debug_mode = debug_mode or st.secrets.get("DEBUG", False)
        self._sheet_ids_cache = None
        self._courses_cache = {}
        self._attendance_cache = {}
        
        if self.debug_mode:
            logger.setLevel(logging.DEBUG)
            logger.debug("✓ GoogleSheetsManager en modo debug")
    
    def get_sheet_ids(self) -> Dict[str, str]:
        """Obtiene IDs de hojas desde secrets con cache local."""
        if self._sheet_ids_cache is not None:
            return self._sheet_ids_cache
        
        try:
            sheet_ids = {
                "asistencia": st.secrets["google"]["asistencia_sheet_id"],
                "clases": st.secrets["google"]["clases_sheet_id"]
            }
            self._sheet_ids_cache = sheet_ids
            return sheet_ids
        except KeyError as e:
            logger.error(f"✗ Secret no encontrado: {e}")
            st.error(f"✗ Configuración incompleta en secrets.toml. Falta: {e}")
            return {}
    
    def load_courses(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Carga todos los cursos desde Google Sheets.
        
        Args:
            force_refresh: Si True, ignora el cache y recarga desde la API
            
        Returns:
            Diccionario con {nombre_curso: datos_curso}
        """
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "clases" not in sheet_ids:
                return {}
            
            clases_sheet_id = sheet_ids["clases"]
            
            # Forzar refresh si se solicita
            if force_refresh:
                st.cache_data.clear()
                self._courses_cache = {}
                logger.info("✓ Cache de cursos limpiado (force refresh)")
            
            # Usar función con cache
            courses = _load_courses_raw(clases_sheet_id)
            
            if self.debug_mode:
                logger.debug(f"Cursos cargados: {len(courses)}")
                for name, data in list(courses.items())[:3]:  # Mostrar solo 3
                    logger.debug(f"  - {name}: {len(data.get('estudiantes', []))} estudiantes")
            
            return courses
            
        except Exception as e:
            logger.error(f"✗ Error en load_courses: {str(e)}")
            
            # Si hay cache anterior, devolverlo como fallback
            if self._courses_cache:
                logger.warning("△ Usando cache anterior debido a error")
                return self._courses_cache
            
            return {}
    
    def load_courses_for_teacher(self, teacher_name: str) -> Dict[str, Any]:
        """
        Carga cursos filtrados por profesor.
        
        Args:
            teacher_name: Nombre del profesor
            
        Returns:
            Diccionario con cursos del profesor
        """
        try:
            all_courses = self.load_courses()
            if not all_courses:
                return {}
            
            # Filtrar por profesor (búsqueda case-insensitive)
            teacher_courses = {}
            teacher_lower = teacher_name.lower().strip()
            
            for name, data in all_courses.items():
                profesor = data.get("profesor", "").lower().strip()
                if profesor == teacher_lower:
                    teacher_courses[name] = data
            
            logger.debug(f"Cursos para profesor '{teacher_name}': {len(teacher_courses)}")
            return teacher_courses
            
        except Exception as e:
            logger.error(f"✗ Error cargando cursos para profesor: {str(e)}")
            return {}
    
    def load_courses_by_sede(self, sede_nombre: str, include_attendance: bool = True) -> Dict[str, Any]:
        """
        Carga cursos filtrados por sede.
        
        Args:
            sede_nombre: Nombre de la sede (ej: "SAN PEDRO")
            include_attendance: Si True, incluye datos de asistencia
            
        Returns:
            Diccionario con cursos de la sede
        """
        try:
            all_courses = self.load_courses()
            if not all_courses:
                return {}
            
            sede_upper = sede_nombre.upper().strip()
            sede_courses = {}
            
            for name, data in all_courses.items():
                if data.get("sede", "").upper() == sede_upper:
                    # Copiar datos para no modificar el cache original
                    curso_data = data.copy()
                    
                    # Cargar asistencia si se solicita
                    if include_attendance:
                        curso_data["asistencias"] = self.load_attendance_for_course(name)
                    
                    sede_courses[name] = curso_data
            
            logger.info(f"Cursos para sede '{sede_nombre}': {len(sede_courses)}")
            return sede_courses
            
        except Exception as e:
            logger.error(f"✗ Error cargando cursos por sede: {str(e)}")
            return {}
    
    def load_attendance_for_course(self, course_name: str) -> Dict[str, Dict[str, bool]]:
        """
        Carga datos de asistencia para un curso específico.
        
        Args:
            course_name: Nombre del curso
            
        Returns:
            Diccionario anidado {estudiante: {fecha: asistencia}}
        """
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}
            
            asistencia_sheet_id = sheet_ids["asistencia"]
            
            # Verificar cache local primero
            cache_key = f"{asistencia_sheet_id}_{course_name}"
            if cache_key in self._attendance_cache:
                return self._attendance_cache[cache_key]
            
            # Cargar desde API con cache
            asistencias = _load_attendance_raw(asistencia_sheet_id, course_name)
            
            # Almacenar en cache local
            self._attendance_cache[cache_key] = asistencias
            
            return asistencias
            
        except Exception as e:
            logger.error(f"✗ Error cargando asistencia para '{course_name}': {str(e)}")
            return {}
    
    def save_attendance(self, course_name: str, fecha: str, 
                       attendance_data: Dict[str, bool], user: str) -> bool:
        """
        Guarda datos de asistencia en Google Sheets.
        NOTA: Las operaciones de escritura NO usan cache.
        
        Args:
            course_name: Nombre del curso
            fecha: Fecha de la clase
            attendance_data: Diccionario {estudiante: presente}
            user: Usuario que registra la asistencia
            
        Returns:
            True si se guardó exitosamente, False en caso contrario
        """
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                logger.error("✗ No hay ID de hoja de asistencia configurado")
                return False
            
            client = _get_gsheets_client()
            spreadsheet = client.open_by_key(sheet_ids["asistencia"])
            
            # Intentar acceder a la hoja del curso
            try:
                worksheet = spreadsheet.worksheet(course_name)
            except gspread.exceptions.WorksheetNotFound:
                # Crear nueva hoja si no existe
                logger.info(f"△ Creando nueva hoja para curso: {course_name}")
                worksheet = spreadsheet.add_worksheet(
                    title=course_name, 
                    rows=1000, 
                    cols=10
                )
                # Agregar encabezados
                worksheet.append_row([
                    "Curso", "Fecha", "Estudiante", 
                    "Asistencia", "Timestamp", "Usuario"
                ])
            
            # Preparar datos para guardar
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows_to_append = []
            
            for estudiante, presente in attendance_data.items():
                rows_to_append.append([
                    course_name,
                    fecha,
                    estudiante,
                    1 if presente else 0,
                    timestamp,
                    user
                ])
            
            # Guardar en lotes para evitar timeouts
            batch_size = 50
            for i in range(0, len(rows_to_append), batch_size):
                batch = rows_to_append[i:i + batch_size]
                worksheet.append_rows(batch)
                time.sleep(0.1)  # Pequeña pausa entre lotes
            
            # Invalidar cache de asistencia para este curso
            cache_key = f"{sheet_ids['asistencia']}_{course_name}"
            if cache_key in self._attendance_cache:
                del self._attendance_cache[cache_key]
            
            # Invalidar cache global de cursos
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
            
            logger.info(f"✓ Asistencia guardada para '{course_name}': {len(rows_to_append)} registros")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error guardando asistencia: {str(e)}")
            return False
    
    def load_emails(self) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        Carga emails de apoderados desde la hoja MAILS.
        
        Returns:
            Tupla con (emails_dict, nombres_apoderados_dict)
        """
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}, {}
            
            return _load_emails_raw(sheet_ids["asistencia"])
            
        except Exception as e:
            logger.error(f"✗ Error cargando emails: {str(e)}")
            return {}, {}
    
    def get_all_emails_by_sede(self, sede_nombre: str) -> List[Dict[str, str]]:
        """
        Obtiene todos los emails de una sede específica.
        
        Args:
            sede_nombre: Nombre de la sede
            
        Returns:
            Lista de diccionarios con información de contacto
        """
        try:
            sede_courses = self.load_courses_by_sede(sede_nombre, include_attendance=False)
            emails_data, _ = self.load_emails()
            
            if not sede_courses or not emails_data:
                return []
            
            result = []
            
            for course_name, course_data in sede_courses.items():
                for estudiante in course_data.get("estudiantes", []):
                    estudiante_key = estudiante.strip().lower()
                    
                    if estudiante_key in emails_data:
                        result.append({
                            "estudiante": estudiante,
                            "email": emails_data[estudiante_key],
                            "curso": course_name,
                            "sede": sede_nombre
                        })
            
            logger.debug(f"Emails para sede '{sede_nombre}': {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"✗ Error obteniendo emails por sede: {str(e)}")
            return []
    
    def get_low_attendance_students(self, sede_nombre: str, 
                                   threshold: float = 70.0) -> List[Dict[str, Any]]:
        """
        Obtiene estudiantes con baja asistencia en una sede.
        
        Args:
            sede_nombre: Nombre de la sede
            threshold: Umbral de porcentaje de asistencia (por debajo es baja)
            
        Returns:
            Lista de estudiantes con baja asistencia
        """
        try:
            sede_courses = self.load_courses_by_sede(sede_nombre, include_attendance=True)
            
            if not sede_courses:
                return []
            
            low_students = []
            emails_data, _ = self.load_emails()
            
            for course_name, course_data in sede_courses.items():
                total_fechas = len(course_data.get("fechas", []))
                
                if total_fechas == 0:
                    continue
                
                asistencias = course_data.get("asistencias", {})
                
                for estudiante, att_data in asistencias.items():
                    presentes = sum(1 for estado in att_data.values() if estado)
                    porcentaje = (presentes / total_fechas) * 100 if total_fechas > 0 else 0
                    
                    if porcentaje < threshold:
                        estudiante_key = estudiante.strip().lower()
                        email = emails_data.get(estudiante_key, "No registrado")
                        
                        low_students.append({
                            "estudiante": estudiante,
                            "curso": course_name,
                            "porcentaje": round(porcentaje, 1),
                            "presentes": presentes,
                            "total_clases": total_fechas,
                            "email": email
                        })
            
            # Ordenar por menor porcentaje primero
            low_students.sort(key=lambda x: x["porcentaje"])
            
            logger.info(f"Estudiantes con baja asistencia (<{threshold}%): {len(low_students)}")
            return low_students
            
        except Exception as e:
            logger.error(f"✗ Error obteniendo estudiantes con baja asistencia: {str(e)}")
            return []
    
    def clear_cache(self):  # <-- CORREGIDO: sin parámetros
        """
        Limpia los caches del manager.
        """
        try:
            self._courses_cache = {}
            self._attendance_cache = {}
            self._sheet_ids_cache = None
            
            # Limpiar cache de Streamlit
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
                logger.debug("✓ Cache de Streamlit limpiado")
            
            logger.info("✓ Cache del manager limpiado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error limpiando cache: {str(e)}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Prueba la conexión con Google Sheets y verifica el acceso a las hojas.
        
        Returns:
            Diccionario con resultados de la prueba
        """
        results = {
            "client": "❓ No probado",
            "clases_sheet": "❓ No probado",
            "asistencia_sheet": "❓ No probado",
            "emails_sheet": "❓ No probado",
            "cursos_count": 0,
            "errors": []
        }
        
        try:
            # Probar cliente
            client = _get_gsheets_client()
            results["client"] = "✅ Conectado"
            
            # Probar hojas
            sheet_ids = self.get_sheet_ids()
            
            if sheet_ids.get("clases"):
                try:
                    spreadsheet = client.open_by_key(sheet_ids["clases"])
                    worksheets = [ws.title for ws in spreadsheet.worksheets()]
                    results["clases_sheet"] = f"✅ Accesible ({len(worksheets)} hojas)"
                    results["cursos_count"] = len([ws for ws in worksheets if ws.upper() != "MAILS"])
                except Exception as e:
                    results["clases_sheet"] = f"❌ Error: {str(e)[:50]}"
                    results["errors"].append(f"Clases: {str(e)}")
            
            if sheet_ids.get("asistencia"):
                try:
                    spreadsheet = client.open_by_key(sheet_ids["asistencia"])
                    results["asistencia_sheet"] = "✅ Accesible"
                    
                    # Verificar hoja MAILS
                    try:
                        spreadsheet.worksheet("MAILS")
                        results["emails_sheet"] = "✅ Encontrada"
                    except:
                        results["emails_sheet"] = "⚠️ No encontrada"
                        
                except Exception as e:
                    results["asistencia_sheet"] = f"❌ Error: {str(e)[:50]}"
                    results["errors"].append(f"Asistencia: {str(e)}")
            
            return results
            
        except Exception as e:
            results["client"] = f"❌ Error: {str(e)[:50]}"
            results["errors"].append(f"Cliente: {str(e)}")
            return results

# Función helper para uso rápido
def get_sheets_manager() -> GoogleSheetsManager:
    """
    Retorna una instancia de GoogleSheetsManager configurada.
    Útil para importaciones rápidas.
    """
    return GoogleSheetsManager()