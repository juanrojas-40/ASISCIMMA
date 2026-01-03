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
            st.error(f"✗ Configuración de email incompleta en secrets: {e}")
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
                    st.warning(f"△ No se pudo adjuntar el logo: {e}")

            server = smtplib.SMTP(self.smtp_config["server"], self.smtp_config["port"])
            server.starttls()
            server.login(self.smtp_config["sender"], self.smtp_config["password"])
            server.send_message(msg)
            server.quit()
            return True

        except Exception as e:
            st.error(f"✗ Error enviando email a {to_email}: {e}")
            return False
    
    def send_bulk_emails(self, destinatarios: List[Dict[str, Any]], subject: str, 
                        body_template: str, is_html: bool = False, delay: float = 0.6) -> Dict[str, Any]:
        """
        Envía emails masivos con delay controlado para evitar límites SMTP.
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
                        "status": "Sin email válido"
                    })
                    continue

                personalized_body = body_template
                for key, value in destino.items():
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in personalized_body:
                        personalized_body = personalized_body.replace(placeholder, str(value) if value else "")
                
                if self.send_email(email_destino, subject, personalized_body):
                    results["sent"] += 1
                    results["details"].append({
                        "estudiante": destino.get("estudiante", ""),
                        "email": email_destino,
                        "status": "Enviado ✅"
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "estudiante": destino.get("estudiante", ""),
                        "email": email_destino,
                        "status": "Falló ❌"
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "estudiante": destino.get("estudiante", ""),
                    "email": destino.get("email", ""),
                    "status": f"Error: {str(e)[:60]}"
                })

            if i < len(destinatarios) - 1:
                time.sleep(delay)

            if progress_bar:
                progress = (i + 1) / len(destinatarios)
                progress_bar.progress(progress)
                if status_text:
                    status_text.caption(f"📤 Enviando... {i+1}/{len(destinatarios)} - {results['sent']} enviados")

        return results