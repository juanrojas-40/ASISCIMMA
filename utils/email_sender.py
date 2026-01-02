# utils/email_sender.py
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
import streamlit as st
from typing import Dict, List, Any

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

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Envía un email individual"""
        try:
            if not self.smtp_config:
                return False

            msg = MIMEMultipart('alternative')
            msg["From"] = self.smtp_config["sender"]
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Date"] = formatdate(localtime=True)

            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"])
            server.starttls()
            server.login(self.smtp_config["sender"], self.smtp_config["password"])
            server.send_message(msg)
            server.quit()
            return True

        except Exception as e:
            st.error(f"❌ Error enviando email a {to_email}: {e}")
            return False

    def create_attendance_email(self, apoderado: str, estudiante: str, curso: str, fecha: str, presente: bool) -> tuple:
        estado = "ASISTIÓ ✅" if presente else "NO ASISTIÓ ❌"
        color = "#28a745" if presente else "#dc3545"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reporte de Asistencia - CIMMA</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <div style="background: linear-gradient(135deg, #1A3B8F 0%, #2D4FA8 100%); padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0;">🎓 Preuniversitario CIMMA</h1>
                    <p style="color: white; opacity: 0.9; margin: 5px 0 0 0;">Reporte de Asistencia 2026</p>
                </div>
                
                <div style="padding: 20px;">
                    <p>Estimado/a <strong>{apoderado}</strong>,</p>
                    <p>Le informamos el estado de asistencia de <strong>{estudiante}</strong>:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {color};">
                        <h3 style="color: #004080; margin-top: 0;">📊 Información de Asistencia</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr><td style="padding: 8px 0; font-weight: bold; width: 120px;">📅 Fecha:</td><td style="padding: 8px 0;">{fecha}</td></tr>
                            <tr><td style="padding: 8px 0; font-weight: bold;">📚 Curso:</td><td style="padding: 8px 0;">{curso}</td></tr>
                            <tr><td style="padding: 8px 0; font-weight: bold;">👨‍🎓 Estudiante:</td><td style="padding: 8px 0;"><strong>{estudiante}</strong></td></tr>
                            <tr><td style="padding: 8px 0; font-weight: bold;">📌 Estado:</td><td style="padding: 8px 0; color: {color}; font-weight: bold; font-size: 18px;">{estado}</td></tr>
                        </table>
                    </div>
                    
                    <p style="text-align: center; font-style: italic; color: #666;">"La educación es el arma más poderosa para cambiar el mundo" - Nelson Mandela</p>
                    <p>Saludos cordiales,<br><strong>Equipo Preuniversitario CIMMA</strong></p>
                </div>
                
                <div style="background-color: #f0f2f5; padding: 15px; border-radius: 0 0 10px 10px; text-align: center; font-size: 12px; color: #666;">
                    <p style="margin: 0;">Este es un mensaje automático. Por favor, no responda a este correo.<br>Si tiene preguntas, contacte a la administración.</p>
                </div>
            </div>
        </body>
        </html>
        """
        subject = f"Asistencia CIMMA - {estudiante} - {fecha}"
        return subject, html

    def send_attendance_emails(self, curso: str, fecha: str, attendance_data: Dict[str, bool]) -> Dict[str, Any]:
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
                subject, html_content = self.create_attendance_email(apoderado, estudiante, curso, fecha, presente)
                if self.send_email(email_destino, subject, html_content, is_html=True):
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

                # Personalizar mensaje
                personalized_body = body_template
                for key, value in destino.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in personalized_body:
                        personalized_body = personalized_body.replace(placeholder, str(value) if value else "")

                # Enviar
                if self.send_email(email_destino, subject, personalized_body, is_html=is_html):
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

            # Throttling (solo si no es el último)
            if i < len(destinatarios) - 1:
                time.sleep(delay)

            # Actualizar progreso
            if progress_bar:
                progress = (i + 1) / len(destinatarios)
                progress_bar.progress(progress)
                if status_text:
                    status_text.caption(f"📧 Enviando... {i+1}/{len(destinatarios)} - {results['sent']} enviados")

        return results