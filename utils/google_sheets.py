# utils/google_sheets.py
import gspread
import pandas as pd
import json
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
from functools import wraps

# === DECORADOR DE RATE LIMITING ===
def rate_limited(calls_per_minute=55):
    """Limita las llamadas a la API para evitar el error 429."""
    min_interval = 60.0 / calls_per_minute
    def decorator(func):
        last_called = [0.0]
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

# === CLIENTE CON CACHÉ A NIVEL DE RECURSO ===
@st.cache_resource
def _get_gsheets_client():
    """Inicializa y almacena en caché el cliente de Google Sheets."""
    if "google" not in st.secrets or "credentials" not in st.secrets["google"]:
        raise ValueError("❌ No se encontraron credenciales de Google en secrets")
    creds_info = json.loads(st.secrets["google"]["credentials"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)

# === FUNCIÓN DE CARGA DE CURSOS CON CACHÉ Y RATE LIMITING ===
@st.cache_data(ttl=900)  # 15 minutos
@rate_limited(calls_per_minute=55)
def _load_courses_raw(clases_sheet_id: str):
    """Carga los cursos desde Google Sheets de forma segura y optimizada."""
    client = _get_gsheets_client()
    sheet = client.open_by_key(clases_sheet_id)
    courses = {}

    for worksheet in sheet.worksheets():
        sheet_name = worksheet.title
        if sheet_name == "MAILS":
            continue
        try:
            all_data = worksheet.get_all_values()
            profesor = all_data[0][1] if len(all_data) > 0 and len(all_data[0]) > 1 else ""
            sede = all_data[1][1] if len(all_data) > 1 and len(all_data[1]) > 1 else ""
            asignatura = all_data[2][1] if len(all_data) > 2 and len(all_data[2]) > 1 else ""

            estudiantes = []
            for i in range(44, min(64, len(all_data))):
                if i < len(all_data) and all_data[i] and all_data[i][0].strip():
                    estudiantes.append(all_data[i][0].strip())

            fechas = []
            for i in range(8, min(43, len(all_data))):
                if i < len(all_data) and all_data[i] and all_data[i][0].strip():
                    fechas.append(all_data[i][0].strip())

            if estudiantes:
                courses[sheet_name] = {
                    "profesor": profesor,
                    "sede": sede,
                    "asignatura": asignatura,
                    "estudiantes": estudiantes,
                    "fechas": fechas if fechas else ["Sin fechas"]
                }
        except Exception as e:
            st.warning(f"⚠️ Error en hoja '{sheet_name}': {str(e)[:50]}")
            continue
    return courses

# === MANAGER PRINCIPAL ===
class GoogleSheetsManager:
    """Manejador optimizado de Google Sheets con rate limiting y caché."""

    def __init__(self):
        # El cliente se inicializa vía _get_gsheets_client() (caché a nivel de recurso)
        pass

    def get_sheet_ids(self) -> Dict[str, str]:
        try:
            return {
                "asistencia": st.secrets["google"]["asistencia_sheet_id"],
                "clases": st.secrets["google"]["clases_sheet_id"]
            }
        except KeyError as e:
            st.error(f"❌ No se encontró el ID de hoja en secrets: {e}")
            return {}

    def load_courses(self) -> Dict[str, Any]:
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "clases" not in sheet_ids:
                return {}
            return _load_courses_raw(sheet_ids["clases"])
        except Exception as e:
            st.error(f"❌ Error cargando cursos: {e}")
            return {}

    def load_courses_for_teacher(self, teacher_name: str) -> Dict[str, Any]:
        all_courses = self.load_courses()
        return {name: data for name, data in all_courses.items() if data["profesor"] == teacher_name}

    def load_courses_by_sede(self, sede_nombre: str) -> Dict[str, Any]:
        try:
            all_courses = self.load_courses()
            sede_courses = {}
            for name, data in all_courses.items():
                if data.get("sede", "").upper() == sede_nombre.upper():
                    # Cargar asistencia para cada curso (usa su propia caché si se implementa)
                    data["asistencias"] = self.load_attendance_for_course(name)
                    sede_courses[name] = data
            return sede_courses
        except Exception as e:
            st.error(f"❌ Error cargando cursos por sede: {e}")
            return {}

    def load_attendance_for_course(self, course_name: str) -> Dict[str, Dict[str, bool]]:
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}
            client = _get_gsheets_client()
            sheet = client.open_by_key(sheet_ids["asistencia"])
            try:
                asistencia_sheet = sheet.worksheet("ASISTENCIA_HISTORICA")
            except gspread.exceptions.WorksheetNotFound:
                try:
                    asistencia_sheet = sheet.worksheet(course_name)
                except gspread.exceptions.WorksheetNotFound:
                    return {}

            data = asistencia_sheet.get_all_records()
            asistencias = {}
            for row in data:
                estudiante = str(row.get("Estudiante", "")).strip()
                fecha = str(row.get("Fecha", "")).strip()
                estado = row.get("Asistencia", 0)
                if estudiante:
                    if estudiante not in asistencias:
                        asistencias[estudiante] = {}
                    asistencias[estudiante][fecha] = bool(estado)
            return asistencias
        except Exception as e:
            st.warning(f"⚠️ Error cargando asistencia para {course_name}: {e}")
            return {}

    def save_attendance(self, course_name: str, fecha: str, attendance_data: Dict[str, bool], user: str) -> bool:
        # Las operaciones de escritura NO usan caché ni rate limiting (son menos frecuentes)
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return False
            client = _get_gsheets_client()
            sheet = client.open_by_key(sheet_ids["asistencia"])
            try:
                worksheet = sheet.worksheet(course_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=course_name, rows=1000, cols=6)
                worksheet.append_row(["Curso", "Fecha", "Estudiante", "Asistencia", "Timestamp", "Usuario"])

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows = []
            for estudiante, presente in attendance_data.items():
                rows.append([course_name, fecha, estudiante, 1 if presente else 0, timestamp, user])
            worksheet.append_rows(rows)
            return True
        except Exception as e:
            st.error(f"❌ Error guardando asistencia: {e}")
            return False

    @st.cache_data(ttl=900)  # 15 minutos
    @rate_limited(calls_per_minute=55)
    def load_emails(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Carga emails con caché y rate limiting para evitar errores 429."""
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}, {}
            client = _get_gsheets_client()
            sheet = client.open_by_key(sheet_ids["asistencia"])
            try:
                mails_sheet = sheet.worksheet("MAILS")
            except:
                return {}, {}
            data = mails_sheet.get_all_records()
            emails = {}
            nombres_apoderados = {}
            for row in data:
                estudiante = str(row.get("NOMBRE ESTUDIANTE", "")).strip().lower()
                apoderado = str(row.get("NOMBRE APODERADO", "")).strip()
                mail_apoderado = str(row.get("MAIL APODERADO", "")).strip()
                if estudiante and mail_apoderado:
                    emails[estudiante] = mail_apoderado
                    nombres_apoderados[estudiante] = apoderado
            return emails, nombres_apoderados
        except Exception as e:
            st.error(f"❌ Error cargando emails: {e}")
            return {}, {}

        @st.cache_data(ttl=900)  # 15 minutos
        @rate_limited(calls_per_minute=55)
        def get_all_emails_by_sede(self, sede_nombre: str) -> List[Dict[str, str]]:
            """Obtiene todos los emails de la sede con caché y rate limiting."""
            try:
                sede_courses = self.load_courses_by_sede(sede_nombre)
                emails_data, _ = self.load_emails()
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
                return result
            except Exception as e:
                st.error(f"❌ Error obteniendo emails por sede: {e}")
                return []

    @st.cache_data(ttl=900)  # 15 minutos
    @rate_limited(calls_per_minute=55)
    def get_low_attendance_students(self, sede_nombre: str, threshold: float = 70.0) -> List[Dict[str, Any]]:
        """Carga estudiantes con baja asistencia con caché y rate limiting."""
        try:
            sede_courses = self.load_courses_by_sede(sede_nombre)
            low_students = []
            for course_name, course_data in sede_courses.items():
                total_fechas = len(course_data.get("fechas", []))
                if total_fechas == 0:
                    continue
                asistencias = course_data.get("asistencias", {})
                for estudiante, att_data in asistencias.items():
                    presentes = sum(1 for estado in att_data.values() if estado)
                    porcentaje = (presentes / total_fechas) * 100 if total_fechas > 0 else 0
                    if porcentaje < threshold:
                        emails_data, _ = self.load_emails()
                        estudiante_key = estudiante.strip().lower()
                        email = emails_data.get(estudiante_key)
                        low_students.append({
                            "estudiante": estudiante,
                            "curso": course_name,
                            "porcentaje": round(porcentaje, 1),
                            "presentes": presentes,
                            "total_clases": total_fechas,
                            "email": email if email else "No registrado"
                        })
            low_students.sort(key=lambda x: x["porcentaje"])
            return low_students
        except Exception as e:
            st.error(f"❌ Error obteniendo estudiantes con baja asistencia: {e}")
            return []