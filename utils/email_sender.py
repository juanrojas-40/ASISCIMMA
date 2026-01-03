# utils/email_sender.py
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formatdate
import streamlit as st
from typing import Dict, List, Any
import os

class EmailManager:
    """Manejador de envío de emails usando secrets de Streamlit"""

    def __init__(self):
        self.smtp_config = self._load_smtp_config()

    def _load_smtp_config(self) -> Dict[str, Any]:
        """Carga configuración SMTP desde secrets de Streamlit"""
        try:
            return {
                "server": st.secrets["EMAIL"]["smtp_server"],
                "port": int(st.secrets["EMAIL"]["smtp_port"]),
                "sender": st.secrets["EMAIL"]["sender_email"],
                "password": st.secrets["EMAIL"]["sender_password"]
            }
        except KeyError as e:
            st.error(f"❌ Configuración de email incompleta en secrets: {e}")
            return {}

    def send_email(self, to_email: str, subject: str, body: str, logo_path: str = None) -> bool:
        """Envía un email individual con soporte para HTML y logo"""
        try:
            if not self.smtp_config:
                return False

            msg = MIMEMultipart('related')
            msg["From"] = self.smtp_config["sender"]
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)

            if body.strip().startswith('<'):
                msg_alternative.attach(MIMEText(body, 'html'))
            else:
                msg_alternative.attach(MIMEText(body, 'plain'))

            if logo_path and os.path.exists(logo_path):
                try:
                    with open(logo_path, 'rb') as f:
                        logo_data = f.read()
                    logo = MIMEImage(logo_data)
                    logo.add_header('Content-ID', '<logo_institucion>')
                    msg.attach(logo)
                except Exception as e:
                    st.warning(f"⚠️ No se pudo adjuntar el logo: {e}")

            server = smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"])
            server.starttls()
            server.login(self.smtp_config["sender"], self.smtp_config["password"])
            server.send_message(msg)
            server.quit()
            return True

        except Exception as e:
            st.error(f"❌ Error enviando email a {to_email}: {e}")
            return False

    def create_attendance_email(self, apoderado: str, estudiante: str, curso: str, fecha: str, presente: bool,
                               porcentaje_asistencia: float, total_clases: int, presentes: int, ausentes: int,
                               recomendaciones: str = "") -> tuple:
        """
        Crea un email de asistencia con formato moderno y atractivo.
        """
        estado = "ASISTIÓ ✅" if presente else "NO ASISTIÓ ❌"
        color = "#28a745" if presente else "#dc3545"
        estado_icono = "✅" if presente else "❌"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reporte de Asistencia - CIMMA</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                    background-color: #f8f9fa;
                }}
                .container {{
                    max-width: 600px;
                    margin: 20px auto;
                    padding: 20px;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-align: center;
                    padding: 20px;
                    border-radius: 10px 10px 0 0;
                    margin-bottom: 20px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 24px;
                }}
                .info-card {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid {color};
                }}
                .info-card h3 {{
                    color: #004080;
                    margin-top: 0;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                .info-card table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                .info-card td {{
                    padding: 8px 0;
                    vertical-align: top;
                }}
                .info-card td:first-child {{
                    font-weight: bold;
                    width: 120px;
                }}
                .summary {{
                    background-color: #f0f2f5;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .summary h4 {{
                    margin-top: 0;
                    color: #004080;
                }}
                .recommendations {{
                    background-color: #fff8e1;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #ffc107;
                }}
                .recommendations h4 {{
                    margin-top: 0;
                    color: #004080;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    border-top: 1px solid #eee;
                    margin-top: 20px;
                    font-size: 12px;
                    color: #666;
                }}
                .footer img {{
                    width: 200px;
                    height: auto;
                    margin-bottom: 10px;
                }}
                .quote {{
                    text-align: center;
                    font-style: italic;
                    color: #666;
                    margin: 20px 0;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reporte de Asistencia</h1>
                </div>

                <p>Hola <strong>{apoderado}</strong>,</p>
                <p>Este es un reporte automático de asistencia para el curso <strong>{curso}</strong>.</p>

                <div class="info-card">
                    <h3><img src="cid:logo_institucion" style="width: 20px; height: 20px;"> Información de Asistencia</h3>
                    <table>
                        <tr><td>📅 Fecha:</td><td>{fecha}</td></tr>
                        <tr><td>👨‍🎓 Estudiante:</td><td><strong>{estudiante}</strong></td></tr>
                        <tr><td>📌 Estado:</td><td style="color: {color}; font-weight: bold; font-size: 18px;">{estado_icono} {estado}</td></tr>
                    </table>
                </div>

                <div class="summary">
                    <h4>📊 Resumen de Asistencia</h4>
                    <ul>
                        <li><strong>Porcentaje de asistencia:</strong> {porcentaje_asistencia:.1f}%</li>
                        <li><strong>Total de clases:</strong> {total_clases}</li>
                        <li><strong>Clases presentes:</strong> {presentes}</li>
                        <li><strong>Clases ausentes:</strong> {ausentes}</li>
                    </ul>
                </div>

                <div class="recommendations">
                    <h4>💡 Recomendaciones</h4>
                    <p>{recomendaciones}</p>
                </div>

                <div class="quote">
                    "La educación es el arma más poderosa para cambiar el mundo" - Nelson Mandela
                </div>

                <div class="footer">
                    <p>Saludos cordiales,<br><strong>Preuniversitario CIMMA 2026</strong></p>
                    <img src="cid:logo_institucion" alt="Logo Preuniversitario CIMMA">
                    <p>Este es un mensaje automático. Por favor, no responda a este correo.<br>Si tiene preguntas, contacte a la administración.</p>
                </div>
            </div>
        </body>
        </html>
        """

        subject = f"Reporte de Asistencia - {estudiante} - {curso} - {fecha}"
        return subject, html

    def send_attendance_emails(self, 
                              curso: str, 
                              fecha: str, 
                              attendance_data: Dict[str, bool],
                              student_stats: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Envía emails de asistencia usando datos precalculados.
        
        Args:
            curso: Nombre del curso.
            fecha: Fecha de la asistencia.
            attendance_data: Dict con el estado de asistencia del día.
            student_stats: Dict con las estadísticas acumuladas por estudiante.
                Ej: {
                    "juan perez": {
                        "porcentaje_asistencia": 85.5,
                        "total_clases": 20,
                        "presentes": 17,
                        "ausentes": 3,
                        "recomendaciones": "¡Excelente asistencia!"
                    }
                }
        """
        from .google_sheets import GoogleSheetsManager
        sheets_manager = GoogleSheetsManager()
        emails, nombres_apoderados = sheets_manager.load_emails()

        if not emails:
            return {"sent": 0, "failed": 0, "total": 0}

        results = {"sent": 0, "failed": 0, "total": 0}
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, (estudiante, presente) in enumerate(attendance_data.items()):
            estudiante_key = estudiante.strip().lower()
            if estudiante_key in emails:
                results["total"] += 1
                apoderado = nombres_apoderados.get(estudiante_key, "Apoderado/a")
                email_destino = emails[estudiante_key]

                # Obtener estadísticas desde el argumento (no se calculan aquí)
                stats = student_stats.get(estudiante_key, {})
                porcentaje_asistencia = stats.get("porcentaje_asistencia", 0.0)
                total_clases = stats.get("total_clases", 0)
                presentes = stats.get("presentes", 0)
                ausentes = stats.get("ausentes", 0)
                recomendaciones = stats.get("recomendaciones", "")

                subject, html_content = self.create_attendance_email(
                    apoderado, estudiante, curso, fecha, presente,
                    porcentaje_asistencia, total_clases, presentes, ausentes, recomendaciones
                )

                if self.send_email(email_destino, subject, html_content, logo_path="LOGO.png"):
                    results["sent"] += 1
                else:
                    results["failed"] += 1

                progress = (i + 1) / len(attendance_data)
                progress_bar.progress(progress)
                status_text.text(f"📧 Enviando... {i+1}/{len(attendance_data)}")

        return results

    def send_bulk_emails(self, destinatarios: List[Dict[str, Any]], subject: str,
                        body_template: str, is_html: bool = False, delay: float = 0.6) -> Dict[str, Any]:
        """
        Envía emails masivos con delay controlado para evitar límites SMTP.
        delay: segundos entre envíos (por defecto 0.6s → ~100 emails/minuto)
        """
        if not self.smtp_config:
            return {"sent": 0, "failed": 0, "total": 0, "details": []}

        results: Dict[str, Any] = {
            "sent": 0,
            "failed": 0,
            "total": len(destinatarios),
            "details": []
        }

        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
        except:
            progress_bar = None
            status_text = None

        for i, destino in enumerate(destinatarios):
            try:
                email_destino = destino.get("email")
                if not email_destino or email_destino == "No registrado":
                    results["failed"] += 1
                    results["details"].append({
                        "estudiante": destino.get("estudiante", "N/A"),
                        "email": email_destino or "N/A",
                        "status": "❌ Sin email válido"
                    })
                    continue

                personalized_body = body_template
                for key, value in destino.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in personalized_body:
                        personalized_body = personalized_body.replace(placeholder, str(value) if value else "")

                if self.send_email(email_destino, subject, personalized_body, logo_path="LOGO.png"):
                    results["sent"] += 1
                    results["details"].append({
                        "estudiante": destino.get("estudiante", ""),
                        "email": email_destino,
                        "status": "✅ Enviado"
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "estudiante": destino.get("estudiante", ""),
                        "email": email_destino,
                        "status": "❌ Falló"
                    })

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "estudiante": destino.get("estudiante", ""),
                    "email": destino.get("email", ""),
                    "status": f"❌ Error: {str(e)[:60]}"
                })

            if i < len(destinatarios) - 1:
                time.sleep(delay)

            if progress_bar:
                progress = (i + 1) / len(destinatarios)
                progress_bar.progress(progress)
                if status_text:
                    status_text.caption(f"📧 Enviando... {i+1}/{len(destinatarios)} - {results['sent']} enviados")

        return results