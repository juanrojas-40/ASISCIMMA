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
        except ValueError:
            st.error("❌ El puerto SMTP debe ser un número entero")
            return {}

    def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Envía un email individual"""
        if not self.smtp_config:
            return False

        # Validación básica de email destino
        if not to_email or "@" not in to_email or " " in to_email.strip():
            st.warning(f"⚠️ Email inválido ignorado: {to_email}")
            return False

        try:
            msg = MIMEMultipart('alternative')
            msg["From"] = self.smtp_config["sender"]
            msg["To"] = to_email.strip()
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

        except smtplib.SMTPAuthenticationError:
            st.error("❌ Error de autenticación SMTP. Verifique usuario/contraseña o app password.")
            return False
        except smtplib.SMTPRecipientsRefused:
            st.warning(f"❌ Destinatario rechazado: {to_email}")
            return False
        except smtplib.SMTPServerDisconnected:
            st.error("❌ Servidor SMTP se desconectó inesperadamente.")
            return False
        except Exception as e:
            st.error(f"❌ Error enviando email a {to_email}: {str(e)[:100]}")
            return False

    def create_attendance_email(self, apoderado: str, estudiante: str, curso: str, fecha: str, presente: bool) -> tuple:
        """Genera el subject y cuerpo HTML del email de asistencia"""
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
                    <p>Estimado/a <strong>{apoderado or "Apoderado/a"}</strong>,</p>
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
                    <p style="margin: 0;">Este es un mensaje automático. Por favor, no responda a este correo.<br>Si tiene preguntas, contacte a la administración de su sede.</p>
                </div>
            </div>
        </body>
        </html>
        """
        subject = f"Asistencia CIMMA - {estudiante} - {fecha}"
        return subject, html

    def send_attendance_emails(self, curso: str, fecha: str, attendance_data: Dict[str, bool]) -> Dict[str, Any]:
        """Envía emails de asistencia a apoderados usando la hoja MAILS"""
        from .google_sheets import GoogleSheetsManager
        sheets_manager = GoogleSheetsManager()
        emails, nombres_apoderados = sheets_manager.load_emails()

        if not emails:
            st.warning("⚠️ No se encontraron emails de apoderados en la hoja MAILS")
            return {"sent": 0, "failed": 0, "total": 0}

        destinatarios = []
        for estudiante, presente in attendance_data.items():
            estudiante_key = estudiante.strip().lower()
            if estudiante_key in emails:
                destinatarios.append({
                    "estudiante": estudiante,
                    "email": emails[estudiante_key],
                    "apoderado": nombres_apoderados.get(estudiante_key, "Apoderado/a"),
                    "presente": presente
                })

        if not destinatarios:
            st.info("ℹ️ No hay apoderados con email registrado para este curso")
            return {"sent": 0, "failed": 0, "total": 0}

        # Usar send_bulk_emails con plantilla personalizada
        body_template = """
        {{create_attendance_email}}
        """

        # Esta función delega al envío masivo optimizado
        return self.send_bulk_emails(
            destinatarios=destinatarios,
            subject="Asistencia CIMMA",  # Será sobrescrito por la plantilla interna
            body_template=body_template,
            is_html=True,
            context_extra={"curso": curso, "fecha": fecha}
        )

    def send_bulk_emails(
        self,
        destinatarios: List[Dict[str, Any]],
        subject: str,
        body_template: str,
        is_html: bool = False,
        delay: float = 0.8,  # Valor base aumentado para mayor seguridad
        context_extra: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Envía emails masivos con throttling inteligente.
        - Delay dinámico: aumenta si el lote es grande.
        - Progreso visual claro.
        - Manejo robusto de errores.
        """
        if not self.smtp_config:
            st.error("❌ Configuración SMTP no disponible")
            return {"sent": 0, "failed": 0, "total": 0, "details": []}

        if not destinatarios:
            st.info("ℹ️ No hay destinatarios válidos para enviar")
            return {"sent": 0, "failed": 0, "total": 0, "details": []}

        total = len(destinatarios)

        # === Delay dinámico basado en volumen ===
        if total > 100:
            delay = max(delay, 2.0)   # ~30 emails/minuto
        elif total > 50:
            delay = max(delay, 1.5)   # ~40 emails/minuto
        elif total > 20:
            delay = max(delay, 1.0)   # ~60 emails/minuto

        st.info(f"📧 Iniciando envío masivo a {total} apoderados (delay ≈ {delay}s entre emails)")

        results: Dict[str, Any] = {
            "sent": 0,
            "failed": 0,
            "total": total,
            "details": []
        }

        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, destino in enumerate(destinatarios):
            email_destino = destino.get("email")
            estudiante = destino.get("estudiante", "Desconocido")

            try:
                if not email_destino or email_destino == "No registrado" or "@" not in email_destino:
                    results["failed"] += 1
                    results["details"].append({
                        "estudiante": estudiante,
                        "email": email_destino or "N/A",
                        "status": "❌ Sin email válido"
                    })
                    progress_bar.progress((i + 1) / total)
                    status_text.text(f"Procesando {i+1}/{total} | Enviados: {results['sent']} | Fallidos: {results['failed']}")
                    continue

                # Personalización del cuerpo
                personalized_body = body_template
                context = destino.copy()
                if context_extra:
                    context.update(context_extra)

                # Caso especial: email de asistencia (usamos create_attendance_email)
                if "{{create_attendance_email}}" in body_template:
                    apoderado = context.get("apoderado", "Apoderado/a")
                    est = context.get("estudiante", "")
                    curso = context.get("curso", "")
                    fecha = context.get("fecha", "")
                    presente = context.get("presente", True)
                    subj, html_body = self.create_attendance_email(apoderado, est, curso, fecha, presente)
                    personalized_body = html_body
                    final_subject = subj
                else:
                    for key, value in context.items():
                        placeholder = f"{{{key}}}"
                        if placeholder in personalized_body:
                            personalized_body = personalized_body.replace(placeholder, str(value) if value else "")
                    final_subject = subject

                # Envío
                if self.send_email(email_destino, final_subject, personalized_body, is_html=is_html):
                    results["sent"] += 1
                    results["details"].append({
                        "estudiante": estudiante,
                        "email": email_destino,
                        "status": "✅ Enviado"
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "estudiante": estudiante,
                        "email": email_destino,
                        "status": "❌ Falló envío"
                    })

            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "estudiante": estudiante,
                    "email": email_destino or "N/A",
                    "status": f"❌ Error: {str(e)[:60]}"
                })

            # Actualizar UI
            progress = (i + 1) / total
            progress_bar.progress(progress)
            status_text.text(f"📧 Enviando {i+1}/{total} | ✅ {results['sent']} | ❌ {results['failed']}")

            # Throttling (excepto último)
            if i < total - 1:
                time.sleep(delay)

        # Resumen final
        if results["sent"] == total:
            st.success(f"🎉 ¡Todos los {total} emails enviados exitosamente!")
        elif results["sent"] > 0:
            st.warning(f"⚠️ Envío completado: {results['sent']} enviados, {results['failed']} fallidos")
        else:
            st.error("❌ Ningún email pudo ser enviado")

        return results

    # === Nota futura (opcional) ===
    # Para escalar a >500 emails/día, considera migrar a:
    # - SendGrid (API key en secrets)
    # - Mailgun
    # - Amazon SES
    # Ejemplo con SendGrid:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    # self.sg = SendGridAPIClient(st.secrets["EMAIL"]["sendgrid_api_key"])