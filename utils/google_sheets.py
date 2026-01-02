# utils/google_sheets.py
import gspread
import pandas as pd
import json
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict, List, Optional, Any
import time
import random
from gspread.exceptions import APIError, WorksheetNotFound

# =============================================
# FUNCIÓN AUXILIAR CACHABLE (fuera de la clase)
# =============================================
@st.cache_data(ttl=1800)  # 30 minutos - datos de cursos son estáticos
def _load_courses_raw(clases_sheet_id: str, credentials_json: str):
    """Carga todos los cursos desde el sheet de clases - función pura para caching"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(json.loads(credentials_json), scopes=scopes)
    client = gspread.authorize(creds)
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
            print(f"⚠️ Error en hoja {sheet_name}: {str(e)[:50]}")
            continue
    return courses


# =============================================
# FUNCIÓN CACHABLE PARA EMAILS
# =============================================
@st.cache_data(ttl=3600)  # 1 hora - emails cambian muy poco
def _load_emails_cached(asistencia_sheet_id: str, credentials_json: str):
    """Carga emails de apoderados desde hoja MAILS - función pura"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(json.loads(credentials_json), scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(asistencia_sheet_id)
    
    try:
        mails_sheet = sheet.worksheet("MAILS")
    except WorksheetNotFound:
        return {}, {}
    
    data = mails_sheet.get_all_records()
    emails = {}
    nombres_apoderados = {}
    
    for row in data:
        estudiante = str(row.get("NOMBRE ESTUDIANTE", "")).strip().lower()
        apoderado = str(row.get("NOMBRE APODERADO", "")).strip()
        mail_apoderado = str(row.get("MAIL APODERADO", "")).strip()
        
        if estudiante and mail_apoderado and "@" in mail_apoderado:
            emails[estudiante] = mail_apoderado
            nombres_apoderados[estudiante] = apoderado
    
    return emails, nombres_apoderados


class GoogleSheetsManager:
    """Manejador de conexión con Google Sheets - OPTIMIZADO y SIN ERRORES DE HASHING"""

    _client = None  # Singleton para reutilizar conexión

    def __init__(self):
        if GoogleSheetsManager._client is None:
            self._init_client()

    def _init_client(self, max_retries: int = 3):
        """Inicialización con retry y backoff exponencial"""
        for attempt in range(max_retries):
            try:
                if "google" not in st.secrets or "credentials" not in st.secrets["google"]:
                    raise ValueError("❌ No se encontraron credenciales de Google en secrets")
                
                creds_info = json.loads(st.secrets["google"]["credentials"])
                scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
                GoogleSheetsManager._client = gspread.authorize(creds)
                return
                
            except json.JSONDecodeError:
                st.error("❌ Error: Las credenciales de Google no tienen formato JSON válido")
                return
            except APIError as e:
                if "Quota" in str(e) or "Rate limit" in str(e):
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(sleep_time)
                else:
                    st.error(f"❌ Error Google API: {str(e)[:100]}")
                    return
            except Exception as e:
                st.error(f"❌ Error inicializando cliente (intento {attempt+1}): {str(e)[:100]}")
                if attempt == max_retries - 1:
                    return
                time.sleep(2 ** attempt)

    @property
    def client(self):
        if GoogleSheetsManager._client is None:
            self._init_client()
        return GoogleSheetsManager._client

    def get_sheet_ids(self) -> Dict[str, str]:
        try:
            return {
                "asistencia": st.secrets["google"]["asistencia_sheet_id"],
                "clases": st.secrets["google"]["clases_sheet_id"]
            }
        except KeyError as e:
            st.error(f"❌ No se encontró el ID de hoja en secrets: {e}")
            return {}

    # ====================== CURSOS ======================
    @st.cache_data(ttl=1800)
    def load_courses(self) -> Dict[str, Any]:
        """Carga todos los cursos usando función auxiliar cacheada"""
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "clases" not in sheet_ids:
                return {}
            credentials_json = st.secrets["google"]["credentials"]
            return _load_courses_raw(sheet_ids["clases"], credentials_json)
        except Exception as e:
            st.error(f"❌ Error cargando cursos: {str(e)[:100]}")
            return {}

    def load_courses_for_teacher(self, teacher_name: str) -> Dict[str, Any]:
        all_courses = self.load_courses()
        return {name: data for name, data in all_courses.items() 
                if teacher_name.lower() in data["profesor"].lower()}

    @st.cache_data(ttl=1800)
    def load_courses_by_sede(self, _manager, sede_nombre: str) -> Dict[str, Any]:
        """
        Carga cursos por sede.
        Nota: _manager es un truco para evitar hashing de 'self' - no se usa dentro.
        """
        try:
            sheet_ids = self.get_sheet_ids()  # 'self' sigue accesible porque es método de instancia
            if not sheet_ids or "clases" not in sheet_ids:
                return {}
            credentials_json = st.secrets["google"]["credentials"]
            all_courses = _load_courses_raw(sheet_ids["clases"], credentials_json)
            
            sede_courses = {}
            for name, data in all_courses.items():
                if data.get("sede", "").strip().upper() == sede_nombre.strip().upper():
                    data["asistencias"] = self.load_attendance_for_course(name)
                    sede_courses[name] = data
            return sede_courses
        except Exception as e:
            st.error(f"❌ Error cargando cursos por sede {sede_nombre}: {str(e)[:100]}")
            return {}

    # Wrapper para llamar sin pasar _manager manualmente
    def load_courses_by_sede_wrapper(self, sede_nombre: str) -> Dict[str, Any]:
        return self.load_courses_by_sede(self, sede_nombre)

    # ====================== ASISTENCIA ======================
    def load_attendance_for_course(self, course_name: str) -> Dict[str, Dict[str, bool]]:
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids or not self.client:
                return {}
            
            sheet = self.client.open_by_key(sheet_ids["asistencia"])
            try:
                asistencia_sheet = sheet.worksheet("ASISTENCIA_HISTORICA")
            except WorksheetNotFound:
                try:
                    asistencia_sheet = sheet.worksheet(course_name)
                except WorksheetNotFound:
                    return {}

            data = asistencia_sheet.get_all_records()
            asistencias = {}
            for row in data:
                estudiante = str(row.get("Estudiante", "")).strip()
                fecha = str(row.get("Fecha", "")).strip()
                estado = row.get("Asistencia", 0)
                if estudiante and fecha:
                    if estudiante not in asistencias:
                        asistencias[estudiante] = {}
                    asistencias[estudiante][fecha] = bool(estado)
            return asistencias
        except Exception as e:
            print(f"⚠️ Error cargando asistencia para {course_name}: {e}")
            return {}

    def save_attendance(self, course_name: str, fecha: str, attendance_data: Dict[str, bool], user: str) -> bool:
        for attempt in range(3):
            try:
                sheet_ids = self.get_sheet_ids()
                if not sheet_ids or "asistencia" not in sheet_ids or not self.client:
                    return False
                
                sheet = self.client.open_by_key(sheet_ids["asistencia"])
                try:
                    worksheet = sheet.worksheet(course_name)
                except WorksheetNotFound:
                    worksheet = sheet.add_worksheet(title=course_name, rows=1000, cols=6)
                    worksheet.append_row(["Curso", "Fecha", "Estudiante", "Asistencia", "Timestamp", "Usuario"])

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                rows = [[course_name, fecha, est, 1 if pres else 0, timestamp, user] 
                        for est, pres in attendance_data.items()]
                
                worksheet.append_rows(rows)
                st.success(f"✅ Asistencia guardada para {course_name}")
                return True
                
            except APIError as e:
                if "Quota" in str(e):
                    time.sleep(2 ** attempt)
                    continue
                st.error(f"❌ Error guardando: {str(e)[:100]}")
                return False
            except Exception as e:
                if attempt == 2:
                    st.error(f"❌ Error final guardando asistencia: {str(e)[:100]}")
                    return False
                time.sleep(1)
        return False

    # ====================== EMAILS ======================
    def load_emails(self) -> tuple[Dict[str, str], Dict[str, str]]:
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}, {}
            credentials_json = st.secrets["google"]["credentials"]
            return _load_emails_cached(sheet_ids["asistencia"], credentials_json)
        except Exception as e:
            st.error(f"❌ Error cargando emails: {str(e)[:100]}")
            return {}, {}

    def get_all_emails_by_sede(self, sede_nombre: str) -> List[Dict[str, str]]:
        try:
            sede_courses = self.load_courses_by_sede_wrapper(sede_nombre)
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
            st.error(f"❌ Error emails por sede: {str(e)[:100]}")
            return []

    def get_low_attendance_students(self, sede_nombre: str, threshold: float = 70.0) -> List[Dict[str, Any]]:
        try:
            sede_courses = self.load_courses_by_sede_wrapper(sede_nombre)
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
                        email = emails_data.get(estudiante.strip().lower(), "No registrado")
                        low_students.append({
                            "estudiante": estudiante,
                            "curso": course_name,
                            "porcentaje": round(porcentaje, 1),
                            "presentes": presentes,
                            "total_clases": total_fechas,
                            "email": email
                        })
            low_students.sort(key=lambda x: x["porcentaje"])
            return low_students
        except Exception as e:
            st.error(f"❌ Error baja asistencia: {str(e)[:100]}")
            return []