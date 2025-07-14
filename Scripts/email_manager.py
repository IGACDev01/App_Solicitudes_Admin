import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

APP_URL = "https://appsolicitudes-h72izekvzacukoykxwnfqb.streamlit.app/"

class EmailManager:
    def __init__(self):
        # Load environment variables
        try:
            load_dotenv("Scripts\\email.env")
        except:
            # File doesn't exist - will use Streamlit secrets or env vars
            pass
        
        # Microsoft Graph API configuration
        self.tenant_id = os.getenv("TENANT_ID", "")
        self.client_id = os.getenv("CLIENT_ID", "")
        self.client_secret = os.getenv("CLIENT_SECRET", "")
        self.sender_email = os.getenv("SENDER_EMAIL", "")
        
        # URLs
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_api_url = "https://graph.microsoft.com/v1.0"
        
        # Check if configuration is complete
        self.email_enabled = bool(self.tenant_id and self.client_id and self.client_secret and self.sender_email)
        
        # Token management
        self.access_token = None
        
        # Internal logging
        if self.email_enabled:
            print("Email service configured successfully")
        else:
            print("Email service not configured - operating in simulation mode")
    
    def _get_access_token(self) -> Optional[str]:
        """Get access token from Microsoft Graph API"""
        try:
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            response = requests.post(self.token_url, data=token_data, headers=headers)
            
            if response.status_code == 200:
                token_info = response.json()
                print("Email token obtained successfully")
                return token_info.get('access_token')
            else:
                error_detail = response.json()
                print(f"Email token error: {error_detail.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"Email authentication error: {e}")
            return None
    
    def get_responsables_email(self, area: str, proceso: str, tipo_solicitud: str) -> list:
        """Get responsible emails based on process only"""
        # Email mapping based on process only
        responsables_map = {
            # Subdirección Administrativa y Financiera
            "Almacén": ["TESTalmacengeneral@igac.gov.co"],
            "Apropiaciones": [""],
            "Contabilidad": ["TESTdoris.aragon@igac.gov.co"],
            "Gestión Administrativa": [""],
            "Gestión Documental": ["TESTgestiondocumental@igac.gov.co"],
            "Infraestructura": ["TESTserviadministrativo@igac.gov.co"],
            "Operación Logística": ["TESTopl@igac.gov.co"],
            "Presupuesto": ["TESTdianap.carvajal@igac.gov.co"],
            "Seguros y Transporte Especial": ["TESTtransporte@igac.gov.co"],
            "Tesorería": ["TESTmdevia@igac.gov.co"],
            "Viáticos": ["TESTtiquetes@igac.gov.co"]
        }
        
        # Get responsibles for the process
        responsables = responsables_map.get(proceso, [])
        
        # If no specific responsibles, assign general area coordinator
        if not responsables:
            if area == "Subdirección Administrativa y Financiera":
                responsables = ["coordinador.administrativa@igac.gov.co"]
            else:
                responsables = ["admin.general@igac.gov.co"]
        
        return responsables
    
    def send_new_request_notification(self, datos_solicitud: Dict[str, Any], id_solicitud: str) -> bool:
        """Send notification for new request to responsibles and confirmation to requester"""
        if not self.email_enabled:
            print(f"[SIMULATION] Email notifications for request {id_solicitud}")
            print(f"- Area: {datos_solicitud['area']}")
            print(f"- Process: {datos_solicitud['proceso']}")
            print(f"- Type: {datos_solicitud['tipo']}")
            print(f"- Confirmation sent to: {datos_solicitud['email']}")
            return True
        
        try:
            # Get access token
            if not self.access_token:
                self.access_token = self._get_access_token()
            
            if not self.access_token:
                print("Failed to obtain email access token")
                return False
            
            successful_emails = 0
            failed_emails = 0
            
            # 1. Send notification to responsibles
            responsibles = self.get_responsables_email(
                datos_solicitud['area'],
                datos_solicitud['proceso'], 
                datos_solicitud['tipo']
            )
            
            subject_responsibles = f"🔔 Nueva Solicitud - {datos_solicitud['area']} (ID: {id_solicitud})"
            html_responsibles = self.get_new_request_template(datos_solicitud, id_solicitud)
            
            # Send to each responsible
            for email_responsible in responsibles:
                if self._send_email_graph(email_responsible, subject_responsibles, html_responsibles):
                    successful_emails += 1
                else:
                    failed_emails += 1
            
            # 2. Send confirmation to requester
            subject_confirmation = f"✅ Confirmación de Solicitud Recibida (ID: {id_solicitud})"
            html_confirmation = self.get_confirmation_template(datos_solicitud, id_solicitud)
            
            if self._send_email_graph(datos_solicitud['email'], subject_confirmation, html_confirmation):
                successful_emails += 1
            else:
                failed_emails += 1
            
            # Internal logging
            print(f"Email notifications sent: {successful_emails} successful, {failed_emails} failed")
            
            return successful_emails > 0
            
        except Exception as e:
            print(f"Email notification error: {e}")
            return False

    def send_status_update_notification(self, datos_solicitud: Dict[str, Any], 
                                    nuevo_estado: str, comentarios: str = "") -> bool:
        """Send status update notification to requester"""
        if not self.email_enabled:
            print(f"[SIMULATION] Status update email to: {datos_solicitud.get('email_solicitante', 'N/A')}")
            print(f"- New status: {nuevo_estado}")
            if comentarios:
                print(f"- Comments: {comentarios[:50]}...")
            return True
        
        try:
            # Get access token
            if not self.access_token:
                self.access_token = self._get_access_token()
            
            if not self.access_token:
                print("Failed to obtain email access token")
                return False
            
            subject = f"🔄 Actualización de Solicitud (ID: {datos_solicitud['id_solicitud']})"
            html_body = self.get_status_update_template(datos_solicitud, nuevo_estado, comentarios)
            
            if self._send_email_graph(datos_solicitud['email_solicitante'], subject, html_body):
                print(f"Status update email sent to requester")
                return True
            else:
                print("Failed to send status update email")
                return False
            
        except Exception as e:
            print(f"Status update email error: {e}")
            return False

    def send_status_update_with_attachment(self, datos_solicitud: Dict[str, Any], 
                                        nuevo_estado: str, comentarios: str = "",
                                        attachment_data: bytes = None, attachment_name: str = None) -> bool:
        """Send status update notification with file attachment"""
        if not self.email_enabled:
            print(f"[SIMULATION] Status update email with attachment to: {datos_solicitud.get('email_solicitante', 'N/A')}")
            print(f"- New status: {nuevo_estado}")
            if comentarios:
                print(f"- Comments: {comentarios[:50]}...")
            if attachment_name:
                print(f"- Attachment: {attachment_name}")
            return True
        
        try:
            # Get access token
            if not self.access_token:
                self.access_token = self._get_access_token()
            
            if not self.access_token:
                print("Failed to obtain email access token")
                return False
            
            subject = f"🔄 Actualización de Solicitud con Archivo (ID: {datos_solicitud['id_solicitud']})"
            
            # Enhanced template for updates with attachments
            html_body = self.get_status_update_template_with_attachment(
                datos_solicitud, nuevo_estado, comentarios, attachment_name
            )
            
            # Send email with attachment
            if self._send_email_graph(
                datos_solicitud['email_solicitante'], 
                subject, 
                html_body, 
                attachment_data, 
                attachment_name
            ):
                print(f"Status update email with attachment sent to requester")
                return True
            else:
                print("Failed to send status update email with attachment")
                return False
            
        except Exception as e:
            print(f"Status update email with attachment error: {e}")
            return False

    def get_status_update_template_with_attachment(self, datos: Dict[str, Any], nuevo_estado: str, 
                                                comentarios: str, attachment_name: str = None) -> str:
        """HTML template for status update notification with attachment"""
        estado_emoji = {
            "Pendiente": "🟡",
            "En Proceso": "🔵", 
            "Completado": "✅",
            "Cancelado": "❌"
        }
        
        attachment_section = ""
        if attachment_name:
            attachment_section = f"""
            <div class="info-box">
                <h3>📎 Archivo Adjunto</h3>
                <p>Se ha adjuntado el archivo: <strong>{attachment_name}</strong></p>
                <p>Este archivo contiene información adicional relacionada con su solicitud.</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #17becf; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #17becf; }}
                .status-box {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔄 Actualización de Solicitud - IGAC</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <h3>📋 Información de la Solicitud</h3>
                        <p><strong>ID:</strong> {datos['id_solicitud']}</p>
                        <p><strong>Área:</strong> {datos.get('area', 'N/A')}</p>
                        <p><strong>Proceso:</strong> {datos.get('proceso', 'N/A')}</p>
                        <p><strong>Tipo:</strong> {datos['tipo_solicitud']}</p>
                        <p><strong>Fecha de Solicitud:</strong> {datos['fecha_solicitud'].strftime('%d/%m/%Y') if 'fecha_solicitud' in datos else 'N/A'}</p>
                    </div>
                    
                    <div class="status-box">
                        <h3>🎯 Nuevo Estado</h3>
                        <h2>{estado_emoji.get(nuevo_estado, '🔹')} {nuevo_estado}</h2>
                        <p><strong>Actualizado:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    {f'''
                    <div class="info-box">
                        <h3>💬 Comentarios</h3>
                        <p>{comentarios}</p>
                    </div>
                    ''' if comentarios else ''}
                    
                    {attachment_section}
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                </div>
            </div>
        </body>
        </html>
        """

    def _send_email_graph(self, to_email: str, subject: str, html_body: str, attachment_data: bytes = None, attachment_name: str = None) -> bool:
        """Send email using Microsoft Graph API with optional attachment"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Build message according to Graph API format
            email_message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ],
                    "from": {
                        "emailAddress": {
                            "address": self.sender_email
                        }
                    }
                }
            }
            
            # Add attachment if provided
            if attachment_data and attachment_name:
                import base64
                attachment_b64 = base64.b64encode(attachment_data).decode('utf-8')
                email_message["message"]["attachments"] = [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": attachment_name,
                        "contentBytes": attachment_b64
                    }
                ]
            
            # Send email using Graph API
            send_url = f"{self.graph_api_url}/users/{self.sender_email}/sendMail"
            response = requests.post(send_url, headers=headers, json=email_message)
            
            if response.status_code == 202:  # Accepted
                return True
            elif response.status_code == 401:
                print(f"Email token expired, attempting to refresh...")
                # Try to renew token
                self.access_token = self._get_access_token()
                if self.access_token:
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.post(send_url, headers=headers, json=email_message)
                    return response.status_code == 202
                return False
            elif response.status_code == 403:
                print(f"Insufficient permissions to send email to {to_email}")
                return False
            else:
                error_detail = "Unknown error"
                try:
                    error_info = response.json()
                    error_detail = error_info.get('error', {}).get('message', error_detail)
                except:
                    pass
                print(f"Email API error [{response.status_code}]: {error_detail}")
                return False
                
        except Exception as e:
            print(f"Email send error to {to_email}: {e}")
            return False
    
    def get_new_request_template(self, datos: Dict[str, Any], id_solicitud: str) -> str:
        """HTML template for new request notification to responsibles"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #0066cc; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .highlight {{ background: #e8f4f8; padding: 10px; border-radius: 5px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔔 Nueva Solicitud - IGAC</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <h3>📋 Detalles de la Solicitud</h3>
                        <p><strong>ID:</strong> {id_solicitud}</p>
                        <p><strong>Territorial:</strong> {datos['territorial']}</p>
                        <p><strong>Solicitante:</strong> {datos['nombre']}</p>
                        <p><strong>Email:</strong> {datos['email']}</p>
                        <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    <div class="highlight">
                        <h3>🏢 Clasificación</h3>
                        <p><strong>Área:</strong> {datos['area']}</p>
                        <p><strong>Proceso:</strong> {datos['proceso']}</p>
                        <p><strong>Tipo de Solicitud:</strong> {datos['tipo']}</p>
                        {f"<p><strong>Fecha Límite Deseada:</strong> {datos['fecha_limite'].strftime('%d/%m/%Y')}</p>" if datos.get('fecha_limite') else ""}
                    </div>
                    
                    <div class="info-box">
                        <h3>📝 Descripción</h3>
                        <p>{datos['descripcion']}</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>⚡ Acción Requerida</h3>
                        <p>Se ha registrado una nueva solicitud que requiere su atención. 
                        Por favor, acceda al sistema para revisar y gestionar esta solicitud.</p>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                    <p>Este es un mensaje automático.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def get_confirmation_template(self, datos: Dict[str, Any], id_solicitud: str) -> str:
        """HTML template for confirmation to requester - UPDATED with app link"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #28a745; }}
                .highlight-box {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; text-align: center; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .id-code {{ font-size: 18px; font-weight: bold; color: #0066cc; font-family: monospace; }}
                .app-link {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Solicitud Recibida - IGAC</h1>
                </div>
                <div class="content">
                    <div class="highlight-box">
                        <h2>¡Su solicitud ha sido recibida exitosamente!</h2>
                        <p>ID de seguimiento: <span class="id-code">{id_solicitud}</span></p>
                    </div>
                    
                    <div class="info-box">
                        <h3>📋 Resumen de su Solicitud</h3>
                        <p><strong>Territorial:</strong> {datos['territorial']}</p>
                        <p><strong>Solicitante:</strong> {datos['nombre']}</p>
                        <p><strong>Fecha de Solicitud:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                        <p><strong>Área:</strong> {datos['area']}</p>
                        <p><strong>Proceso:</strong> {datos['proceso']}</p>
                        <p><strong>Tipo:</strong> {datos['tipo']}</p>
                        {f"<p><strong>Fecha Límite Deseada:</strong> {datos['fecha_limite'].strftime('%d/%m/%Y')}</p>" if datos.get('fecha_limite') else ""}
                    </div>
                    
                    <div class="info-box">
                        <h3>📝 Su Descripción</h3>
                        <p><em>"{datos['descripcion']}"</em></p>
                    </div>
                    
                    <div class="info-box">
                        <h3>📞 Próximos Pasos</h3>
                        <ul>
                            <li>Su solicitud ha sido enviada al proceso {datos['proceso']} de {datos['area']}</li>
                            <li>Los responsables revisarán su solicitud y comenzarán a procesarla</li>
                            <li>Recibirá notificaciones por email cuando haya actualizaciones</li>
                            <li>Puede consultar el estado usando el ID: <strong>{id_solicitud}</strong></li>
                        </ul>
                    </div>
                    
                    <div class="info-box" style="text-align: center;">
                        <h3>🔍 Seguimiento de su Solicitud</h3>
                        <p>Para más información y seguimiento en tiempo real, visite:</p>
                        <a href="{APP_URL}" class="app-link">📱 App de Seguimiento de Solicitudes</a>
                        <p><small>Use su ID de solicitud: <strong>{id_solicitud}</strong> para hacer seguimiento</small></p>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                    <p>Guarde este email para futuras referencias. ID: {id_solicitud}</p>
                </div>
            </div>
        </body>
        </html>
        """

    def get_status_update_template(self, datos: Dict[str, Any], nuevo_estado: str, comentarios: str) -> str:
            """HTML template for status update notification - UPDATED with app link"""
            estado_emoji = {
                "Pendiente": "🟡",
                "En Proceso": "🔵", 
                "Completado": "✅",
                "Cancelado": "❌"
            }
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #17becf; color: white; padding: 20px; text-align: center; }}
                    .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                    .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #17becf; }}
                    .status-box {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                    .app-link {{ background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔄 Actualización de Solicitud - IGAC</h1>
                    </div>
                    <div class="content">
                        <div class="info-box">
                            <h3>📋 Información de la Solicitud</h3>
                            <p><strong>ID:</strong> {datos['id_solicitud']}</p>
                            <p><strong>Área:</strong> {datos.get('area', 'N/A')}</p>
                            <p><strong>Proceso:</strong> {datos.get('proceso', 'N/A')}</p>
                            <p><strong>Tipo:</strong> {datos['tipo_solicitud']}</p>
                            <p><strong>Fecha de Solicitud:</strong> {datos['fecha_solicitud'].strftime('%d/%m/%Y') if 'fecha_solicitud' in datos else 'N/A'}</p>
                        </div>
                        
                        <div class="status-box">
                            <h3>🎯 Nuevo Estado</h3>
                            <h2>{estado_emoji.get(nuevo_estado, '🔹')} {nuevo_estado}</h2>
                            <p><strong>Actualizado:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                        </div>
                        
                        {f'''
                        <div class="info-box">
                            <h3>💬 Comentarios</h3>
                            <p>{comentarios}</p>
                        </div>
                        ''' if comentarios else ''}
                        
                        <div class="info-box" style="text-align: center;">
                            <h3>🔍 Ver Detalles Completos</h3>
                            <p>Para más información y seguimiento detallado:</p>
                            <a href="{APP_URL}" class="app-link">📱 App de Seguimiento</a>
                            <p><small>Use su ID: <strong>{datos['id_solicitud']}</strong></small></p>
                        </div>
                    </div>
                    <div class="footer">
                        <p>Sistema de Gestión de Solicitudes - IGAC</p>
                    </div>
                </div>
            </body>
            </html>
            """

    def get_status_update_template_with_attachment(self, datos: Dict[str, Any], nuevo_estado: str, 
                                                comentarios: str, attachment_name: str = None) -> str:
        """HTML template for status update notification with attachment - UPDATED with app link"""
        estado_emoji = {
            "Pendiente": "🟡",
            "En Proceso": "🔵", 
            "Completado": "✅",
            "Cancelado": "❌"
        }
        
        attachment_section = ""
        if attachment_name:
            attachment_section = f"""
            <div class="info-box">
                <h3>📎 Archivo Adjunto</h3>
                <p>Se ha adjuntado el archivo: <strong>{attachment_name}</strong></p>
                <p>Este archivo contiene información adicional relacionada con su solicitud.</p>
            </div>
            """
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #17becf; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #17becf; }}
                .status-box {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .app-link {{ background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔄 Actualización de Solicitud - IGAC</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <h3>📋 Información de la Solicitud</h3>
                        <p><strong>ID:</strong> {datos['id_solicitud']}</p>
                        <p><strong>Área:</strong> {datos.get('area', 'N/A')}</p>
                        <p><strong>Proceso:</strong> {datos.get('proceso', 'N/A')}</p>
                        <p><strong>Tipo:</strong> {datos['tipo_solicitud']}</p>
                        <p><strong>Fecha de Solicitud:</strong> {datos['fecha_solicitud'].strftime('%d/%m/%Y') if 'fecha_solicitud' in datos else 'N/A'}</p>
                    </div>
                    
                    <div class="status-box">
                        <h3>🎯 Nuevo Estado</h3>
                        <h2>{estado_emoji.get(nuevo_estado, '🔹')} {nuevo_estado}</h2>
                        <p><strong>Actualizado:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    {f'''
                    <div class="info-box">
                        <h3>💬 Comentarios</h3>
                        <p>{comentarios}</p>
                    </div>
                    ''' if comentarios else ''}
                    
                    {attachment_section}
                    
                    <div class="info-box" style="text-align: center;">
                        <h3>🔍 Ver Detalles Completos</h3>
                        <p>Para más información y seguimiento detallado:</p>
                        <a href="{APP_URL}" class="app-link">📱 App de Seguimiento</a>
                        <p><small>Use su ID: <strong>{datos['id_solicitud']}</strong></small></p>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                </div>
            </div>
        </body>
        </html>
        """