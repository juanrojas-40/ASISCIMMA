# utils/send_apoderados.py
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from .email_sender import EmailManager
from .google_sheets import GoogleSheetsManager
from config.settings import AppSettings

logger = logging.getLogger(__name__)

class ApoderadosEmailSender:
    """Clase especializada para envíos masivos a apoderados."""
    
    def __init__(self):
        self.email_manager = EmailManager()
        self.sheets_manager = GoogleSheetsManager()
        self.settings = AppSettings.load_from_secrets()
        
    def get_apoderados_by_filters(
        self, 
        sede: str, 
        curso: Optional[str] = None,
        filtro_porcentaje: Optional[float] = None,
        fecha_reporte: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtiene apoderados filtrados por diferentes criterios."""
        
        try:
            # Cargar emails
            emails_data, nombres_apoderados = self.sheets_manager.load_emails()
            if not emails_data:
                logger.warning("No se encontraron emails en la base de datos")
                return []
            
            # Cargar cursos de la sede
            cursos_sede = self.sheets_manager.load_courses_by_sede(sede)
            if not cursos_sede:
                logger.warning(f"No se encontraron cursos para la sede {sede}")
                return []
            
            apoderados_list = []
            
            for curso_nombre, curso_data in cursos_sede.items():
                # Filtrar por curso específico si se especifica
                if curso and curso_nombre != curso:
                    continue
                
                # Calcular estadísticas para cada estudiante
                for estudiante in curso_data.get("estudiantes", []):
                    estudiante_key = estudiante.strip().lower()
                    
                    # Verificar si tiene email registrado
                    if estudiante_key not in emails_data:
                        continue
                    
                    # Calcular estadísticas
                    stats = self._calculate_student_stats(estudiante, curso_nombre, curso_data, fecha_reporte)
                    
                    # Aplicar filtro por porcentaje si existe
                    if filtro_porcentaje is not None:
                        if filtro_porcentaje < 70 and stats["porcentaje_asistencia"] >= 70:
                            continue
                        elif filtro_porcentaje >= 85 and stats["porcentaje_asistencia"] < 85:
                            continue
                    
                    # Agregar a la lista
                    apoderados_list.append({
                        "estudiante": estudiante,
                        "curso": curso_nombre,
                        "email": emails_data[estudiante_key],
                        "apoderado": nombres_apoderados.get(estudiante_key, "Apoderado/a"),
                        "sede": sede,
                        **stats
                    })
            
            logger.info(f"Apoderados encontrados: {len(apoderados_list)}")
            return apoderados_list
            
        except Exception as e:
            logger.error(f"Error obteniendo apoderados: {e}")
            st.error(f"Error obteniendo lista de apoderados: {str(e)[:100]}")
            return []
    
    def _calculate_student_stats(
        self, 
        estudiante: str, 
        curso_nombre: str, 
        curso_data: Dict[str, Any],
        fecha_reporte: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calcula estadísticas de asistencia para un estudiante."""
        
        try:
            asistencias_est = curso_data.get("asistencias", {}).get(estudiante, {})
            total_fechas = len(curso_data.get("fechas", []))
            
            # Si hay fecha específica, calcular solo para esa fecha
            if fecha_reporte:
                presente = asistencias_est.get(fecha_reporte, False)
                return {
                    "presente_hoy": presente,
                    "estado_hoy": "PRESENTE ✅" if presente else "AUSENTE ❌",
                    "fecha_reporte": fecha_reporte
                }
            
            # Calcular estadísticas generales
            presentes = sum(1 for estado in asistencias_est.values() if estado)
            ausentes = total_fechas - presentes
            porcentaje = (presentes / total_fechas * 100) if total_fechas > 0 else 0
            
            # Determinar recomendación
            if porcentaje < 70:
                recomendacion = "Le recomendamos mejorar la asistencia para un mejor rendimiento académico."
                nivel = "CRITICO"
            elif porcentaje < 85:
                recomendacion = "Su asistencia es buena, pero puede mejorar."
                nivel = "REGULAR"
            else:
                recomendacion = "¡Excelente asistencia! Continúe así."
                nivel = "EXCELENTE"
            
            return {
                "porcentaje_asistencia": round(porcentaje, 1),
                "total_clases": total_fechas,
                "presentes": presentes,
                "ausentes": ausentes,
                "recomendacion": recomendacion,
                "nivel_asistencia": nivel,
                "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d")
            }
            
        except Exception as e:
            logger.error(f"Error calculando stats para {estudiante}: {e}")
            return {
                "porcentaje_asistencia": 0,
                "total_clases": 0,
                "presentes": 0,
                "ausentes": 0,
                "recomendacion": "No hay datos disponibles.",
                "nivel_asistencia": "SIN DATOS",
                "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d")
            }
    
    def send_bulk_emails_to_apoderados(
        self,
        sede: str,
        subject: str,
        body_template: str,
        curso: Optional[str] = None,
        filtro_porcentaje: Optional[float] = None,
        fecha_reporte: Optional[str] = None,
        test_mode: bool = False
    ) -> Dict[str, Any]:
        """Envía emails masivos a apoderados."""
        
        try:
            # Obtener destinatarios
            destinatarios_data = self.get_apoderados_by_filters(
                sede=sede,
                curso=curso,
                filtro_porcentaje=filtro_porcentaje,
                fecha_reporte=fecha_reporte
            )
            
            if not destinatarios_data:
                return {
                    "success": False,
                    "message": "No se encontraron destinatarios con los criterios especificados",
                    "sent": 0,
                    "failed": 0,
                    "total": 0
                }
            
            # Modo prueba - solo mostrar preview
            if test_mode:
                preview_data = []
                for d in destinatarios_data[:3]:  # Solo primeros 3 para preview
                    preview_body = self._personalize_template(body_template, d)
                    preview_data.append({
                        "estudiante": d["estudiante"],
                        "email": d["email"],
                        "preview": preview_body[:200] + "..."
                    })
                
                return {
                    "success": True,
                    "message": f"Modo prueba: {len(destinatarios_data)} emails listos para enviar",
                    "preview": preview_data,
                    "total": len(destinatarios_data)
                }
            
            # Preparar destinatarios para el email manager
            destinatarios = []
            for apoderado in destinatarios_data:
                destinatarios.append({
                    "estudiante": apoderado["estudiante"],
                    "email": apoderado["email"],
                    "curso": apoderado["curso"],
                    "apoderado": apoderado["apoderado"],
                    "porcentaje": apoderado["porcentaje_asistencia"],
                    "total_clases": apoderado["total_clases"],
                    "presentes": apoderado["presentes"],
                    "ausentes": apoderado["ausentes"],
                    "sede": apoderado["sede"],
                    "recomendacion": apoderado["recomendacion"],
                    "nivel": apoderado.get("nivel_asistencia", ""),
                    "fecha_reporte": fecha_reporte or datetime.now().strftime("%Y-%m-%d")
                })
            
            # Enviar emails
            resultados = self.email_manager.send_bulk_emails(
                destinatarios=destinatarios,
                subject=subject,
                body_template=body_template,
                is_html=True,
                delay=self.settings.EMAIL_DELAY_BETWEEN_SENDS
            )
            
            # Agregar contexto adicional
            resultados.update({
                "sede": sede,
                "curso": curso or "Todos",
                "filtro": f"Porcentaje < {filtro_porcentaje}%" if filtro_porcentaje else "Todos",
                "fecha_envio": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return resultados
            
        except Exception as e:
            logger.error(f"Error en envío masivo a apoderados: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "sent": 0,
                "failed": 0,
                "total": 0
            }
    
    def _personalize_template(self, template: str, data: Dict[str, Any]) -> str:
        """Personaliza una plantilla con datos del destinatario."""
        personalized = template
        
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in personalized:
                personalized = personalized.replace(placeholder, str(value))
        
        return personalized
    
    def generate_email_template(
        self,
        tipo: str = "asistencia_general",
        sede: str = "",
        fecha: str = ""
    ) -> str:
        """Genera plantillas de email predefinidas."""
        
        templates = {
            "asistencia_general": f"""
Estimado/a {{apoderado}},

Le informamos sobre la situación de asistencia de **{{estudiante}}** en el curso **{{curso}}** de la sede **{{sede}}**.

**📊 Resumen de asistencia:**
- 📅 Período evaluado: Hasta {fecha or "la fecha actual"}
- ✅ Porcentaje de asistencia: **{{porcentaje}}%**
- 📚 Total de clases: {{total_clases}}
- ✅ Clases presentes: {{presentes}}
- ❌ Clases ausentes: {{ausentes}}
- 🎯 Nivel: {{nivel}}

**💡 Recomendaciones:**
{{recomendacion}}

**📌 Importante:**
La asistencia regular es fundamental para el éxito académico. Le recomendamos revisar este reporte con su estudiante.

Saludos cordiales,
Equipo Sede {sede}
Preuniversitario CIMMA

📍 Contacto: +56 9 XXXX XXXX
📧 Email: contacto@cimma.cl
            """,
            
            "baja_asistencia": f"""
Estimado/a {{apoderado}},

Nos dirigimos a usted para informarle que **{{estudiante}}** presenta **baja asistencia** en el curso **{{curso}}** de la sede **{{sede}}**.

**🚨 Situación actual:**
- 📅 Período evaluado: Hasta {fecha or "la fecha actual"}
- ⚠️ Porcentaje de asistencia: **{{porcentaje}}%** (por debajo del 70% recomendado)
- 📚 Total de clases: {{total_clases}}
- ✅ Clases presentes: {{presentes}}
- ❌ Clases ausentes: {{ausentes}}

**🔔 Acciones recomendadas:**
1. Revisar con su estudiante las razones de las ausencias
2. Establecer un plan para mejorar la asistencia
3. Contactar al profesor del curso si necesita apoyo

**📞 Soporte:**
Puede contactarnos para coordinar una reunión o recibir asesoramiento.

Saludos cordiales,
Equipo Sede {sede}
Preuniversitario CIMMA

📍 Contacto: +56 9 XXXX XXXX
📧 Email: contacto@cimma.cl
            """,
            
            "excelente_asistencia": f"""
Estimado/a {{apoderado}},

¡Tenemos excelentes noticias! **{{estudiante}}** mantiene una **asistencia ejemplar** en el curso **{{curso}}** de la sede **{{sede}}**.

**🏆 Reconocimiento:**
- 📅 Período evaluado: Hasta {fecha or "la fecha actual"}
- 🎯 Porcentaje de asistencia: **{{porcentaje}}%** (¡Excelente!)
- 📚 Total de clases: {{total_clases}}
- ✅ Clases presentes: {{presentes}}
- ❌ Clases ausentes: {{ausentes}}

**✨ Felicitaciones:**
Queremos reconocer el compromiso y responsabilidad de su estudiante. Esta dedicación es fundamental para el éxito académico.

¡Siga así!

Saludos cordiales,
Equipo Sede {sede}
Preuniversitario CIMMA

📍 Contacto: +56 9 XXXX XXXX
📧 Email: contacto@cimma.cl
            """
        }
        
        return templates.get(tipo, templates["asistencia_general"])

# Función helper para uso rápido
def get_apoderados_sender() -> ApoderadosEmailSender:
    """Retorna una instancia de ApoderadosEmailSender."""
    return ApoderadosEmailSender()