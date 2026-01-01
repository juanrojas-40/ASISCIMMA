# Añade estos métodos a la clase GoogleSheetsManager (después de load_courses_for_teacher)

def load_courses_by_sede(self, sede_nombre: str) -> Dict:
    """Carga todos los cursos de una sede específica"""
    try:
        all_courses = self.load_courses()
        sede_courses = {}
        
        for course_name, course_data in all_courses.items():
            if course_data.get("sede", "").upper() == sede_nombre.upper():
                # Enriquecer con datos de asistencia si es necesario
                course_data["asistencias"] = self.load_attendance_for_course(course_name)
                sede_courses[course_name] = course_data
        
        return sede_courses
        
    except Exception as e:
        st.error(f"❌ Error cargando cursos por sede: {e}")
        return {}

def load_attendance_for_course(self, course_name: str) -> Dict:
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
            return {}
            
    except Exception as e:
        print(f"⚠️ Error cargando asistencia para {course_name}: {e}")
        return {}

def get_all_emails_by_sede(self, sede_nombre: str) -> List[Dict]:
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

def get_low_attendance_students(self, sede_nombre: str, threshold: float = 70.0) -> List[Dict]:
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