# Añade este método a la clase EmailManager (después de send_attendance_emails)

def send_bulk_emails(self, destinatarios: List[Dict], subject: str, 
                     body_template: str, is_html: bool = True) -> Dict:
    """Envía emails masivos a múltiples destinatarios"""
    
    if not self.smtp_config:
        return {"sent": 0, "failed": 0, "total": 0, "details": []}
    
    results = {
        "sent": 0,
        "failed": 0, 
        "total": len(destinatarios),
        "details": []
    }
    
    # Configurar barra de progreso si estamos en Streamlit
    try:
        import streamlit as st
        progress_bar = st.progress(0)
        status_text = st.empty()
    except:
        progress_bar = None
        status_text = None
    
    for i, destino in enumerate(destinatarios):
        try:
            # Personalizar el mensaje
            personalized_body = body_template
            for key, value in destino.items():
                placeholder = f"{{{key}}}"
                if placeholder in personalized_body:
                    personalized_body = personalized_body.replace(placeholder, str(value))
            
            # Enviar email
            if self.send_email(
                to_email=destino["email"],
                subject=subject,
                body=personalized_body,
                is_html=is_html
            ):
                results["sent"] += 1
                results["details"].append({
                    "estudiante": destino.get("estudiante", ""),
                    "email": destino["email"],
                    "status": "✅ Enviado"
                })
            else:
                results["failed"] += 1
                results["details"].append({
                    "estudiante": destino.get("estudiante", ""),
                    "email": destino["email"],
                    "status": "❌ Falló"
                })
            
            # Actualizar progreso
            if progress_bar:
                progress = (i + 1) / len(destinatarios)
                progress_bar.progress(progress)
                if status_text:
                    status_text.text(f"📧 Enviando... {i+1}/{len(destinatarios)}")
            
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "estudiante": destino.get("estudiante", ""),
                "email": destino.get("email", ""),
                "status": f"❌ Error: {str(e)[:50]}"
            })
    
    return results