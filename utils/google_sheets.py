import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

class GoogleSheetsManager:
    """Manejador de conexión con Google Sheets usando secrets de Streamlit"""
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Inicializa el cliente de Google Sheets usando secrets"""
        try:
            # Obtener credenciales de secrets de Streamlit
            if "google" not in st.secrets or "credentials" not in st.secrets["google"]:
                raise ValueError("❌ No se encontraron credenciales de Google en secrets")
            
            # Parsear credenciales JSON desde secrets
            creds_info = json.loads(st.secrets["google"]["credentials"])
            
            # Configurar scopes
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Crear credenciales
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
            
            # Crear cliente
            self.client = gspread.authorize(creds)
            
            return True
            
        except json.JSONDecodeError:
            st.error("❌ Error: Las credenciales de Google no tienen formato JSON válido")
            return False
        except Exception as e:
            st.error(f"❌ Error inicializando cliente de Google Sheets: {e}")
            return False
    
    def get_sheet_ids(self) -> Dict[str, str]:
        """Obtiene los IDs de las hojas desde secrets"""
        try:
            return {
                "asistencia": st.secrets["google"]["asistencia_sheet_id"],
                "clases": st.secrets["google"]["clases_sheet_id"]
            }
        except KeyError as e:
            st.error(f"❌ No se encontró el ID de hoja en secrets: {e}")
            return {}
    
    def load_courses(self) -> Dict[str, Any]:
        """Carga todos los cursos desde Google Sheets"""
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "clases" not in sheet_ids:
                return {}
            
            sheet = self.client.open_by_key(sheet_ids["clases"])
            courses = {}
            
            for worksheet in sheet.worksheets():
                # Saltar hojas que no son cursos
                sheet_name = worksheet.title
                if sheet_name in ["MAILS"]:
                    continue
                
                try:
                    all_data = worksheet.get_all_values()
                    
                    # Nueva estructura (filas específicas)
                    profesor = all_data[0][1] if len(all_data) > 1 else ""
                    sede = all_data[1][1] if len(all_data) > 1 and len(all_data[1]) > 1 else ""
                    asignatura = all_data[2][1] if len(all_data) > 1 and len(all_data[1]) > 2 else ""
                    
                    # Estudiantes (A45:A64)
                    estudiantes = []
                    for i in range(44, 64):
                        if i < len(all_data) and all_data[i]:
                            estudiante = all_data[i][0].strip()
                            if estudiante:
                                estudiantes.append(estudiante)
                    
                    # Fechas (A9:A43)
                    fechas = []
                    for i in range(8, 43):
                        if i < len(all_data) and all_data[i]:
                            fecha = all_data[i][0].strip()
                            if fecha:
                                fechas.append(fecha)
                    
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
            
        except Exception as e:
            st.error(f"❌ Error cargando cursos: {e}")
            return {}
    
    def load_courses_for_teacher(self, teacher_name: str) -> Dict[str, Any]:
        """Carga cursos específicos para un profesor"""
        all_courses = self.load_courses()
        
        # Filtrar cursos por profesor
        teacher_courses = {}
        for course_name, course_data in all_courses.items():
            if course_data["profesor"] == teacher_name:
                teacher_courses[course_name] = course_data
        
        return teacher_courses
    
    def load_courses_by_sede(self, sede_nombre: str) -> Dict[str, Any]:
        """Carga todos los cursos de una sede específica"""
        try:
            all_courses = self.load_courses()
            sede_courses = {}
            
            for course_name, course_data in all_courses.items():
                if course_data.get("sede", "").upper() == sede_nombre.upper():
                    # Enriquecer con datos de asistencia
                    course_data["asistencias"] = self.load_attendance_for_course(course_name)
                    sede_courses[course_name] = course_data
            
            return sede_courses
            
        except Exception as e:
            st.error(f"❌ Error cargando cursos por sede: {e}")
            return {}
    
    def load_attendance_for_course(self, course_name: str) -> Dict[str, Dict[str, bool]]:
        """Carga datos de asistencia para un curso específico"""
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}
            
            sheet = self.client.open_by_key(sheet_ids["asistencia"])
            
            try:
                # Buscar en hoja de asistencia histórica
                asistencia_sheet = sheet.worksheet("ASISTENCIA_HISTORICA")
                data = asistencia_sheet.get_all_records()
                
                asistencias = {}
                for row in data:
                    if str(row.get("Curso", "")).strip() == course_name:
                        estudiante = str(row.get("Estudiante", "")).strip()
                        fecha = str(row.get("Fecha", ""))
                        estado = row.get("Asistencia", 0)
                        
                        if estudiante not in asistencias:
                            asistencias[estudiante] = {}
                        
                        asistencias[estudiante][fecha] = bool(estado)
                
                return asistencias
                
            except gspread.exceptions.WorksheetNotFound:
                # Si no existe la hoja, buscar en cualquier hoja con el nombre del curso
                try:
                    curso_sheet = sheet.worksheet(course_name)
                    data = curso_sheet.get_all_records()
                    
                    asistencias = {}
                    for row in data:
                        estudiante = str(row.get("Estudiante", "")).strip()
                        fecha = str(row.get("Fecha", ""))
                        estado = row.get("Asistencia", 0)
                        
                        if estudiante not in asistencias:
                            asistencias[estudiante] = {}
                        
                        asistencias[estudiante][fecha] = bool(estado)
                    
                    return asistencias
                    
                except gspread.exceptions.WorksheetNotFound:
                    return {}
                    
        except Exception as e:
            print(f"⚠️ Error cargando asistencia para {course_name}: {e}")
            return {}
    
    def get_all_emails_by_sede(self, sede_nombre: str) -> List[Dict[str, str]]:
        """Obtener todos los emails de apoderados de una sede"""
        try:
            # Primero cargar todos los cursos de la sede
            sede_courses = self.load_courses_by_sede(sede_nombre)
            
            # Cargar emails de la hoja MAILS
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
    
    def get_low_attendance_students(self, sede_nombre: str, threshold: float = 70.0) -> List[Dict[str, Any]]:
        """Obtener estudiantes con baja asistencia (< threshold%)"""
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
                        # Buscar email
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
            
            # Ordenar por menor porcentaje
            low_students.sort(key=lambda x: x["porcentaje"])
            
            return low_students
            
        except Exception as e:
            st.error(f"❌ Error obteniendo estudiantes con baja asistencia: {e}")
            return []
    
    def save_attendance(self, course_name: str, fecha: str, 
                       attendance_data: Dict[str, bool], 
                       user: str) -> bool:
        """Guarda datos de asistencia en Google Sheets"""
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return False
            
            sheet = self.client.open_by_key(sheet_ids["asistencia"])
            
            # Buscar o crear hoja del curso
            try:
                worksheet = sheet.worksheet(course_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=course_name, rows=1000, cols=6)
                worksheet.append_row(["Curso", "Fecha", "Estudiante", "Asistencia", "Timestamp", "Usuario"])
            
            # Preparar datos
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            rows = []
            
            for estudiante, presente in attendance_data.items():
                rows.append([
                    course_name,
                    fecha,
                    estudiante,
                    1 if presente else 0,
                    timestamp,
                    user
                ])
            
            # Guardar datos
            worksheet.append_rows(rows)
            return True
            
        except Exception as e:
            st.error(f"❌ Error guardando asistencia: {e}")
            return False
    
    def load_emails(self) -> tuple[Dict[str, str], Dict[str, str]]:
        """Carga emails de estudiantes y apoderados"""
        try:
            sheet_ids = self.get_sheet_ids()
            if not sheet_ids or "asistencia" not in sheet_ids:
                return {}, {}
            
            sheet = self.client.open_by_key(sheet_ids["asistencia"])
            
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