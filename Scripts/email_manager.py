import requests
from typing import Dict, Any, Optional
import os
import streamlit as st
from shared_timezone_utils import obtener_fecha_actual_colombia, formatear_fecha_colombia

URL_APLICACION = "https://igac-requests-control-panel.streamlit.app/"

class GestorNotificacionesEmail:
    def __init__(self):
        """Inicializa el gestor de notificaciones por email"""
        # Configuración de Microsoft Graph API desde Streamlit secrets
        self.tenant_id = st.secrets["TENANT_ID"]
        self.client_id = st.secrets["CLIENT_ID"]
        self.client_secret = st.secrets["CLIENT_SECRET"]
        self.email_remitente = st.secrets["SENDER_EMAIL"]
        
        # URLs de la API
        self.url_token = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.url_graph_api = "https://graph.microsoft.com/v1.0"
        
        # Verificar si la configuración está completa
        self.email_habilitado = bool(self.tenant_id and self.client_id and self.client_secret and self.email_remitente)
        
        # Gestión de tokens
        self.token_acceso = None
        
        # Logging interno
        if self.email_habilitado:
            print("Servicio de email configurado exitosamente")
        else:
            print("Servicio de email no configurado - operando en modo simulación")
    
    def _obtener_token_acceso(self) -> Optional[str]:
        """Obtiene token de acceso de Microsoft Graph API"""
        try:
            datos_token = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            response = requests.post(self.url_token, data=datos_token, headers=headers)
            
            if response.status_code == 200:
                info_token = response.json()
                print("Token de email obtenido exitosamente")
                return info_token.get('access_token')
            else:
                detalle_error = response.json()
                print(f"Error en token de email: {detalle_error.get('error_description', 'Error desconocido')}")
                return None
                
        except Exception as e:
            print(f"Error en autenticación de email: {e}")
            return None

    def obtener_responsables_email(self, area: str, proceso: str, tipo_solicitud: str) -> list:
        """Obtiene emails de responsables basado en área y proceso"""
        # Mapeo de emails basado en área y proceso
        mapeo_responsables = {
            "Subdirección Administrativa y Financiera": {
                "Almacén": ["TESTalmacengeneral@igac.gov.co"],
                "Archivo": ["TESTgestiondocumental@igac.gov.co"],
                "Contabilidad": ["TESTdoris.aragon@igac.gov.co"],
                "Contractual": ["TESTcontratacion@igac.gov.co"],
                "Correspondencia": ["TESTgestiondocumental@igac.gov.co"],
                "Infraestructura": ["TESTserviadministrativo@igac.gov.co"],
                "Operación Logística SAF": ["TESTopl@igac.gov.co"],
                "Presupuesto": ["TESTdianap.carvajal@igac.gov.co"],
                "Tesorería": ["TESTmdevia@igac.gov.co"],
                "Tiquetes": ["TESTtiquetes@igac.gov.co"],
                "Transporte": ["TESTtransporte@igac.gov.co"]
            },
            "Oficina Asesora de Comunicaciones": {
                "Comunicación Externa": ["comunicaciones@igac.gov.co"],
                "Comunicación Interna": ["comunicacioninterna@igac.gov.co"]
            }
        }

        # Obtener responsables para el área y proceso
        responsables = []
        if area in mapeo_responsables and proceso in mapeo_responsables[area]:
            responsables = mapeo_responsables[area][proceso]

        # Si no hay responsables específicos, asignar coordinador
        if not responsables:
            responsables = ["juan.vallejo@igac.gov.co"]

        return responsables
    
    def enviar_notificacion_nueva_solicitud(self, datos_solicitud: Dict[str, Any], id_solicitud: str) -> bool:
        """Envía notificación de nueva solicitud a responsables y confirmación al solicitante"""
        if not self.email_habilitado:
            print(f"Notificaciones de email para solicitud {id_solicitud}")
            print(f"- Área: {datos_solicitud['area']}")
            print(f"- Proceso: {datos_solicitud['proceso']}")
            print(f"- Tipo: {datos_solicitud['tipo']}")
            print(f"- Confirmación enviada a: {datos_solicitud['email']}")
            return True
        
        try:
            # Obtener token de acceso
            if not self.token_acceso:
                self.token_acceso = self._obtener_token_acceso()
            
            if not self.token_acceso:
                print("Error al obtener token de acceso para email")
                return False
            
            emails_exitosos = 0
            emails_fallidos = 0
            
            # 1. Enviar notificación a responsables
            responsables = self.obtener_responsables_email(
                datos_solicitud['area'],
                datos_solicitud['proceso'], 
                datos_solicitud['tipo']
            )
            
            asunto_responsables = f"🔔 Nueva Solicitud - {datos_solicitud['area']} (ID: {id_solicitud})"
            html_responsables = self.obtener_plantilla_nueva_solicitud(datos_solicitud, id_solicitud)
            
            # Enviar a cada responsable
            for email_responsable in responsables:
                if self._enviar_email_graph(email_responsable, asunto_responsables, html_responsables):
                    emails_exitosos += 1
                else:
                    emails_fallidos += 1
            
            # 2. Enviar confirmación al solicitante
            asunto_confirmacion = f"✅ Confirmación de Solicitud Recibida (ID: {id_solicitud})"
            html_confirmacion = self.obtener_plantilla_confirmacion(datos_solicitud, id_solicitud)
            
            if self._enviar_email_graph(datos_solicitud['email'], asunto_confirmacion, html_confirmacion):
                emails_exitosos += 1
            else:
                emails_fallidos += 1
            
            # Logging interno
            print(f"Notificaciones de email enviadas: {emails_exitosos} exitosos, {emails_fallidos} fallidos")
            
            return emails_exitosos > 0
            
        except Exception as e:
            print(f"Error en notificación de email: {e}")
            return False

    def enviar_notificacion_actualizacion_solo_cambios(self, datos_solicitud: Dict[str, Any], 
                                                     cambios: Dict[str, Any], responsable: str = "", 
                                                     email_responsable: str = "") -> bool:
        """Envía notificación de actualización de estado con solo los campos modificados"""
        if not self.email_habilitado:
            print(f"Email de actualización solo cambios a: {datos_solicitud.get('email_solicitante', 'N/A')}")
            for tipo_cambio, datos_cambio in cambios.items():
                print(f"- {tipo_cambio}: {datos_cambio}")
            return True
        
        try:
            if not self.token_acceso:
                self.token_acceso = self._obtener_token_acceso()
            
            if not self.token_acceso:
                return False
            
            asunto = f"🔄 Actualización de Solicitud (ID: {datos_solicitud['id_solicitud']})"
            cuerpo_html = self.obtener_plantilla_solo_cambios(datos_solicitud, cambios, responsable, email_responsable)
            
            return self._enviar_email_graph(datos_solicitud['email_solicitante'], asunto, cuerpo_html)
            
        except Exception as e:
            print(f"Error en email de solo cambios: {e}")
            return False
    
    def enviar_actualizacion_estado_con_archivo_adjunto(self, datos_solicitud: Dict[str, Any], 
                                                      nuevo_estado: str, comentarios: str = "",
                                                      datos_archivo_adjunto: bytes = None, nombre_archivo_adjunto: str = None) -> bool:
        """Envía notificación de actualización de estado con archivo adjunto"""
        if not self.email_habilitado:
            print(f"Email de actualización de estado con archivo adjunto a: {datos_solicitud.get('email_solicitante', 'N/A')}")
            print(f"- Nuevo estado: {nuevo_estado}")
            if comentarios:
                print(f"- Comentarios: {comentarios[:50]}...")
            if nombre_archivo_adjunto:
                print(f"- Archivo adjunto: {nombre_archivo_adjunto}")
            return True
        
        try:
            # Obtener token de acceso
            if not self.token_acceso:
                self.token_acceso = self._obtener_token_acceso()
            
            if not self.token_acceso:
                print("Error al obtener token de acceso para email")
                return False
            
            asunto = f"🔄 Actualización de Solicitud con Archivo (ID: {datos_solicitud['id_solicitud']})"
            
            # Plantilla mejorada para actualizaciones con archivos adjuntos
            cuerpo_html = self.obtener_plantilla_actualizacion_estado_con_archivo_adjunto(
                datos_solicitud, nuevo_estado, comentarios, nombre_archivo_adjunto
            )
            
            # Enviar email con archivo adjunto
            if self._enviar_email_graph(
                datos_solicitud['email_solicitante'], 
                asunto, 
                cuerpo_html, 
                datos_archivo_adjunto, 
                nombre_archivo_adjunto
            ):
                print(f"Email de actualización de estado con archivo adjunto enviado al solicitante")
                return True
            else:
                print("Error al enviar email de actualización de estado con archivo adjunto")
                return False
            
        except Exception as e:
            print(f"Error en email de actualización de estado con archivo adjunto: {e}")
            return False

    def enviar_notificacion_responsable(self, datos_solicitud: Dict[str, Any], 
                                      cambios: Dict[str, Any], responsable: str = "", 
                                      email_responsable: str = "") -> bool:
        """Envía notificación a la persona responsable sobre cambios en la solicitud"""
        if not self.email_habilitado:
            print(f"Email de notificación de responsable a: {email_responsable}")
            for tipo_cambio, datos_cambio in cambios.items():
                print(f"- {tipo_cambio}: {datos_cambio}")
            return True
        
        try:
            if not self.token_acceso:
                self.token_acceso = self._obtener_token_acceso()
            
            if not self.token_acceso:
                return False
            
            asunto = f"📋 Asignación de Solicitud (ID: {datos_solicitud['id_solicitud']})"
            cuerpo_html = self.obtener_plantilla_notificacion_responsable(
                datos_solicitud, cambios, responsable, email_responsable
            )
            
            return self._enviar_email_graph(email_responsable, asunto, cuerpo_html)
            
        except Exception as e:
            print(f"Error en email de notificación de responsable: {e}")
            return False

    def _enviar_email_graph(self, email_destino: str, asunto: str, cuerpo_html: str, 
                           datos_archivo_adjunto: bytes = None, nombre_archivo_adjunto: str = None) -> bool:
        """Envía email usando Microsoft Graph API con archivo adjunto opcional"""
        try:
            headers = {
                'Authorization': f'Bearer {self.token_acceso}',
                'Content-Type': 'application/json'
            }
            
            # Construir mensaje según formato de Graph API
            mensaje_email = {
                "message": {
                    "subject": asunto,
                    "body": {
                        "contentType": "HTML",
                        "content": cuerpo_html
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": email_destino
                            }
                        }
                    ],
                    "from": {
                        "emailAddress": {
                            "address": self.email_remitente
                        }
                    }
                }
            }
            
            # Agregar archivo adjunto si se proporciona
            if datos_archivo_adjunto and nombre_archivo_adjunto:
                import base64
                archivo_adjunto_b64 = base64.b64encode(datos_archivo_adjunto).decode('utf-8')
                mensaje_email["message"]["attachments"] = [
                    {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": nombre_archivo_adjunto,
                        "contentBytes": archivo_adjunto_b64
                    }
                ]
            
            # Enviar email usando Graph API
            url_envio = f"{self.url_graph_api}/users/{self.email_remitente}/sendMail"
            response = requests.post(url_envio, headers=headers, json=mensaje_email)
            
            if response.status_code == 202:  # Aceptado
                return True
            elif response.status_code == 401:
                print(f"Token de email expirado, intentando renovar...")
                # Intentar renovar token
                self.token_acceso = self._obtener_token_acceso()
                if self.token_acceso:
                    headers['Authorization'] = f'Bearer {self.token_acceso}'
                    response = requests.post(url_envio, headers=headers, json=mensaje_email)
                    return response.status_code == 202
                return False
            elif response.status_code == 403:
                print(f"Permisos insuficientes para enviar email a {email_destino}")
                return False
            else:
                detalle_error = "Error desconocido"
                try:
                    info_error = response.json()
                    detalle_error = info_error.get('error', {}).get('message', detalle_error)
                except:
                    pass
                print(f"Error en API de email [{response.status_code}]: {detalle_error}")
                return False
                
        except Exception as e:
            print(f"Error al enviar email a {email_destino}: {e}")
            return False

    def obtener_plantilla_nueva_solicitud(self, datos: Dict[str, Any], id_solicitud: str) -> str:
        """Plantilla HTML para notificación de nueva solicitud a responsables"""
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
                        <p><strong>Fecha:</strong> {obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    <div class="highlight">
                        <h3>🏢 Clasificación</h3>
                        <p><strong>Área:</strong> {datos['area']}</p>
                        <p><strong>Proceso:</strong> {datos['proceso']}</p>
                        <p><strong>Tipo de Solicitud:</strong> {datos['tipo']}</p>
                        {f"<p><strong>Fecha Límite Deseada:</strong> {formatear_fecha_colombia(datos['fecha_limite'])}</p>" if datos.get('fecha_limite') else ""}
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
    
    def obtener_plantilla_confirmacion(self, datos: Dict[str, Any], id_solicitud: str) -> str:
        """Plantilla HTML para confirmación al solicitante con información de acceso a archivos"""
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
                        <p><strong>Fecha de Solicitud:</strong> {obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M')}</p>
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
                            <li><strong>📎 Archivos adjuntos:</strong> Estarán disponibles en la App de Seguimiento</li>
                        </ul>
                    </div>
                    
                    <div class="info-box" style="text-align: center; background: #f0f8ff;">
                        <h3>🔍 Seguimiento de su Solicitud</h3>
                        <p>Para consultar el estado, ver comentarios y <strong>descargar archivos adjuntos:</strong></p>
                        <a href="{URL_APLICACION}" class="app-link">📱 App de Seguimiento de Solicitudes</a>
                        <p><strong>Su ID de seguimiento:</strong> <span class="id-code">{id_solicitud}</span></p>
                        <div style="background: #e3f2fd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                            <p><strong>💡 Cómo hacer seguimiento:</strong></p>
                            <ol style="text-align: left; display: inline-block;">
                                <li>Visite la App de Seguimiento</li>
                                <li>Vaya a la pestaña <strong>"🔍 Seguimiento"</strong></li>
                                <li>Ingrese su ID: <strong>{id_solicitud}</strong></li>
                                <li>Vea el estado, comentarios y descargue archivos</li>
                            </ol>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                    <p>Guarde este email para futuras referencias. ID: {id_solicitud}</p>
                    <p>📧 Este es un mensaje automático. No responda a este correo.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def obtener_plantilla_actualizacion_estado_con_archivo_adjunto(self, datos: Dict[str, Any], nuevo_estado: str, 
                                                                 comentarios: str, nombre_archivo_adjunto: str = None) -> str:
        """Plantilla HTML para notificación de actualización de estado con archivo adjunto y enlace a la app"""
        emojis_estado = {
        "Asignada": "🟡",
        "En Proceso": "🔵", 
        "Incompleta": "🟠",
        "Completada": "✅",
        "Cancelada": "❌"
        }
        
        seccion_archivo_adjunto = ""
        if nombre_archivo_adjunto:
            seccion_archivo_adjunto = f"""
            <div class="info-box">
                <h3>📎 Archivo Adjunto</h3>
                <p>Se ha adjuntado el archivo: <strong>{nombre_archivo_adjunto}</strong></p>
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
                        <h2>{emojis_estado.get(nuevo_estado, '🔹')} {nuevo_estado}</h2>
                        <p><strong>Actualizado:</strong> {obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    {f'''
                    <div class="info-box">
                        <h3>💬 Comentarios</h3>
                        <p>{comentarios}</p>
                    </div>
                    ''' if comentarios else ''}
                    
                    {seccion_archivo_adjunto}
                    
                    <div class="info-box" style="text-align: center;">
                        <h3>🔍 Ver Detalles Completos</h3>
                        <p>Para más información y seguimiento detallado:</p>
                        <a href="{URL_APLICACION}" class="app-link">📱 App de Seguimiento</a>
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
    
    def obtener_plantilla_solo_cambios(self, datos: Dict[str, Any], cambios: Dict[str, Any], 
                                      responsable: str = "", email_responsable: str = "") -> str:
        """Plantilla HTML mostrando solo los campos modificados con información de acceso a archivos en la app"""
        
        # Construir sección de cambios
        html_cambios = ""
        
        if 'estado' in cambios:
            emojis_estado = {
                "Asignada": "🟡", 
                "En Proceso": "🔵", 
                "Incompleta": "🟠", 
                "Completada": "✅", 
                "Cancelada": "❌"
            }
            emoji_anterior = emojis_estado.get(cambios['estado']['old'], '🔹')
            emoji_nuevo = emojis_estado.get(cambios['estado']['new'], '🔹')
            
            html_cambios += f"""
            <div class="change-box">
                <h3>📊 Estado Actualizado</h3>
                <p><strong>Anterior:</strong> {emoji_anterior} {cambios['estado']['old']}</p>
                <p><strong>Nuevo:</strong> {emoji_nuevo} {cambios['estado']['new']}</p>
            </div>
            """
        
        if 'prioridad' in cambios:
            html_cambios += f"""
            <div class="change-box">
                <h3>🎯 Prioridad Actualizada</h3>
                <p><strong>Anterior:</strong> {cambios['prioridad']['old']}</p>
                <p><strong>Nueva:</strong> {cambios['prioridad']['new']}</p>
            </div>
            """
        
        if 'responsable' in cambios:
            html_cambios += f"""
            <div class="change-box">
                <h3>👤 Responsable Asignado</h3>
                <p><strong>Nuevo responsable:</strong> {cambios['responsable']['new']}</p>
                {f"<p><strong>Email:</strong> {email_responsable}</p>" if email_responsable else ""}
            </div>
            """
        
        if 'comentario' in cambios:
            html_cambios += f"""
            <div class="change-box">
                <h3>💬 Nuevo Comentario</h3>
                <p><em>"{cambios['comentario']['new']}"</em></p>
                {f"<p><strong>Por:</strong> {responsable}</p>" if responsable else ""}
            </div>
            """
        
        if 'archivos' in cambios:
            lista_archivos = ', '.join(cambios['archivos']['new'])
            cantidad_archivos = len(cambios['archivos']['new'])
            html_cambios += f"""
            <div class="change-box">
                <h3>📎 Archivos Adjuntos</h3>
                <p><strong>Nuevos archivos subidos ({cantidad_archivos}):</strong> {lista_archivos}</p>
                <div style="background: #e3f2fd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                    <p><strong>📱 Para acceder a los archivos:</strong></p>
                    <ol>
                        <li>Visite la <strong>App de Seguimiento de Solicitudes</strong></li>
                        <li>Vaya a la pestaña <strong>"🔍 Seguimiento"</strong></li>
                        <li>Ingrese su ID de solicitud: <strong>{datos['id_solicitud']}</strong></li>
                        <li>Los archivos aparecerán en la sección <strong>"📎 Archivos Adjuntos"</strong></li>
                    </ol>
                    <p><em>💡 Los archivos están disponibles para descarga las 24 horas del día.</em></p>
                </div>
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
                .change-box {{ background: #e8f5e8; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #28a745; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .app-link {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; font-weight: bold; }}
                .app-link:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔄 Actualización de Solicitud - IGAC</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <h3>📋 Solicitud</h3>
                        <p><strong>ID:</strong> {datos['id_solicitud']}</p>
                        <p><strong>Proceso:</strong> {datos.get('proceso', 'N/A')}</p>
                        <p><strong>Actualizado:</strong> {obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                    
                    <h3>🔄 Cambios Realizados:</h3>
                    {html_cambios}
                    
                    <div class="info-box" style="text-align: center; background: #f0f8ff;">
                        <h3>🔍 Ver Detalles Completos y Archivos</h3>
                        <p>Para acceder a toda la información de su solicitud y descargar archivos:</p>
                        <a href="{URL_APLICACION}" class="app-link">📱 App de Seguimiento de Solicitudes</a>
                        <p><strong>Su ID de seguimiento:</strong> <span style="font-family: monospace; background: #e8e8e8; padding: 2px 6px; border-radius: 3px;">{datos['id_solicitud']}</span></p>
                        <p><small>💡 En la pestaña "🔍 Seguimiento" podrá ver el historial completo y descargar todos los archivos adjuntos.</small></p>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                    <p>📧 Este es un mensaje automático. No responda a este correo.</p>
                </div>
            </div>
        </body>
        </html>
        """

    def obtener_plantilla_notificacion_responsable(self, datos: Dict[str, Any], 
                                                  cambios: Dict[str, Any], responsable: str, 
                                                  email_responsable: str) -> str:
        """Plantilla HTML para notificación a la persona responsable"""
        
        # Construir sección de cambios
        html_cambios = ""
        
        if 'estado' in cambios:
            emojis_estado = {
                "Asignada": "🟡", 
                "En Proceso": "🔵", 
                "Incompleta": "🟠",
                "Completada": "✅", 
                "Cancelada": "❌"
            }
            emoji_nuevo = emojis_estado.get(cambios['estado']['new'], '🔹')
            html_cambios += f"""
            <div class="status-box">
                <h3>📊 Estado Actual</h3>
                <h2>{emoji_nuevo} {cambios['estado']['new']}</h2>
            </div>
            """
        
        if 'comentario' in cambios:
            html_cambios += f"""
            <div class="info-box">
                <h3>💬 Comentarios del Administrador</h3>
                <p><em>"{cambios['comentario']['new']}"</em></p>
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
                .header {{ background: #0066cc; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .info-box {{ background: white; padding: 15px; margin: 10px 0; border-left: 4px solid #0066cc; }}
                .status-box {{ background: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                .app-link {{ background: #007bff; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Solicitud Asignada - IGAC</h1>
                </div>
                <div class="content">
                    <div class="info-box">
                        <h3>👋 Hola {responsable or email_responsable}</h3>
                        <p>Se le ha asignado la siguiente solicitud para su gestión:</p>
                    </div>
                    
                    <div class="info-box">
                        <h3>📋 Detalles de la Solicitud</h3>
                        <p><strong>ID:</strong> {datos['id_solicitud']}</p>
                        <p><strong>Solicitante:</strong> {datos.get('nombre_solicitante', 'N/A')}</p>
                        <p><strong>Email:</strong> {datos['email_solicitante']}</p>
                        <p><strong>Proceso:</strong> {datos.get('proceso', 'N/A')}</p>
                        <p><strong>Tipo:</strong> {datos['tipo_solicitud']}</p>
                        <p><strong>Fecha:</strong> {formatear_fecha_colombia(datos['fecha_solicitud']) if 'fecha_solicitud' in datos else 'N/A'}</p>
                    </div>
                    
                    {html_cambios}
                    
                    <div class="info-box">
                        <h3>⚡ Próximos Pasos</h3>
                        <ul>
                            <li>Revise los detalles de la solicitud</li>
                            <li>Coordine la respuesta según sus procesos internos</li>
                            <li>Mantenga actualizado el estado cuando sea necesario</li>
                            <li>Contacte al solicitante si requiere información adicional</li>
                        </ul>
                    </div>
                    
                    <div class="info-box" style="text-align: center;">
                        <h3>🔍 Acceder al Sistema</h3>
                        <p>Para gestionar esta solicitud:</p>
                        <a href="{URL_APLICACION}" class="app-link">📱 Sistema de Gestión</a>
                        <p><small>Use el ID: <strong>{datos['id_solicitud']}</strong></small></p>
                    </div>
                </div>
                <div class="footer">
                    <p>Sistema de Gestión de Solicitudes - IGAC</p>
                    <p>Si tiene preguntas, contacte al administrador del sistema.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
