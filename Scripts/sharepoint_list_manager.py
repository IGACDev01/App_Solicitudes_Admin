import pandas as pd
import os
import streamlit as st
import uuid
from datetime import datetime, timedelta
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from timezone_utils import now_colombia, to_colombia, to_utc_for_storage

class SharePointListManager:
    def __init__(self, list_name: str = "Data App Solicitudes"):
        """Initialize SharePoint List Manager"""
        self.list_name = list_name
        self.df = None
        
        # SharePoint/Graph API configuration
        self.graph_config = self._load_graph_config()
        self.access_token = None
        self.token_expires_at = None
        
        # SharePoint connection info
        self.sharepoint_site_id = None
        self.list_id = None
        self.target_drive_id = None
        
        # Validate configuration
        if not self._validate_sharepoint_config():
            st.error("❌ SharePoint configuration incomplete. Check your environment variables.")
            st.stop()
        
        # Initialize connection
        self._initialize_sharepoint_connection()
    
    def _validate_sharepoint_config(self) -> bool:
        """Validate SharePoint configuration"""
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'sharepoint_site_url']
        missing_fields = [field for field in required_fields if not self.graph_config.get(field)]
        
        if missing_fields:
            print(f"Missing SharePoint configuration: {', '.join(missing_fields)}")
            return False
        
        return True

    def _load_graph_config(self) -> Dict[str, str]:
        """Load Graph API configuration from environment"""
        try:
            from dotenv import load_dotenv
            load_dotenv("Scripts/email.env")
        except:
            pass
        
        return {
            'tenant_id': os.getenv("TENANT_ID", ""),
            'client_id': os.getenv("CLIENT_ID", ""),
            'client_secret': os.getenv("CLIENT_SECRET", ""),
            'graph_url': "https://graph.microsoft.com/v1.0",
            'sharepoint_site_url': os.getenv("SHAREPOINT_SITE_URL", "")
        }
    
    def _get_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API"""
        if (hasattr(self, '_cached_token') and hasattr(self, '_token_expires_at') and 
            datetime.now() < self._token_expires_at):
            return self._cached_token
        
        try:
            token_url = f"https://login.microsoftonline.com/{self.graph_config['tenant_id']}/oauth2/v2.0/token"
            
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': self.graph_config['client_id'],
                'client_secret': self.graph_config['client_secret'],
                'scope': 'https://graph.microsoft.com/.default'
            }
            
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            
            response = requests.post(token_url, data=token_data, headers=headers)
            
            if response.status_code == 200:
                token_info = response.json()
                access_token = token_info.get('access_token')
                expires_in = token_info.get('expires_in', 3600)
                
                self._cached_token = access_token
                self._token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)
                
                print("SharePoint token obtained successfully")
                return access_token
            else:
                error_info = response.json()
                print(f"SharePoint authentication failed: {error_info.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"SharePoint authentication error: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Graph API requests"""
        token = self._get_access_token()
        if not token:
            return {}
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _get_sharepoint_site_id(self) -> Optional[str]:
        """Get SharePoint site ID"""
        if hasattr(self, '_cached_site_id'):
            return self._cached_site_id
            
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return None
            
            site_url = self.graph_config['sharepoint_site_url']
            
            if site_url.startswith('https://'):
                site_url = site_url[8:]
            
            parts = site_url.split('/')
            hostname = parts[0]
            site_path = '/'.join(parts[1:]) if len(parts) > 1 else ''
            
            if site_path:
                encoded_path = quote(site_path, safe='')
                url = f"{self.graph_config['graph_url']}/sites/{hostname}:/{encoded_path}"
            else:
                url = f"{self.graph_config['graph_url']}/sites/{hostname}"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                site_info = response.json()
                self._cached_site_id = site_info['id']
                print(f"Connected to SharePoint site: {site_url}")
                return self._cached_site_id
            else:
                print(f"Failed to get SharePoint site: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting SharePoint site ID: {e}")
            return None
    
    def _get_list_id(self) -> Optional[str]:
        """Get SharePoint list ID"""
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return None
            
            site_id = self._get_sharepoint_site_id()
            if not site_id:
                return None
            
            # Get list by name
            lists_url = f"{self.graph_config['graph_url']}/sites/{site_id}/lists"
            response = requests.get(lists_url, headers=headers)
            
            if response.status_code == 200:
                lists_data = response.json()
                
                for list_item in lists_data.get('value', []):
                    if list_item.get('displayName') == self.list_name:
                        list_id = list_item['id']
                        print(f"Found SharePoint list: {self.list_name}")
                        return list_id
                
                print(f"List '{self.list_name}' not found")
                return None
            else:
                print(f"Failed to get lists: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error getting list ID: {e}")
            return None

    def _get_target_drive_id(self) -> Optional[str]:
        """Get the Sistema_Gestion_Solicitudes drive ID"""
        if hasattr(self, '_cached_target_drive_id'):
            return self._cached_target_drive_id
            
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return None
            
            site_id = self._get_sharepoint_site_id()
            if not site_id:
                return None
            
            # Get all drives in the site
            drives_url = f"{self.graph_config['graph_url']}/sites/{site_id}/drives"
            response = requests.get(drives_url, headers=headers)
            
            if response.status_code == 200:
                drives_data = response.json()
                drives = drives_data.get('value', [])
                
                # Look for Sistema_Gestion_Solicitudes drive - exact match first
                for drive in drives:
                    if drive.get('name') == 'Sistema_Gestion_Solicitudes':
                        self._cached_target_drive_id = drive['id']
                        print(f"✅ Found target drive: {drive['name']}")
                        return self._cached_target_drive_id
                
                # Look for partial match
                for drive in drives:
                    if 'Sistema_Gestion_Solicitudes' in drive.get('name', ''):
                        self._cached_target_drive_id = drive['id']
                        print(f"✅ Found target drive (partial): {drive['name']}")
                        return self._cached_target_drive_id
                
                # Fallback to Documents library
                for drive in drives:
                    if drive.get('name') == 'Documents':
                        self._cached_target_drive_id = drive['id']
                        print(f"📁 Using Documents library as fallback")
                        return self._cached_target_drive_id
                        
                print("❌ Could not find suitable drive")
                return None
            else:
                print(f"❌ Failed to get drives: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting target drive ID: {e}")
            return None
    
    def _initialize_sharepoint_connection(self):
        """Initialize SharePoint connection"""
        print(f"Initializing connection to SharePoint list '{self.list_name}'...")
        
        site_id = self._get_sharepoint_site_id()
        if not site_id:
            st.error("❌ Failed to connect to SharePoint site")
            st.stop()
        
        self.sharepoint_site_id = site_id
        
        list_id = self._get_list_id()
        if not list_id:
            st.error(f"❌ SharePoint list '{self.list_name}' not found")
            st.stop()
        
        self.list_id = list_id
        
        # Get target drive for file uploads
        target_drive_id = self._get_target_drive_id()
        if target_drive_id:
            self.target_drive_id = target_drive_id
        else:
            print("⚠️ Target drive not found, file uploads may fail")
        
        print(f"Connected to SharePoint list: {self.list_name}")
        
        # Load initial data
        self.load_data()
    
    def _normalize_datetime(self, dt) -> Optional[datetime]:
        """Normalize datetime to timezone-naive for consistent handling - UPDATED"""
        if dt is None:
            return None
        
        try:
            # Use timezone utility for consistency
            return to_colombia(dt)
        except Exception as e:
            print(f"Error normalizing datetime {dt}: {e}")
            return None
    
    def load_data(self, force_reload: bool = True):
        """Load data from SharePoint List"""
        try:
            if not self.list_id:
                print("No list ID available")
                return
            
            headers = self._get_headers()
            if not headers.get('Authorization'):
                print("No SharePoint authorization")
                return
            
            # Get all list items with expanded fields
            items_url = f"{self.graph_config['graph_url']}/sites/{self.sharepoint_site_id}/lists/{self.list_id}/items"
            
            # Add query parameters to get field values
            params = {
                '$expand': 'fields',
                '$top': 5000  # Adjust as needed
            }
            
            response = requests.get(items_url, headers=headers, params=params)
            
            if response.status_code == 200:
                items_data = response.json()
                items = items_data.get('value', [])
                
                if not items:
                    print("SharePoint list is empty")
                    self.df = self.create_empty_dataframe()
                    return
                
                # Convert SharePoint list items to DataFrame
                rows = []
                for item in items:
                    fields = item.get('fields', {})
                    
                    # Map SharePoint fields to your DataFrame columns - with timezone normalization
                    row = {
                        'id_solicitud': fields.get('IDSolicitud', ''),
                        'territorial': fields.get('Territorial', ''),
                        'nombre_solicitante': fields.get('NombreSolicitante', ''),
                        'email_solicitante': fields.get('EmailSolicitante', ''),
                        'fecha_solicitud': self._normalize_datetime(self._parse_date(fields.get('FechaSolicitud'))),
                        'tipo_solicitud': fields.get('TipoSolicitud', ''),
                        'area': fields.get('Area', ''),
                        'proceso': fields.get('Proceso', ''),
                        'prioridad': fields.get('Prioridad', 'Por definir'),
                        'descripcion': fields.get('Descripcion', ''),
                        'estado': fields.get('Estado', 'Asignada'),
                        'responsable_asignado': fields.get('ResponsableAsignado', ''),
                        'fecha_actualizacion': self._normalize_datetime(self._parse_date(fields.get('FechaActualizacion'))),
                        'fecha_completado': self._normalize_datetime(self._parse_date(fields.get('FechaCompletado'))),
                        'comentarios_admin': fields.get('ComentariosAdmin', ''),
                        'tiempo_respuesta_dias': fields.get('TiempoRespuestaDias', 0),
                        'tiempo_resolucion_dias': fields.get('TiempoResolucionDias', 0),
                        'sharepoint_id': item.get('id', '')  # Store SharePoint internal ID
                    }
                    rows.append(row)
                
                self.df = pd.DataFrame(rows)
                print(f"Successfully loaded {len(self.df)} items from SharePoint list")
                
            else:
                print(f"Failed to load list items: {response.status_code}")
                self.df = self.create_empty_dataframe()
                
        except Exception as e:
            print(f"Error loading data from SharePoint list: {e}")
            self.df = self.create_empty_dataframe()
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse SharePoint date string to datetime"""
        if not date_str:
            return None
        
        try:
            # SharePoint returns ISO format: 2023-12-01T10:30:00Z
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}")
            return None
    
    def add_request(self, datos_solicitud: Dict[str, Any]) -> Optional[str]:
        """Add new request to SharePoint List"""
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return None
            
            # Generate unique ID
            id_solicitud = str(uuid.uuid4())[:8].upper()
            
            # Prepare SharePoint list item
            current_time_utc = to_utc_for_storage(now_colombia()).isoformat() + 'Z'
            
            list_item = {
                'fields': {
                    'IDSolicitud': id_solicitud,
                    'Territorial': datos_solicitud['territorial'],
                    'NombreSolicitante': datos_solicitud['nombre'],
                    'EmailSolicitante': datos_solicitud['email'],
                    'FechaSolicitud': current_time_utc,
                    'TipoSolicitud': datos_solicitud['tipo'],
                    'Area': datos_solicitud['area'],
                    'Proceso': datos_solicitud['proceso'],
                    'Prioridad': datos_solicitud.get('prioridad', 'Por definir'),
                    'Descripcion': datos_solicitud['descripcion'],
                    'Estado': 'Asignada',
                    'ResponsableAsignado': '',
                    'FechaActualizacion': current_time_utc,
                    'TiempoRespuestaDias': 0,
                    'TiempoResolucionDias': 0
                }
            }
            
            # Add optional fields
            if datos_solicitud.get('fecha_limite'):
                list_item['fields']['FechaNecesaria'] = datos_solicitud['fecha_limite'].isoformat()
            
            # Create list item
            create_url = f"{self.graph_config['graph_url']}/sites/{self.sharepoint_site_id}/lists/{self.list_id}/items"
            
            response = requests.post(create_url, headers=headers, json=list_item)
            
            if response.status_code == 201:
                print(f"New request created in SharePoint list: {id_solicitud}")
                
                # Reload data to include new item
                self.load_data()
                return id_solicitud
            else:
                error_detail = response.text
                print(f"Failed to create list item: {response.status_code} - {error_detail}")
                return None
                
        except Exception as e:
            print(f"Error adding request to SharePoint list: {e}")
            return None
    
    def update_request_status(self, id_solicitud: str, nuevo_estado: str, 
                            responsable: str = "", comentarios: str = "") -> bool:
        """Update request status in SharePoint List - FIXED timezone handling"""
        try:
            # Find the SharePoint item
            sharepoint_id = self._get_sharepoint_item_id(id_solicitud)
            if not sharepoint_id:
                print(f"SharePoint item not found for ID: {id_solicitud}")
                return False
            
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return False
            
            current_time_utc = to_utc_for_storage(now_colombia()).isoformat() + 'Z'
            
            # Prepare update data
            update_data = {
                'Estado': nuevo_estado,
                'FechaActualizacion': current_time_utc
            }
            
            if responsable:
                update_data['ResponsableAsignado'] = responsable
            
            if comentarios:
                update_data['ComentariosAdmin'] = comentarios
            
            # Handle completion
            if nuevo_estado == 'Completado':
                update_data['FechaCompletado'] = current_time_utc
                
                # Calculate resolution time
                original_item = self.get_request_by_id(id_solicitud)
                if not original_item.empty:
                    fecha_solicitud = original_item.iloc[0]['fecha_solicitud']
                    if pd.notna(fecha_solicitud):
                        # Normalize both dates to timezone-naive
                        fecha_solicitud_colombia = to_colombia(fecha_solicitud)
                        fecha_actual_norm = now_colombia()
                        
                        if fecha_solicitud_colombia:
                            tiempo_resolucion = (fecha_actual_norm - fecha_solicitud_colombia).total_seconds() / (24 * 3600)
                            update_data['TiempoResolucionDias'] = round(tiempo_resolucion, 2)
            
            # Calculate response time if this is the first update - FIXED timezone handling
            if nuevo_estado != 'Asignada':
                original_item = self.get_request_by_id(id_solicitud)
                if not original_item.empty:
                    current_response_time = original_item.iloc[0].get('tiempo_respuesta_dias', 0)
                    if current_response_time == 0:
                        fecha_solicitud = original_item.iloc[0]['fecha_solicitud']
                        if pd.notna(fecha_solicitud):
                            # Normalize both dates to timezone-naive
                            fecha_solicitud_colombia = to_colombia(fecha_solicitud)
                            fecha_actual_norm = now_colombia()
                            
                            if fecha_solicitud_colombia:
                                tiempo_respuesta = (fecha_actual_norm - fecha_solicitud_colombia).total_seconds() / (24 * 3600)
                                update_data['TiempoRespuestaDias'] = round(tiempo_respuesta, 2)
            
            # Update SharePoint list item
            update_url = f"{self.graph_config['graph_url']}/sites/{self.sharepoint_site_id}/lists/{self.list_id}/items/{sharepoint_id}/fields"
            
            response = requests.patch(update_url, headers=headers, json=update_data)
            
            if response.status_code in [200, 204]:
                print(f"Request {id_solicitud} updated successfully")
                return True
            else:
                print(f"Failed to update request: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error updating request status: {e}")
            return False
    
    def update_request_priority(self, id_solicitud: str, nueva_prioridad: str) -> bool:
        """Update request priority in SharePoint List"""
        try:
            # Find the SharePoint item
            sharepoint_id = self._get_sharepoint_item_id(id_solicitud)
            if not sharepoint_id:
                print(f"SharePoint item not found for ID: {id_solicitud}")
                return False
            
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return False
            
            current_time_utc = to_utc_for_storage(now_colombia()).isoformat() + 'Z'
            
            # Prepare update data
            update_data = {
                'Prioridad': nueva_prioridad,
                'FechaActualizacion': current_time_utc
            }
            
            # Update SharePoint list item
            update_url = f"{self.graph_config['graph_url']}/sites/{self.sharepoint_site_id}/lists/{self.list_id}/items/{sharepoint_id}/fields"
            
            response = requests.patch(update_url, headers=headers, json=update_data)
            
            if response.status_code in [200, 204]:
                print(f"Request {id_solicitud} priority updated to {nueva_prioridad}")
                return True
            else:
                print(f"Failed to update priority: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error updating request priority: {e}")
            return False
    
    def _get_sharepoint_item_id(self, id_solicitud: str) -> Optional[str]:
        """Get SharePoint internal item ID from custom ID"""
        if self.df is None or self.df.empty:
            return None
        
        matching_items = self.df[self.df['id_solicitud'] == id_solicitud]
        if matching_items.empty:
            return None
        
        return matching_items.iloc[0].get('sharepoint_id')
    
    # ============================================
    # FILE UPLOAD METHODS
    # ============================================
    
    def upload_attachment_to_item(self, id_solicitud: str, file_data: bytes, file_name: str) -> bool:
        """Upload file attachment for a specific request"""
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                print("❌ No authorization token")
                return False
            
            if not self.target_drive_id:
                print("❌ No target drive available")
                return False
            
            # Step 1: Ensure "Archivos Adjuntos" folder exists
            if not self._ensure_archivos_adjuntos_folder():
                print("❌ Could not create/verify 'Archivos Adjuntos' folder")
                return False
            
            # Step 2: Create request-specific subfolder
            if not self._create_request_subfolder(id_solicitud):
                print(f"❌ Could not create subfolder for {id_solicitud}")
                return False
            
            # Step 3: Upload file to the subfolder
            file_path = f"Archivos Adjuntos/{id_solicitud}/{file_name}"
            
            upload_url = f"{self.graph_config['graph_url']}/drives/{self.target_drive_id}/root:/{file_path}:/content"
            
            upload_headers = {
                'Authorization': headers['Authorization'],
                'Content-Type': 'application/octet-stream'
            }
            
            response = requests.put(upload_url, headers=upload_headers, data=file_data)
            
            if response.status_code in [200, 201]:
                print(f"✅ File uploaded: {file_name} to {id_solicitud}")
                return True
            else:
                print(f"❌ Upload failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error uploading attachment: {e}")
            return False
    
    def _ensure_archivos_adjuntos_folder(self) -> bool:
        """Ensure 'Archivos Adjuntos' folder exists in root"""
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return False
            
            # Create folder in root - use replace to avoid conflicts
            create_url = f"{self.graph_config['graph_url']}/drives/{self.target_drive_id}/root/children"
            
            folder_data = {
                "name": "Archivos Adjuntos",
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"  # Don't fail if exists
            }
            
            response = requests.post(create_url, headers=headers, json=folder_data)
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"❌ Failed to ensure 'Archivos Adjuntos' folder: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error ensuring base folder: {e}")
            return False
    
    def _create_request_subfolder(self, id_solicitud: str) -> bool:
        """Create subfolder for specific request"""
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return False
            
            # Create subfolder under "Archivos Adjuntos"
            subfolder_url = f"{self.graph_config['graph_url']}/drives/{self.target_drive_id}/root:/Archivos Adjuntos:/children"
            
            subfolder_data = {
                "name": id_solicitud,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"  # Don't fail if exists
            }
            
            response = requests.post(subfolder_url, headers=headers, json=subfolder_data)
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"❌ Failed to create subfolder {id_solicitud}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating request subfolder: {e}")
            return False
    
    def get_request_attachments(self, id_solicitud: str) -> List[Dict[str, Any]]:
        """Get all attachments for a specific request"""
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                return []
            
            if not self.target_drive_id:
                return []
            
            # Get files from request subfolder
            folder_path = f"Archivos Adjuntos/{id_solicitud}"
            files_url = f"{self.graph_config['graph_url']}/drives/{self.target_drive_id}/root:/{folder_path}:/children"
            
            response = requests.get(files_url, headers=headers)
            
            if response.status_code == 200:
                files_data = response.json()
                files = []
                for item in files_data.get('value', []):
                    if 'file' in item:  # It's a file, not a folder
                        files.append({
                            'name': item['name'],
                            'id': item['id'],
                            'download_url': item.get('@microsoft.graph.downloadUrl', ''),
                            'size': item.get('size', 0),
                            'created': item.get('createdDateTime', ''),
                            'modified': item.get('lastModifiedDateTime', ''),
                            'web_url': item.get('webUrl', '')
                        })
                return files
            else:
                # Folder doesn't exist or no files
                return []
                
        except Exception as e:
            print(f"❌ Error getting attachments for {id_solicitud}: {e}")
            return []
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def create_empty_dataframe(self) -> pd.DataFrame:
        """Create empty DataFrame with proper structure"""
        return pd.DataFrame(columns=[
            'id_solicitud', 'territorial', 'nombre_solicitante', 'email_solicitante',
            'fecha_solicitud', 'tipo_solicitud', 'area', 'proceso', 'prioridad',
            'descripcion', 'estado', 'responsable_asignado', 'fecha_actualizacion',
            'fecha_completado', 'comentarios_admin', 'tiempo_respuesta_dias',
            'tiempo_resolucion_dias', 'sharepoint_id'
        ])
    
    def get_all_requests(self) -> pd.DataFrame:
        """Get all requests"""
        if self.df is None:
            return self.create_empty_dataframe()
        return self.df.copy()
    
    def get_request_by_id(self, id_solicitud: str) -> pd.DataFrame:
        """Get request by ID"""
        if self.df is None:
            return pd.DataFrame()
        return self.df[self.df['id_solicitud'] == id_solicitud]
    
    def get_requests_summary(self) -> Dict[str, Any]:
        """Get requests summary for dashboard"""
        if self.df is None or self.df.empty:
            return {
                'total_solicitudes': 0,
                'solicitudes_activas': 0,
                'solicitudes_completadas': 0,
                'tiempo_promedio_respuesta': 0,
                'tiempo_promedio_resolucion': 0,
                'solicitudes_por_estado': {},
                'solicitudes_por_tipo': {},
                'solicitudes_por_area': {},
                'solicitudes_por_proceso': {},
                'solicitudes_por_territorial': {},
                'solicitudes_por_mes': {}
            }
        
        try:
            total = len(self.df)
            activas = len(self.df[self.df['estado'] != 'Completado'])
            completadas = len(self.df[self.df['estado'] == 'Completado'])
            
            # Calculate averages
            solicitudes_con_respuesta = self.df[self.df['tiempo_respuesta_dias'] > 0]
            tiempo_promedio_respuesta = solicitudes_con_respuesta['tiempo_respuesta_dias'].mean() if not solicitudes_con_respuesta.empty else 0
            
            solicitudes_completadas = self.df[self.df['estado'] == 'Completado']
            tiempo_promedio_resolucion = solicitudes_completadas['tiempo_resolucion_dias'].mean() if not solicitudes_completadas.empty else 0
            
            # Generate distributions
            por_estado = self.df['estado'].value_counts().to_dict()
            por_tipo = self.df['tipo_solicitud'].value_counts().to_dict()
            por_area = self.df['area'].value_counts().to_dict()
            por_proceso = self.df['proceso'].value_counts().to_dict()
            por_territorial = self.df['territorial'].value_counts().to_dict()
            
            # Monthly distribution
            df_copy = self.df.copy()
            
            # Ensure fecha_solicitud is timezone-naive before converting to period
            if 'fecha_solicitud' in df_copy.columns:
                # Normalize all datetime values first
                df_copy['fecha_solicitud_colombia'] = df_copy['fecha_solicitud'].apply(to_colombia)
                
                # Convert to pandas datetime, ensuring timezone-naive by removing timezone info
                df_copy['fecha_solicitud_naive'] = df_copy['fecha_solicitud_colombia'].dt.tz_localize(None)
                
                # Create period only for non-null dates
                mask = df_copy['fecha_solicitud_naive'].notna()
                if mask.any():
                    # Suppress the timezone warning by using tz_localize(None)
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        df_copy.loc[mask, 'mes_solicitud'] = df_copy.loc[mask, 'fecha_solicitud_naive'].dt.to_period('M')
                    
                    por_mes = df_copy['mes_solicitud'].value_counts().sort_index().to_dict()
                    por_mes = {str(k): v for k, v in por_mes.items() if pd.notna(k)}
                else:
                    por_mes = {}
            else:
                por_mes = {}
            
            return {
                'total_solicitudes': total,
                'solicitudes_activas': activas,
                'solicitudes_completadas': completadas,
                'tiempo_promedio_respuesta': round(tiempo_promedio_respuesta, 2),
                'tiempo_promedio_resolucion': round(tiempo_promedio_resolucion, 2),
                'solicitudes_por_estado': por_estado,
                'solicitudes_por_tipo': por_tipo,
                'solicitudes_por_area': por_area,
                'solicitudes_por_proceso': por_proceso,
                'solicitudes_por_territorial': por_territorial,
                'solicitudes_por_mes': por_mes
            }
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {
                'total_solicitudes': 0,
                'solicitudes_activas': 0,
                'solicitudes_completadas': 0,
                'tiempo_promedio_respuesta': 0,
                'tiempo_promedio_resolucion': 0,
                'solicitudes_por_estado': {},
                'solicitudes_por_tipo': {},
                'solicitudes_por_area': {},
                'solicitudes_por_proceso': {},
                'solicitudes_por_territorial': {},
                'solicitudes_por_mes': {}
            }
    
    def get_sharepoint_status(self) -> Dict[str, Any]:
        """Get SharePoint connection status"""
        return {
            'sharepoint_connected': bool(self.list_id),
            'site_id': self.sharepoint_site_id,
            'list_id': self.list_id,
            'list_name': self.list_name,
            'token_available': bool(self._get_access_token()),
            'site_url': self.graph_config.get('sharepoint_site_url'),
            'target_drive_connected': bool(self.target_drive_id)
        }