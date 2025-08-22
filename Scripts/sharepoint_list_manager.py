import pandas as pd
import os
import streamlit as st
import uuid
import time
import random
from datetime import datetime, timedelta
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import quote
from timezone_utils_admin import obtener_fecha_actual_colombia, convertir_a_colombia, convertir_a_utc_para_almacenamiento

class GestorListasSharePoint:
    def __init__(self, nombre_lista: str = "Data App Solicitudes"):
        """Inicializar Gestor de Listas SharePoint"""
        self.nombre_lista = nombre_lista
        self.df = None
        
        # Configuración SharePoint/Graph API
        self.configuracion_graph = self._cargar_configuracion_graph()
        self.token_acceso = None
        self.token_expira_en = None
        
        # Información de conexión SharePoint
        self.id_sitio_sharepoint = None
        self.id_lista = None
        self.id_drive_destino = None
        
        # Validar configuración
        if not self._validar_configuracion_sharepoint():
            st.error("❌ Configuración de SharePoint incompleta. Verifique sus variables de entorno.")
            st.stop()
        
        # Inicializar conexión
        self._inicializar_conexion_sharepoint()
    
    def _validar_configuracion_sharepoint(self) -> bool:
        """Validar configuración de SharePoint"""
        campos_requeridos = ['tenant_id', 'client_id', 'client_secret', 'sharepoint_site_url']
        campos_faltantes = [campo for campo in campos_requeridos if not self.configuracion_graph.get(campo)]
        
        if campos_faltantes:
            print(f"Configuración de SharePoint faltante: {', '.join(campos_faltantes)}")
            return False
        
        return True

    def _cargar_configuracion_graph(self) -> Dict[str, str]:
        """Cargar configuración de Graph API desde el entorno"""
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
    
    def _obtener_token_acceso(self) -> Optional[str]:
        """Obtener token de acceso para Microsoft Graph API con retry logic"""
        
        # Check if we have a valid cached token
        if (hasattr(self, '_token_cache') and hasattr(self, '_token_expira_en') and 
            datetime.now() < self._token_expira_en):
            return self._token_cache
        
        # Retry configuration
        max_retries = 3
        base_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                url_token = f"https://login.microsoftonline.com/{self.configuracion_graph['tenant_id']}/oauth2/v2.0/token"
                
                datos_token = {
                    'grant_type': 'client_credentials',
                    'client_id': self.configuracion_graph['client_id'],
                    'client_secret': self.configuracion_graph['client_secret'],
                    'scope': 'https://graph.microsoft.com/.default'
                }
                
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                
                # Add timeout to prevent hanging
                response = requests.post(url_token, data=datos_token, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    info_token = response.json()
                    token_acceso = info_token.get('access_token')
                    expira_en = info_token.get('expires_in', 3600)
                    
                    self._token_cache = token_acceso
                    self._token_expira_en = datetime.now() + timedelta(seconds=expira_en - 300)
                    
                    print(f"✅ Token de SharePoint obtenido exitosamente (intento {attempt + 1})")
                    return token_acceso
                
                else:
                    # Handle specific error codes
                    if response.status_code == 400:
                        print("❌ Error de configuración OAuth - verifique credenciales")
                        return None  # Don't retry for config errors
                    elif response.status_code == 401:
                        print("❌ Credenciales inválidas")
                        return None  # Don't retry for auth errors
                    elif response.status_code in [429, 503, 504]:
                        # Rate limiting or server errors - retry with backoff
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"⚠️ Error temporal ({response.status_code}), reintentando en {delay:.1f}s...")
                        if attempt < max_retries - 1:
                            time.sleep(delay)
                            continue
                    else:
                        info_error = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                        error_desc = info_error.get('error_description', f'HTTP {response.status_code}')
                        print(f"❌ Error en autenticación SharePoint: {error_desc}")
                        
                        # Retry for unknown errors
                        if attempt < max_retries - 1:
                            delay = base_delay * (2 ** attempt)
                            print(f"🔄 Reintentando en {delay}s...")
                            time.sleep(delay)
                            continue
                    
            except requests.exceptions.Timeout:
                print(f"⏱️ Timeout en autenticación (intento {attempt + 1})")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                    
            except requests.exceptions.ConnectionError:
                print(f"🌐 Error de conexión (intento {attempt + 1})")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                    
            except Exception as e:
                print(f"❌ Error inesperado en autenticación: {e}")
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
        
        # All retries failed
        print(f"❌ Falló autenticación SharePoint después de {max_retries} intentos")
        return None

    def _obtener_headers(self) -> Dict[str, str]:
        """Obtener headers para peticiones Graph API con retry automático"""
        token = self._obtener_token_acceso()
        if not token:
            # Try one more time with cache clear
            if hasattr(self, '_token_cache'):
                delattr(self, '_token_cache')
            if hasattr(self, '_token_expira_en'):
                delattr(self, '_token_expira_en')
            
            token = self._obtener_token_acceso()
            if not token:
                return {}
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def _obtener_id_sitio_sharepoint(self) -> Optional[str]:
        """Obtener ID del sitio SharePoint"""
        if hasattr(self, '_id_sitio_cache'):
            return self._id_sitio_cache
            
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return None
            
            url_sitio = self.configuracion_graph['sharepoint_site_url']
            
            if url_sitio.startswith('https://'):
                url_sitio = url_sitio[8:]
            
            partes = url_sitio.split('/')
            hostname = partes[0]
            ruta_sitio = '/'.join(partes[1:]) if len(partes) > 1 else ''
            
            if ruta_sitio:
                ruta_codificada = quote(ruta_sitio, safe='')
                url = f"{self.configuracion_graph['graph_url']}/sites/{hostname}:/{ruta_codificada}"
            else:
                url = f"{self.configuracion_graph['graph_url']}/sites/{hostname}"
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                info_sitio = response.json()
                self._id_sitio_cache = info_sitio['id']
                print(f"Conectado al sitio SharePoint: {url_sitio}")
                return self._id_sitio_cache
            else:
                print(f"Error al obtener sitio SharePoint: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error obteniendo ID del sitio SharePoint: {e}")
            return None
    
    def _obtener_id_lista(self) -> Optional[str]:
        """Obtener ID de la lista SharePoint"""
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return None
            
            id_sitio = self._obtener_id_sitio_sharepoint()
            if not id_sitio:
                return None
            
            # Obtener lista por nombre
            url_listas = f"{self.configuracion_graph['graph_url']}/sites/{id_sitio}/lists"
            response = requests.get(url_listas, headers=headers)
            
            if response.status_code == 200:
                datos_listas = response.json()
                
                for item_lista in datos_listas.get('value', []):
                    if item_lista.get('displayName') == self.nombre_lista:
                        id_lista = item_lista['id']
                        print(f"Encontrada lista SharePoint: {self.nombre_lista}")
                        return id_lista
                
                print(f"Lista '{self.nombre_lista}' no encontrada")
                return None
            else:
                print(f"Error al obtener listas: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error obteniendo ID de lista: {e}")
            return None

    def _obtener_id_drive_destino(self) -> Optional[str]:
        """Obtener el ID del drive Sistema_Gestion_Solicitudes"""
        if hasattr(self, '_id_drive_destino_cache'):
            return self._id_drive_destino_cache
            
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return None
            
            id_sitio = self._obtener_id_sitio_sharepoint()
            if not id_sitio:
                return None
            
            # Obtener todos los drives del sitio
            url_drives = f"{self.configuracion_graph['graph_url']}/sites/{id_sitio}/drives"
            response = requests.get(url_drives, headers=headers)
            
            if response.status_code == 200:
                datos_drives = response.json()
                drives = datos_drives.get('value', [])
                
                # Buscar drive Sistema_Gestion_Solicitudes - coincidencia exacta primero
                for drive in drives:
                    if drive.get('name') == 'Sistema_Gestion_Solicitudes':
                        self._id_drive_destino_cache = drive['id']
                        print(f"✅ Encontrado drive destino: {drive['name']}")
                        return self._id_drive_destino_cache
                
                # Buscar coincidencia parcial
                for drive in drives:
                    if 'Sistema_Gestion_Solicitudes' in drive.get('name', ''):
                        self._id_drive_destino_cache = drive['id']
                        print(f"✅ Encontrado drive destino (parcial): {drive['name']}")
                        return self._id_drive_destino_cache
                
                # Fallback a biblioteca Documents
                for drive in drives:
                    if drive.get('name') == 'Documents':
                        self._id_drive_destino_cache = drive['id']
                        print(f"📁 Usando biblioteca Documents como fallback")
                        return self._id_drive_destino_cache
                        
                print("❌ No se pudo encontrar drive adecuado")
                return None
            else:
                print(f"❌ Error al obtener drives: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error obteniendo ID de drive destino: {e}")
            return None
    
    def _inicializar_conexion_sharepoint(self):
        """Inicializar conexión SharePoint"""
        print(f"Inicializando conexión a lista SharePoint '{self.nombre_lista}'...")
        
        id_sitio = self._obtener_id_sitio_sharepoint()
        if not id_sitio:
            st.error("❌ Error al conectar con el sitio SharePoint")
            st.stop()
        
        self.id_sitio_sharepoint = id_sitio
        
        id_lista = self._obtener_id_lista()
        if not id_lista:
            st.error(f"❌ Lista SharePoint '{self.nombre_lista}' no encontrada")
            st.stop()
        
        self.id_lista = id_lista
        
        # Obtener drive destino para subida de archivos
        id_drive_destino = self._obtener_id_drive_destino()
        if id_drive_destino:
            self.id_drive_destino = id_drive_destino
        else:
            print("⚠️ Drive destino no encontrado, las subidas de archivos pueden fallar")
        
        print(f"Conectado a lista SharePoint: {self.nombre_lista}")

        # Cargar data frame vacio para ser llenado bajo demanda
        self.df = self.crear_dataframe_vacio()
        print(f"Conectado a lista SharePoint: {self.nombre_lista} (datos cargados bajo demanda)")
    
    def _normalizar_datetime(self, dt) -> Optional[datetime]:
        """Normalizar datetime a timezone-naive para manejo consistente"""
        if dt is None:
            return None
        
        try:
            # Usar utilidad de zona horaria para consistencia
            return convertir_a_colombia(dt)
        except Exception as e:
            print(f"Error normalizando datetime {dt}: {e}")
            return None
    
    def cargar_datos(self, forzar_recarga: bool = True):
        """Cargar datos desde Lista SharePoint"""
        try:
            if not self.id_lista:
                print("No hay ID de lista disponible")
                return
            
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                print("No hay autorización SharePoint")
                return
            
            # Obtener todos los elementos de la lista con campos expandidos
            url_items = f"{self.configuracion_graph['graph_url']}/sites/{self.id_sitio_sharepoint}/lists/{self.id_lista}/items"
            
            # Agregar parámetros de consulta para obtener valores de campos
            params = {
                '$expand': 'fields',
                '$top': 5000  # Ajustar según sea necesario
            }
            
            response = requests.get(url_items, headers=headers, params=params)
            
            if response.status_code == 200:
                datos_items = response.json()
                items = datos_items.get('value', [])
                
                if not items:
                    print("Lista SharePoint está vacía")
                    self.df = self.crear_dataframe_vacio()
                    return
                
                # Convertir elementos de lista SharePoint a DataFrame
                filas = []
                for item in items:
                    campos = item.get('fields', {})
                    
                    # Mapear campos SharePoint a columnas DataFrame - con normalización de zona horaria
                    fila = {
                        'id_solicitud': campos.get('IDSolicitud', ''),
                        'territorial': campos.get('Territorial', ''),
                        'nombre_solicitante': campos.get('NombreSolicitante', ''),
                        'email_solicitante': campos.get('EmailSolicitante', ''),
                        'fecha_solicitud': self._normalizar_datetime(self._parsear_fecha(campos.get('FechaSolicitud'))),
                        'tipo_solicitud': campos.get('TipoSolicitud', ''),
                        'area': campos.get('Area', ''),
                        'proceso': campos.get('Proceso', ''),
                        'prioridad': campos.get('Prioridad', 'Por definir'),
                        'descripcion': campos.get('Descripcion', ''),
                        'estado': campos.get('Estado', 'Asignada'),
                        'responsable_asignado': campos.get('ResponsableAsignado', ''),
                        'fecha_actualizacion': self._normalizar_datetime(self._parsear_fecha(campos.get('FechaActualizacion'))),
                        'fecha_completado': self._normalizar_datetime(self._parsear_fecha(campos.get('FechaCompletado'))),
                        'comentarios_admin': campos.get('ComentariosAdmin', ''),
                        'comentarios_usuario': campos.get('ComentariosUsuario', ''), 
                        'tiempo_respuesta_dias': campos.get('TiempoRespuestaDias', 0),
                        'tiempo_resolucion_dias': campos.get('TiempoResolucionDias', 0),
                        'sharepoint_id': item.get('id', ''),
                        'tiempo_pausado_dias': campos.get('TiempoPausadoDias', 0),
                        'fecha_pausa': self._normalizar_datetime(self._parsear_fecha(campos.get('FechaPausa'))),
                        'historial_pausas': campos.get('HistorialPausas', '')
                    }
                    filas.append(fila)
                
                self.df = pd.DataFrame(filas)
                print(f"Cargados exitosamente {len(self.df)} elementos desde lista SharePoint")
                
            else:
                print(f"Error al cargar elementos de lista: {response.status_code}")
                self.df = self.crear_dataframe_vacio()
                
        except Exception as e:
            print(f"Error cargando datos desde lista SharePoint: {e}")
            self.df = self.crear_dataframe_vacio()
    
    def _parsear_fecha(self, cadena_fecha: str) -> Optional[datetime]:
        """Parsear cadena de fecha SharePoint a datetime"""
        if not cadena_fecha:
            return None
        
        try:
            # SharePoint retorna formato ISO: 2023-12-01T10:30:00Z
            if 'T' in cadena_fecha:
                return datetime.fromisoformat(cadena_fecha.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(cadena_fecha)
        except Exception as e:
            print(f"Error parseando fecha '{cadena_fecha}': {e}")
            return None
    
    def agregar_solicitud(self, datos_solicitud: Dict[str, Any]) -> Optional[str]:
        """Agregar nueva solicitud a Lista SharePoint"""
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return None
            
            # Generar ID único
            id_solicitud = str(uuid.uuid4())[:8].upper()
            
            # Preparar elemento de lista SharePoint
            tiempo_actual_utc = convertir_a_utc_para_almacenamiento(obtener_fecha_actual_colombia()).isoformat() + 'Z'
            
            elemento_lista = {
                'fields': {
                    'IDSolicitud': id_solicitud,
                    'Territorial': datos_solicitud['territorial'],
                    'NombreSolicitante': datos_solicitud['nombre'],
                    'EmailSolicitante': datos_solicitud['email'],
                    'FechaSolicitud': tiempo_actual_utc,
                    'TipoSolicitud': datos_solicitud['tipo'],
                    'Area': datos_solicitud['area'],
                    'Proceso': datos_solicitud['proceso'],
                    'Prioridad': datos_solicitud.get('prioridad', 'Por definir'),
                    'Descripcion': datos_solicitud['descripcion'],
                    'Estado': 'Asignada',
                    'ResponsableAsignado': '',
                    'FechaActualizacion': tiempo_actual_utc,
                    'TiempoRespuestaDias': 0,
                    'TiempoResolucionDias': 0
                }
            }
            
            # Agregar campos opcionales
            if datos_solicitud.get('fecha_limite'):
                elemento_lista['fields']['FechaNecesaria'] = datos_solicitud['fecha_limite'].isoformat()
            
            # Crear elemento de lista
            url_crear = f"{self.configuracion_graph['graph_url']}/sites/{self.id_sitio_sharepoint}/lists/{self.id_lista}/items"
            
            response = requests.post(url_crear, headers=headers, json=elemento_lista)
            
            if response.status_code == 201:
                print(f"Nueva solicitud creada en lista SharePoint: {id_solicitud}")
                
                # Recargar datos para incluir nuevo elemento
                self.cargar_datos()
                return id_solicitud
            else:
                detalle_error = response.text
                print(f"Error al crear elemento de lista: {response.status_code} - {detalle_error}")
                return None
                
        except Exception as e:
            print(f"Error agregando solicitud a lista SharePoint: {e}")
            return None
    
    def actualizar_estado_solicitud(self, id_solicitud: str, nuevo_estado: str, 
                                responsable: str = "", comentarios: str = "") -> bool:
        """Actualizar estado de solicitud en Lista SharePoint"""
        try:
            # Obtener estado anterior
            solicitud_actual = self.obtener_solicitud_por_id(id_solicitud)
            if solicitud_actual.empty:
                return False
            
            estado_anterior = solicitud_actual.iloc[0]['estado']
            
            # Gestionar pausas/reanudaciones
            if not self._gestionar_pausa_reanudacion(id_solicitud, estado_anterior, nuevo_estado, "Estado cambiado"):
                print(f"Error gestionando pausa para solicitud {id_solicitud}")
                # Continuar con actualización normal aunque falle la gestión de pausa
            
            # Encontrar el elemento SharePoint
            id_sharepoint = self._obtener_id_elemento_sharepoint(id_solicitud)
            if not id_sharepoint:
                print(f"Elemento SharePoint no encontrado para ID: {id_solicitud}")
                return False
            
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return False
            
            tiempo_actual_utc = convertir_a_utc_para_almacenamiento(obtener_fecha_actual_colombia()).isoformat() + 'Z'
            
            # Preparar datos de actualización
            datos_actualizacion = {
                'Estado': nuevo_estado,
                'FechaActualizacion': tiempo_actual_utc
            }
            
            if responsable:
                datos_actualizacion['ResponsableAsignado'] = responsable
            
            if comentarios:
                datos_actualizacion['ComentariosAdmin'] = comentarios
            
            # Manejar Completada
            if nuevo_estado == 'Completada':
                datos_actualizacion['FechaCompletado'] = tiempo_actual_utc
                
                # Cálculo de tiempo de resolución para considerar pausas
                if not solicitud_actual.empty:
                    fecha_solicitud = solicitud_actual.iloc[0]['fecha_solicitud']
                    tiempo_pausado = solicitud_actual.iloc[0].get('tiempo_pausado_dias', 0)
                    
                    if pd.notna(fecha_solicitud):
                        fecha_solicitud_colombia = convertir_a_colombia(fecha_solicitud)
                        fecha_actual_norm = obtener_fecha_actual_colombia()
                        
                        if fecha_solicitud_colombia:
                            tiempo_total = (fecha_actual_norm - fecha_solicitud_colombia).total_seconds() / (24 * 3600)
                            tiempo_efectivo = tiempo_total - tiempo_pausado
                            datos_actualizacion['TiempoResolucionDias'] = round(max(tiempo_efectivo, 0), 2)
            
            # MODIFICAR cálculo de tiempo de respuesta para considerar pausas
            if nuevo_estado != 'Asignada' and estado_anterior == 'Asignada':
                if not solicitud_actual.empty:
                    tiempo_respuesta_actual = solicitud_actual.iloc[0].get('tiempo_respuesta_dias', 0)
                    if tiempo_respuesta_actual == 0:
                        fecha_solicitud = solicitud_actual.iloc[0]['fecha_solicitud']
                        tiempo_pausado = solicitud_actual.iloc[0].get('tiempo_pausado_dias', 0)
                        
                        if pd.notna(fecha_solicitud):
                            fecha_solicitud_colombia = convertir_a_colombia(fecha_solicitud)
                            fecha_actual_norm = obtener_fecha_actual_colombia()
                            
                            if fecha_solicitud_colombia:
                                tiempo_total = (fecha_actual_norm - fecha_solicitud_colombia).total_seconds() / (24 * 3600)
                                tiempo_efectivo = tiempo_total - tiempo_pausado
                                datos_actualizacion['TiempoRespuestaDias'] = round(max(tiempo_efectivo, 0), 2)
            
            # Actualizar elemento de lista SharePoint
            url_actualizar = f"{self.configuracion_graph['graph_url']}/sites/{self.id_sitio_sharepoint}/lists/{self.id_lista}/items/{id_sharepoint}/fields"
            
            response = requests.patch(url_actualizar, headers=headers, json=datos_actualizacion)
            
            if response.status_code in [200, 204]:
                print(f"Solicitud {id_solicitud} actualizada exitosamente")
                return True
            else:
                print(f"Error al actualizar solicitud: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error actualizando estado de solicitud: {e}")
            return False
    
    def actualizar_prioridad_solicitud(self, id_solicitud: str, nueva_prioridad: str) -> bool:
        """Actualizar prioridad de solicitud en Lista SharePoint"""
        try:
            # Encontrar el elemento SharePoint
            id_sharepoint = self._obtener_id_elemento_sharepoint(id_solicitud)
            if not id_sharepoint:
                print(f"Elemento SharePoint no encontrado para ID: {id_solicitud}")
                return False
            
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return False
            
            tiempo_actual_utc = convertir_a_utc_para_almacenamiento(obtener_fecha_actual_colombia()).isoformat() + 'Z'
            
            # Preparar datos de actualización
            datos_actualizacion = {
                'Prioridad': nueva_prioridad,
                'FechaActualizacion': tiempo_actual_utc
            }
            
            # Actualizar elemento de lista SharePoint
            url_actualizar = f"{self.configuracion_graph['graph_url']}/sites/{self.id_sitio_sharepoint}/lists/{self.id_lista}/items/{id_sharepoint}/fields"
            
            response = requests.patch(url_actualizar, headers=headers, json=datos_actualizacion)
            
            if response.status_code in [200, 204]:
                print(f"Prioridad de solicitud {id_solicitud} actualizada a {nueva_prioridad}")
                return True
            else:
                print(f"Error al actualizar prioridad: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error actualizando prioridad de solicitud: {e}")
            return False
    
    def _obtener_id_elemento_sharepoint(self, id_solicitud: str) -> Optional[str]:
        """Obtener ID interno del elemento SharePoint desde ID personalizado"""
        if self.df is None or self.df.empty:
            return None
        
        elementos_coincidentes = self.df[self.df['id_solicitud'] == id_solicitud]
        if elementos_coincidentes.empty:
            return None
        
        return elementos_coincidentes.iloc[0].get('sharepoint_id')
    
    # ============================================
    # MÉTODOS DE SUBIDA DE ARCHIVOS
    # ============================================
    
    def subir_archivo_adjunto_a_item(self, id_solicitud: str, datos_archivo: bytes, nombre_archivo: str) -> bool:
        """Subir archivo adjunto para una solicitud específica"""
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                print("❌ No hay token de autorización")
                return False
            
            if not self.id_drive_destino:
                print("❌ No hay drive destino disponible")
                return False
            
            # Paso 1: Asegurar que existe carpeta "Archivos Adjuntos"
            if not self._asegurar_carpeta_archivos_adjuntos():
                print("❌ No se pudo crear/verificar carpeta 'Archivos Adjuntos'")
                return False
            
            # Paso 2: Crear subcarpeta específica de solicitud
            if not self._crear_subcarpeta_solicitud(id_solicitud):
                print(f"❌ No se pudo crear subcarpeta para {id_solicitud}")
                return False
            
            # Paso 3: Subir archivo a la subcarpeta
            ruta_archivo = f"Archivos Adjuntos/{id_solicitud}/{nombre_archivo}"
            
            url_subida = f"{self.configuracion_graph['graph_url']}/drives/{self.id_drive_destino}/root:/{ruta_archivo}:/content"
            
            headers_subida = {
                'Authorization': headers['Authorization'],
                'Content-Type': 'application/octet-stream'
            }
            
            response = requests.put(url_subida, headers=headers_subida, data=datos_archivo)
            
            if response.status_code in [200, 201]:
                print(f"✅ Archivo subido: {nombre_archivo} a {id_solicitud}")
                return True
            else:
                print(f"❌ Error en subida: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error subiendo archivo adjunto: {e}")
            return False
    
    def _asegurar_carpeta_archivos_adjuntos(self) -> bool:
        """Asegurar que existe carpeta 'Archivos Adjuntos' en raíz"""
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return False
            
            # Crear carpeta en raíz - usar replace para evitar conflictos
            url_crear = f"{self.configuracion_graph['graph_url']}/drives/{self.id_drive_destino}/root/children"
            
            datos_carpeta = {
                "name": "Archivos Adjuntos",
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"  # No fallar si ya existe
            }
            
            response = requests.post(url_crear, headers=headers, json=datos_carpeta)
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"❌ Error al asegurar carpeta 'Archivos Adjuntos': {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error asegurando carpeta base: {e}")
            return False
    
    def _crear_subcarpeta_solicitud(self, id_solicitud: str) -> bool:
        """Crear subcarpeta para solicitud específica"""
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return False
            
            # Crear subcarpeta bajo "Archivos Adjuntos"
            url_subcarpeta = f"{self.configuracion_graph['graph_url']}/drives/{self.id_drive_destino}/root:/Archivos Adjuntos:/children"
            
            datos_subcarpeta = {
                "name": id_solicitud,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace"  # No fallar si ya existe
            }
            
            response = requests.post(url_subcarpeta, headers=headers, json=datos_subcarpeta)
            
            if response.status_code in [200, 201]:
                return True
            else:
                print(f"❌ Error al crear subcarpeta {id_solicitud}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error creando subcarpeta de solicitud: {e}")
            return False
    
    def obtener_archivos_adjuntos_solicitud(self, id_solicitud: str) -> List[Dict[str, Any]]:
        """Obtener todos los archivos adjuntos para una solicitud específica"""
        try:
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return []
            
            if not self.id_drive_destino:
                return []
            
            # Obtener archivos de subcarpeta de solicitud
            ruta_carpeta = f"Archivos Adjuntos/{id_solicitud}"
            url_archivos = f"{self.configuracion_graph['graph_url']}/drives/{self.id_drive_destino}/root:/{ruta_carpeta}:/children"
            
            response = requests.get(url_archivos, headers=headers)
            
            if response.status_code == 200:
                datos_archivos = response.json()
                archivos = []
                for item in datos_archivos.get('value', []):
                    if 'file' in item:  # Es un archivo, no una carpeta
                        archivos.append({
                            'name': item['name'],
                            'id': item['id'],
                            'download_url': item.get('@microsoft.graph.downloadUrl', ''),
                            'size': item.get('size', 0),
                            'created': item.get('createdDateTime', ''),
                            'modified': item.get('lastModifiedDateTime', ''),
                            'web_url': item.get('webUrl', '')
                        })
                return archivos
            else:
                # Carpeta no existe o no hay archivos
                return []
                
        except Exception as e:
            print(f"❌ Error obteniendo archivos adjuntos para {id_solicitud}: {e}")
            return []
    
    # ============================================
    # MÉTODOS DE UTILIDAD
    # ============================================
    
    def crear_dataframe_vacio(self) -> pd.DataFrame:
        """Crear DataFrame vacío con estructura apropiada"""
        return pd.DataFrame(columns=[
            'id_solicitud', 'territorial', 'nombre_solicitante', 'email_solicitante',
            'fecha_solicitud', 'tipo_solicitud', 'area', 'proceso', 'prioridad',
            'descripcion', 'estado', 'responsable_asignado', 'fecha_actualizacion',
            'fecha_completado', 'comentarios_admin', 'comentarios_usuario',  # NEW FIELD
            'tiempo_respuesta_dias', 'tiempo_resolucion_dias', 'sharepoint_id',
            'tiempo_pausado_dias', 'fecha_pausa', 'historial_pausas'
        ])
    
    def obtener_todas_solicitudes(self) -> pd.DataFrame:
        """Obtener todas las solicitudes"""
        if self.df is None:
            return self.crear_dataframe_vacio()
        return self.df.copy()
    
    def obtener_solicitud_por_id(self, id_solicitud: str) -> pd.DataFrame:
        """Obtener solicitud por ID"""
        if self.df is None:
            return pd.DataFrame()
        return self.df[self.df['id_solicitud'] == id_solicitud]
    
    def obtener_resumen_solicitudes(self) -> Dict[str, Any]:
        """Obtener resumen de solicitudes para dashboard"""
        if self.df is None or self.df.empty:
            return {
                'total_solicitudes': 0,
                'solicitudes_activas': 0,
                'solicitudes_completadas': 0,
                'solicitudes_incompletas': 0,
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
            activas = len(self.df[self.df['estado'] != 'Completada'])
            completadas = len(self.df[self.df['estado'] == 'Completada'])
            incompletas = len(self.df[self.df['estado'] == 'Incompleta'])
            
            # Calcular promedios
            solicitudes_con_respuesta = self.df[self.df['tiempo_respuesta_dias'] > 0]
            tiempo_promedio_respuesta = solicitudes_con_respuesta['tiempo_respuesta_dias'].mean() if not solicitudes_con_respuesta.empty else 0
            
            solicitudes_completadas = self.df[self.df['estado'] == 'Completada']
            tiempo_promedio_resolucion = solicitudes_completadas['tiempo_resolucion_dias'].mean() if not solicitudes_completadas.empty else 0
            
            # Generar distribuciones
            por_estado = self.df['estado'].value_counts().to_dict()
            por_tipo = self.df['tipo_solicitud'].value_counts().to_dict()
            por_area = self.df['area'].value_counts().to_dict()
            por_proceso = self.df['proceso'].value_counts().to_dict()
            por_territorial = self.df['territorial'].value_counts().to_dict()
            
            # Distribución mensual
            df_copia = self.df.copy()
            
            # Asegurar que fecha_solicitud sea timezone-naive antes de convertir a período
            if 'fecha_solicitud' in df_copia.columns:
                # Normalizar todos los valores datetime primero
                df_copia['fecha_solicitud_colombia'] = df_copia['fecha_solicitud'].apply(convertir_a_colombia)
                
                # Convertir a pandas datetime, asegurando timezone-naive removiendo información de zona horaria
                df_copia['fecha_solicitud_naive'] = df_copia['fecha_solicitud_colombia'].dt.tz_localize(None)
                
                # Crear período solo para fechas no nulas
                mask = df_copia['fecha_solicitud_naive'].notna()
                if mask.any():
                    # Suprimir advertencia de zona horaria usando tz_localize(None)
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        df_copia.loc[mask, 'mes_solicitud'] = df_copia.loc[mask, 'fecha_solicitud_naive'].dt.to_period('M')
                    
                    por_mes = df_copia['mes_solicitud'].value_counts().sort_index().to_dict()
                    por_mes = {str(k): v for k, v in por_mes.items() if pd.notna(k)}
                else:
                    por_mes = {}
            else:
                por_mes = {}
            
            return {
                'total_solicitudes': total,
                'solicitudes_activas': activas,
                'solicitudes_completadas': completadas,
                'solicitudes_incompletas': len(self.df[self.df['estado'] == 'Incompleta']),
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
            print(f"Error generando resumen: {e}")
            return {
                'total_solicitudes': 0,
                'solicitudes_activas': 0,
                'solicitudes_completadas': 0,
                'solicitudes_incompletas': 0,
                'tiempo_promedio_respuesta': 0,
                'tiempo_promedio_resolucion': 0,
                'solicitudes_por_estado': {},
                'solicitudes_por_tipo': {},
                'solicitudes_por_area': {},
                'solicitudes_por_proceso': {},
                'solicitudes_por_territorial': {},
                'solicitudes_por_mes': {}
            }

    def obtener_estado_sharepoint(self) -> Dict[str, Any]:
        """Obtener estado de conexión SharePoint"""
        estado = {
            'sharepoint_conectado': False,
            'id_sitio': self.id_sitio_sharepoint,
            'id_lista': self.id_lista,
            'nombre_lista': self.nombre_lista,
            'token_disponible': False,
            'url_sitio': self.configuracion_graph.get('sharepoint_site_url'),
            'drive_destino_conectado': bool(self.id_drive_destino),
            'error_mensaje': None
        }
        
        # Test token availability
        token = self._obtener_token_acceso()
        estado['token_disponible'] = bool(token)
        
        if not token:
            estado['error_mensaje'] = "No se pudo obtener token de autenticación"
            return estado
        
        # Simple connection test - just check if we have what we need
        try:
            headers = self._obtener_headers()
            if headers.get('Authorization'):
                # If we have a lista ID, we're connected
                estado['sharepoint_conectado'] = bool(self.id_lista)
                if not self.id_lista:
                    estado['error_mensaje'] = f"Lista '{self.nombre_lista}' no encontrada"
            else:
                estado['error_mensaje'] = "No se pudieron obtener headers de autorización"
                
        except Exception as e:
            estado['error_mensaje'] = f"Error de conexión: {str(e)}"
        
        return estado

    def _gestionar_pausa_reanudacion(self, id_solicitud: str, estado_anterior: str, nuevo_estado: str, motivo: str = ""):
        """Gestionar lógica de pausa y reanudación"""
        try:
            # Pausar solicitud
            if nuevo_estado == "Incompleta" and estado_anterior != "Incompleta":
                return self._pausar_solicitud(id_solicitud, motivo)
            
            # Reanudar solicitud
            elif estado_anterior == "Incompleta" and nuevo_estado != "Incompleta":
                return self._reanudar_solicitud(id_solicitud, motivo)
            
            return True
        except Exception as e:
            print(f"Error en gestión de pausa: {e}")
            return False

    def _pausar_solicitud(self, id_solicitud: str, motivo: str) -> bool:
        """Pausar solicitud - registrar inicio de pausa"""
        try:
            id_sharepoint = self._obtener_id_elemento_sharepoint(id_solicitud)
            if not id_sharepoint:
                return False
            
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return False
            
            tiempo_actual_utc = convertir_a_utc_para_almacenamiento(obtener_fecha_actual_colombia()).isoformat() + 'Z'
            
            # Obtener historial actual
            solicitud_actual = self.obtener_solicitud_por_id(id_solicitud)
            historial_actual = solicitud_actual.iloc[0].get('historial_pausas', '') if not solicitud_actual.empty else ''
            
            # Agregar entrada al historial
            nueva_entrada = f"[{obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M')}] PAUSADA - {motivo}"
            historial_actualizado = f"{historial_actual}\n{nueva_entrada}" if historial_actual else nueva_entrada
            
            datos_pausa = {
                'FechaPausa': tiempo_actual_utc,
                'HistorialPausas': historial_actualizado
            }
            
            url_actualizar = f"{self.configuracion_graph['graph_url']}/sites/{self.id_sitio_sharepoint}/lists/{self.id_lista}/items/{id_sharepoint}/fields"
            response = requests.patch(url_actualizar, headers=headers, json=datos_pausa)
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            print(f"Error pausando solicitud: {e}")
            return False

    def _reanudar_solicitud(self, id_solicitud: str, motivo: str) -> bool:
        """Reanudar solicitud - calcular tiempo pausado y acumular"""
        try:
            id_sharepoint = self._obtener_id_elemento_sharepoint(id_solicitud)
            if not id_sharepoint:
                return False
            
            headers = self._obtener_headers()
            if not headers.get('Authorization'):
                return False
            
            # Obtener datos actuales
            solicitud_actual = self.obtener_solicitud_por_id(id_solicitud)
            if solicitud_actual.empty:
                return False
            
            solicitud = solicitud_actual.iloc[0]
            fecha_pausa = solicitud.get('fecha_pausa')
            tiempo_pausado_acumulado = solicitud.get('tiempo_pausado_dias', 0)
            historial_actual = solicitud.get('historial_pausas', '')
            
            # Calcular tiempo de esta pausa
            tiempo_pausa_actual = 0
            if fecha_pausa and pd.notna(fecha_pausa):
                fecha_pausa_norm = convertir_a_colombia(fecha_pausa)
                tiempo_pausa_actual = (obtener_fecha_actual_colombia() - fecha_pausa_norm).total_seconds() / (24 * 3600)
            
            # Acumular tiempo pausado
            tiempo_pausado_total = tiempo_pausado_acumulado + tiempo_pausa_actual
            
            # Actualizar historial
            nueva_entrada = f"[{obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M')}] REANUDADA - {motivo} (Pausada {tiempo_pausa_actual:.1f} días)"
            historial_actualizado = f"{historial_actual}\n{nueva_entrada}" if historial_actual else nueva_entrada
            
            datos_reanudacion = {
                'TiempoPausadoDias': round(tiempo_pausado_total, 2),
                'FechaPausa': None,  # Limpiar fecha de pausa
                'HistorialPausas': historial_actualizado
            }
            
            url_actualizar = f"{self.configuracion_graph['graph_url']}/sites/{self.id_sitio_sharepoint}/lists/{self.id_lista}/items/{id_sharepoint}/fields"
            response = requests.patch(url_actualizar, headers=headers, json=datos_reanudacion)
            
            return response.status_code in [200, 204]
            
        except Exception as e:
            print(f"Error reanudando solicitud: {e}")
            return False