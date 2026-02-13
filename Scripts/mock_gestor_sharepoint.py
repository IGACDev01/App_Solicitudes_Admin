"""
Mock Gestor de Listas SharePoint - Modo de Desarrollo Local
=============================================================

Reemplazo drop-in de GestorListasSharePoint que usa JSON local + filesystem
en lugar de SharePoint/Microsoft Graph API. Permite ejecutar la aplicación
completa sin conexión a SharePoint ni credenciales reales.

Almacenamiento:
- Datos: Data/local_solicitudes_admin.json
- Adjuntos: Data/attachments/{id_solicitud}/{nombre_archivo}

Uso:
    Activar con variable de entorno USE_MOCK=true (por defecto en main_admin.py)
"""

import pandas as pd
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from shared_timezone_utils import obtener_fecha_actual_colombia, convertir_a_colombia


class MockGestorListasSharePoint:
    """Drop-in replacement for GestorListasSharePoint using local JSON + filesystem."""

    COLUMNS = [
        'id_solicitud', 'territorial', 'nombre_solicitante', 'email_solicitante',
        'fecha_solicitud', 'tipo_solicitud', 'area', 'proceso', 'prioridad', 'descripcion',
        'estado', 'responsable_asignado', 'email_responsable',
        'fecha_actualizacion', 'fecha_completado',
        'comentarios_admin', 'comentarios_usuario',
        'tiempo_respuesta_dias', 'tiempo_resolucion_dias', 'tiempo_pausado_dias',
        'fecha_pausa', 'historial_pausas', 'historial_estados',
        'sharepoint_id'
    ]

    DATE_COLUMNS = ['fecha_solicitud', 'fecha_actualizacion', 'fecha_completado', 'fecha_pausa']

    def __init__(self, nombre_lista: str = "Data App Solicitudes"):
        self.nombre_lista = nombre_lista
        self.df = None

        # Local storage paths
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'Data')
        self.json_path = os.path.join(self.data_dir, 'local_solicitudes_admin.json')
        self.attachments_dir = os.path.join(self.data_dir, 'attachments')

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.attachments_dir, exist_ok=True)

        if not os.path.exists(self.json_path):
            self._seed_sample_data()

        self.cargar_datos()
        print(f"[MOCK] Initialized with {len(self.df)} solicitudes from local JSON")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _save_to_json(self):
        """Persist current DataFrame to JSON."""
        if self.df is None or self.df.empty:
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return

        records = []
        for _, row in self.df.iterrows():
            record = {}
            for col in self.COLUMNS:
                val = row.get(col)
                if pd.isna(val):
                    record[col] = None
                elif isinstance(val, (datetime, pd.Timestamp)):
                    record[col] = val.isoformat()
                else:
                    record[col] = val
            records.append(record)

        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2, default=str)

    def _load_from_json(self) -> pd.DataFrame:
        """Read JSON file into a DataFrame."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self.crear_dataframe_vacio()

        if not records:
            return self.crear_dataframe_vacio()

        df = pd.DataFrame(records)

        # Ensure all columns exist
        for col in self.COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Parse date columns
        for col in self.DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Ensure numeric columns
        for col in ['tiempo_respuesta_dias', 'tiempo_resolucion_dias', 'tiempo_pausado_dias']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

    def _seed_sample_data(self):
        """Create realistic sample data for first run."""
        now = obtener_fecha_actual_colombia()

        samples = [
            {
                "id_solicitud": "A1B2C3D4",
                "territorial": "Cundinamarca",
                "nombre_solicitante": "Juan Perez",
                "email_solicitante": "juan.perez@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=7)).isoformat(),
                "tipo_solicitud": "Solicitud de suministros (papeleria, insumos, llantas, equipos)",
                "area": "Subdirecci\u00f3n Administrativa y Financiera",
                "proceso": "Almac\u00e9n",
                "prioridad": "Alta",
                "descripcion": "Necesitamos 50 resmas de papel carta para la oficina territorial de Cundinamarca.",
                "estado": "Asignada",
                "responsable_asignado": "",
                "email_responsable": "",
                "fecha_actualizacion": (now - timedelta(days=7)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": "",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 0,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=7)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada",
                "sharepoint_id": "mock-sp-1"
            },
            {
                "id_solicitud": "E5F6G7H8",
                "territorial": "Antioquia",
                "nombre_solicitante": "Maria Garcia",
                "email_solicitante": "maria.garcia@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=14)).isoformat(),
                "tipo_solicitud": "Gestion de pagos (perfil pagador, parafiscales, embargos, claves)",
                "area": "Subdirecci\u00f3n Administrativa y Financiera",
                "proceso": "Contabilidad",
                "prioridad": "Media",
                "descripcion": "Solicitud de revision de registros contables para la territorial Antioquia.",
                "estado": "En Proceso",
                "responsable_asignado": "Carlos Rodriguez",
                "email_responsable": "carlos.rodriguez@igac.gov.co",
                "fecha_actualizacion": (now - timedelta(days=3)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": f"[{(now - timedelta(days=3)).strftime('%d/%m/%Y %H:%M')} COT - Admin]: Se esta procesando la revision contable.",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 11.0,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=14)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada\n[{(now - timedelta(days=3)).strftime('%d/%m/%Y %H:%M:%S')} COT] En Proceso",
                "sharepoint_id": "mock-sp-2"
            },
            {
                "id_solicitud": "I9J0K1L2",
                "territorial": "Cundinamarca",
                "nombre_solicitante": "Ana Martinez",
                "email_solicitante": "ana.martinez@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=10)).isoformat(),
                "tipo_solicitud": "Solicitud de suministros (papeleria, insumos, llantas, equipos)",
                "area": "Subdirecci\u00f3n Administrativa y Financiera",
                "proceso": "Almac\u00e9n",
                "prioridad": "Alta",
                "descripcion": "Se requieren insumos de limpieza para las oficinas de Bogota. Urgente.",
                "estado": "Incompleta",
                "responsable_asignado": "Pedro Lopez",
                "email_responsable": "pedro.lopez@igac.gov.co",
                "fecha_actualizacion": (now - timedelta(days=2)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": f"[{(now - timedelta(days=2)).strftime('%d/%m/%Y %H:%M')} COT - Admin]: Favor adjuntar cotizacion de los insumos solicitados.",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 3.0,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": (now - timedelta(days=2)).isoformat(),
                "historial_pausas": f"Pausa: {(now - timedelta(days=2)).strftime('%d/%m/%Y %H:%M:%S')} COT",
                "historial_estados": f"[{(now - timedelta(days=10)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada\n[{(now - timedelta(days=7)).strftime('%d/%m/%Y %H:%M:%S')} COT] En Proceso\n[{(now - timedelta(days=2)).strftime('%d/%m/%Y %H:%M:%S')} COT] Incompleta",
                "sharepoint_id": "mock-sp-3"
            },
            {
                "id_solicitud": "M3N4O5P6",
                "territorial": "Valle del Cauca",
                "nombre_solicitante": "Luis Gomez",
                "email_solicitante": "luis.gomez@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=30)).isoformat(),
                "tipo_solicitud": "Gestion presupuestal (CDP, RP, vigencias futuras, traslados)",
                "area": "Subdirecci\u00f3n Administrativa y Financiera",
                "proceso": "Presupuesto",
                "prioridad": "Baja",
                "descripcion": "Solicitud de CDP para adquisicion de mobiliario para la territorial Valle del Cauca.",
                "estado": "Completada",
                "responsable_asignado": "Sandra Ruiz",
                "email_responsable": "sandra.ruiz@igac.gov.co",
                "fecha_actualizacion": (now - timedelta(days=10)).isoformat(),
                "fecha_completado": (now - timedelta(days=10)).isoformat(),
                "comentarios_admin": f"[{(now - timedelta(days=10)).strftime('%d/%m/%Y %H:%M')} COT - Admin]: CDP generado exitosamente. Numero: CDP-2025-0342.",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 2.5,
                "tiempo_resolucion_dias": 20.0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=30)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada\n[{(now - timedelta(days=27)).strftime('%d/%m/%Y %H:%M:%S')} COT] En Proceso\n[{(now - timedelta(days=10)).strftime('%d/%m/%Y %H:%M:%S')} COT] Completada",
                "sharepoint_id": "mock-sp-4"
            },
            {
                "id_solicitud": "Q7R8S9T0",
                "territorial": "Bogota D.C.",
                "nombre_solicitante": "Carolina Diaz",
                "email_solicitante": "carolina.diaz@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=5)).isoformat(),
                "tipo_solicitud": "Aperturas de puntos de atencion",
                "area": "Oficina Asesora de Comunicaciones",
                "proceso": "Comunicaci\u00f3n Externa",
                "prioridad": "Media",
                "descripcion": "Se requiere cobertura mediatica para la apertura del nuevo punto de atencion en Bogota.",
                "estado": "Asignada",
                "responsable_asignado": "",
                "email_responsable": "",
                "fecha_actualizacion": (now - timedelta(days=5)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": "",
                "comentarios_usuario": f"[{(now - timedelta(days=4)).strftime('%d/%m/%Y %H:%M')} COT - Carolina Diaz]: Adjunto fotos del local para referencia.",
                "tiempo_respuesta_dias": 0,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=5)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada",
                "sharepoint_id": "mock-sp-5"
            },
            {
                "id_solicitud": "U1V2W3X4",
                "territorial": "Santander",
                "nombre_solicitante": "Roberto Hernandez",
                "email_solicitante": "roberto.hernandez@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=12)).isoformat(),
                "tipo_solicitud": "Mantenimiento correctivo (redes electricas, pisos, puertas, cubiertas, aires acondicionados)",
                "area": "Subdirecci\u00f3n Administrativa y Financiera",
                "proceso": "Transporte",
                "prioridad": "Alta",
                "descripcion": "Vehiculo institucional con falla mecanica. Requiere revision urgente.",
                "estado": "En Proceso",
                "responsable_asignado": "Equipo Transporte",
                "email_responsable": "transporte@igac.gov.co",
                "fecha_actualizacion": (now - timedelta(days=1)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": f"[{(now - timedelta(days=1)).strftime('%d/%m/%Y %H:%M')} COT - Admin]: Vehiculo en taller. Diagnostico en proceso.",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 1.5,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=12)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada\n[{(now - timedelta(days=10)).strftime('%d/%m/%Y %H:%M:%S')} COT] En Proceso",
                "sharepoint_id": "mock-sp-6"
            },
            {
                "id_solicitud": "Y5Z6A7B8",
                "territorial": "Bogota D.C.",
                "nombre_solicitante": "Patricia Vargas",
                "email_solicitante": "patricia.vargas@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=20)).isoformat(),
                "tipo_solicitud": "Diseno de pieza para enviar por correo electronico institucional",
                "area": "Oficina Asesora de Comunicaciones",
                "proceso": "Comunicaci\u00f3n Interna",
                "prioridad": "Por definir",
                "descripcion": "Solicitud de diseno de pieza grafica para boletin interno. Cancelada por duplicidad.",
                "estado": "Cancelada",
                "responsable_asignado": "",
                "email_responsable": "",
                "fecha_actualizacion": (now - timedelta(days=15)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": f"[{(now - timedelta(days=15)).strftime('%d/%m/%Y %H:%M')} COT - Admin]: Solicitud cancelada por duplicidad con solicitud Y5Z6A7B9.",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 5.0,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=20)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada\n[{(now - timedelta(days=15)).strftime('%d/%m/%Y %H:%M:%S')} COT] Cancelada",
                "sharepoint_id": "mock-sp-7"
            },
            {
                "id_solicitud": "C9D0E1F2",
                "territorial": "Santander",
                "nombre_solicitante": "Fernando Castro",
                "email_solicitante": "fernando.castro@igac.gov.co",
                "fecha_solicitud": (now - timedelta(days=3)).isoformat(),
                "tipo_solicitud": "Solicitud de suministros (papeleria, insumos, llantas, equipos)",
                "area": "Subdirecci\u00f3n Administrativa y Financiera",
                "proceso": "Almac\u00e9n",
                "prioridad": "Media",
                "descripcion": "Solicitud de toner para impresoras de la territorial Santander.",
                "estado": "Asignada",
                "responsable_asignado": "",
                "email_responsable": "",
                "fecha_actualizacion": (now - timedelta(days=3)).isoformat(),
                "fecha_completado": None,
                "comentarios_admin": "",
                "comentarios_usuario": "",
                "tiempo_respuesta_dias": 0,
                "tiempo_resolucion_dias": 0,
                "tiempo_pausado_dias": 0,
                "fecha_pausa": None,
                "historial_pausas": "",
                "historial_estados": f"[{(now - timedelta(days=3)).strftime('%d/%m/%Y %H:%M:%S')} COT] Asignada",
                "sharepoint_id": "mock-sp-8"
            }
        ]

        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        print("[MOCK] Seeded 8 sample solicitudes")

    # ------------------------------------------------------------------
    # Public API (mirrors GestorListasSharePoint)
    # ------------------------------------------------------------------

    def cargar_datos(self, forzar_recarga: bool = True):
        """Load data from local JSON file."""
        self.df = self._load_from_json()

    def crear_dataframe_vacio(self) -> pd.DataFrame:
        """Create empty DataFrame with full column schema."""
        return pd.DataFrame(columns=self.COLUMNS)

    def obtener_todas_solicitudes(self) -> pd.DataFrame:
        """Get all requests."""
        if self.df is None:
            return self.crear_dataframe_vacio()
        return self.df.copy()

    def obtener_solicitud_por_id(self, id_solicitud: str) -> pd.DataFrame:
        """Get a single request by ID."""
        if self.df is None:
            return pd.DataFrame()
        return self.df[self.df['id_solicitud'] == id_solicitud]

    def obtener_estado_sharepoint(self) -> Dict[str, Any]:
        """Return mock connected status."""
        return {
            'sharepoint_conectado': True,
            'id_sitio': 'mock-site-id',
            'id_lista': 'mock-list-id',
            'nombre_lista': self.nombre_lista,
            'token_disponible': True,
            'url_sitio': 'http://localhost/mock-sharepoint',
            'drive_destino_conectado': True,
            'error_mensaje': None
        }

    def agregar_solicitud(self, datos_solicitud: Dict[str, Any]) -> Optional[str]:
        """Add a new request to local storage."""
        try:
            id_solicitud = str(uuid.uuid4())[:8].upper()
            current_time = obtener_fecha_actual_colombia()
            timestamp_str = current_time.strftime('%d/%m/%Y %H:%M:%S COT')

            new_row = {
                'id_solicitud': id_solicitud,
                'territorial': datos_solicitud.get('territorial', ''),
                'nombre_solicitante': datos_solicitud.get('nombre', ''),
                'email_solicitante': datos_solicitud.get('email', ''),
                'fecha_solicitud': current_time,
                'tipo_solicitud': datos_solicitud.get('tipo', ''),
                'area': datos_solicitud.get('area', ''),
                'proceso': datos_solicitud.get('proceso', ''),
                'prioridad': datos_solicitud.get('prioridad', 'Por definir'),
                'descripcion': datos_solicitud.get('descripcion', ''),
                'estado': 'Asignada',
                'responsable_asignado': '',
                'email_responsable': '',
                'fecha_actualizacion': current_time,
                'fecha_completado': None,
                'comentarios_admin': '',
                'comentarios_usuario': '',
                'tiempo_respuesta_dias': 0,
                'tiempo_resolucion_dias': 0,
                'tiempo_pausado_dias': 0,
                'fecha_pausa': None,
                'historial_pausas': '',
                'historial_estados': f"[{timestamp_str}] Asignada",
                'sharepoint_id': f'mock-sp-{uuid.uuid4().hex[:6]}'
            }

            new_df = pd.DataFrame([new_row])
            if self.df is None or self.df.empty:
                self.df = new_df
            else:
                self.df = pd.concat([self.df, new_df], ignore_index=True)

            self._save_to_json()
            print(f"[MOCK] Created solicitud {id_solicitud}")
            return id_solicitud
        except Exception as e:
            print(f"[MOCK] Error adding request: {e}")
            return None

    def actualizar_estado_solicitud(self, id_solicitud: str, nuevo_estado: str,
                                    responsable: str = "", comentarios: str = "",
                                    historial_estados: str = "", email_responsable: str = "") -> bool:
        """Update request status in local storage."""
        try:
            if self.df is None or self.df.empty:
                return False

            mask = self.df['id_solicitud'] == id_solicitud
            if not mask.any():
                return False

            idx = self.df[mask].index[0]
            estado_anterior = self.df.at[idx, 'estado']
            tiempo_actual = obtener_fecha_actual_colombia()

            # Handle pause/resume tracking
            if nuevo_estado == 'Incompleta' and estado_anterior != 'Incompleta':
                self.df.at[idx, 'fecha_pausa'] = tiempo_actual
                historial_p = self.df.at[idx, 'historial_pausas'] or ''
                nueva_entrada = f"Pausa: {tiempo_actual.strftime('%d/%m/%Y %H:%M:%S')} COT"
                self.df.at[idx, 'historial_pausas'] = f"{historial_p}\n{nueva_entrada}".strip()

            elif estado_anterior == 'Incompleta' and nuevo_estado != 'Incompleta':
                fecha_pausa = self.df.at[idx, 'fecha_pausa']
                if pd.notna(fecha_pausa):
                    if hasattr(fecha_pausa, 'to_pydatetime'):
                        fecha_pausa = fecha_pausa.to_pydatetime()
                    dias_pausa = (tiempo_actual - fecha_pausa).total_seconds() / 86400
                    tiempo_pausado_prev = self.df.at[idx, 'tiempo_pausado_dias'] or 0
                    self.df.at[idx, 'tiempo_pausado_dias'] = round(tiempo_pausado_prev + dias_pausa, 2)

                    historial_p = self.df.at[idx, 'historial_pausas'] or ''
                    nueva_entrada = f"Reanudacion: {tiempo_actual.strftime('%d/%m/%Y %H:%M:%S')} COT ({dias_pausa:.1f} dias)"
                    self.df.at[idx, 'historial_pausas'] = f"{historial_p}\n{nueva_entrada}".strip()

                self.df.at[idx, 'fecha_pausa'] = None

            # Update core fields
            self.df.at[idx, 'estado'] = nuevo_estado
            self.df.at[idx, 'fecha_actualizacion'] = tiempo_actual

            if responsable:
                self.df.at[idx, 'responsable_asignado'] = responsable
            if email_responsable:
                self.df.at[idx, 'email_responsable'] = email_responsable
            if comentarios:
                self.df.at[idx, 'comentarios_admin'] = comentarios
            if historial_estados:
                self.df.at[idx, 'historial_estados'] = historial_estados

            # Handle Completada
            if nuevo_estado == 'Completada':
                self.df.at[idx, 'fecha_completado'] = tiempo_actual
                fecha_solicitud = self.df.at[idx, 'fecha_solicitud']
                tiempo_pausado = self.df.at[idx, 'tiempo_pausado_dias'] or 0
                if pd.notna(fecha_solicitud):
                    if hasattr(fecha_solicitud, 'to_pydatetime'):
                        fecha_solicitud = fecha_solicitud.to_pydatetime()
                    tiempo_total = (tiempo_actual - fecha_solicitud).total_seconds() / 86400
                    self.df.at[idx, 'tiempo_resolucion_dias'] = round(max(tiempo_total - tiempo_pausado, 0), 2)

            # Handle first response time (leaving Asignada)
            if nuevo_estado != 'Asignada' and estado_anterior == 'Asignada':
                tiempo_resp_actual = self.df.at[idx, 'tiempo_respuesta_dias'] or 0
                if tiempo_resp_actual == 0:
                    fecha_solicitud = self.df.at[idx, 'fecha_solicitud']
                    tiempo_pausado = self.df.at[idx, 'tiempo_pausado_dias'] or 0
                    if pd.notna(fecha_solicitud):
                        if hasattr(fecha_solicitud, 'to_pydatetime'):
                            fecha_solicitud = fecha_solicitud.to_pydatetime()
                        tiempo_total = (tiempo_actual - fecha_solicitud).total_seconds() / 86400
                        self.df.at[idx, 'tiempo_respuesta_dias'] = round(max(tiempo_total - tiempo_pausado, 0), 2)

            self._save_to_json()
            print(f"[MOCK] Solicitud {id_solicitud}: {estado_anterior} -> {nuevo_estado}")
            return True
        except Exception as e:
            print(f"[MOCK] Error updating status: {e}")
            return False

    def actualizar_prioridad_solicitud(self, id_solicitud: str, nueva_prioridad: str) -> bool:
        """Update request priority in local storage."""
        try:
            if self.df is None or self.df.empty:
                return False

            mask = self.df['id_solicitud'] == id_solicitud
            if not mask.any():
                return False

            idx = self.df[mask].index[0]
            self.df.at[idx, 'prioridad'] = nueva_prioridad
            self.df.at[idx, 'fecha_actualizacion'] = obtener_fecha_actual_colombia()
            self._save_to_json()
            print(f"[MOCK] Solicitud {id_solicitud} prioridad -> {nueva_prioridad}")
            return True
        except Exception as e:
            print(f"[MOCK] Error updating priority: {e}")
            return False

    # ------------------------------------------------------------------
    # File attachment methods
    # ------------------------------------------------------------------

    def subir_archivo_adjunto_a_item(self, id_solicitud: str, datos_archivo: bytes, nombre_archivo: str) -> bool:
        """Save attachment to local filesystem."""
        try:
            folder = os.path.join(self.attachments_dir, id_solicitud)
            os.makedirs(folder, exist_ok=True)
            file_path = os.path.join(folder, nombre_archivo)
            with open(file_path, 'wb') as f:
                f.write(datos_archivo)
            print(f"[MOCK] Saved attachment {nombre_archivo} for {id_solicitud}")
            return True
        except Exception as e:
            print(f"[MOCK] Error uploading attachment: {e}")
            return False

    def obtener_archivos_adjuntos_solicitud(self, id_solicitud: str) -> List[Dict[str, Any]]:
        """List attachments from local filesystem."""
        folder = os.path.join(self.attachments_dir, id_solicitud)
        if not os.path.isdir(folder):
            return []

        files = []
        for idx, filename in enumerate(os.listdir(folder)):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                files.append({
                    'name': filename,
                    'id': f'mock-file-{idx}',
                    'download_url': '',
                    'size': os.path.getsize(filepath),
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat() + 'Z',
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat() + 'Z',
                    'web_url': ''
                })
        return files

    def borrar_archivo_adjunto_solicitud(self, id_solicitud: str, nombre_archivo: str) -> bool:
        """Delete attachment from local filesystem."""
        try:
            filepath = os.path.join(self.attachments_dir, id_solicitud, nombre_archivo)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"[MOCK] Deleted attachment {nombre_archivo} for {id_solicitud}")
                return True
            print(f"[MOCK] Attachment not found: {nombre_archivo}")
            return False
        except Exception as e:
            print(f"[MOCK] Error deleting attachment: {e}")
            return False

    # ------------------------------------------------------------------
    # Summary / analytics
    # ------------------------------------------------------------------

    def obtener_resumen_solicitudes(self) -> Dict[str, Any]:
        """Get summary statistics from local data."""
        empty_result = {
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

        if self.df is None or self.df.empty:
            return empty_result

        try:
            total = len(self.df)
            activas = len(self.df[self.df['estado'] != 'Completada'])
            completadas = len(self.df[self.df['estado'] == 'Completada'])
            incompletas = len(self.df[self.df['estado'] == 'Incompleta'])

            sol_con_respuesta = self.df[self.df['tiempo_respuesta_dias'] > 0]
            avg_respuesta = sol_con_respuesta['tiempo_respuesta_dias'].mean() if not sol_con_respuesta.empty else 0

            sol_completadas = self.df[self.df['estado'] == 'Completada']
            avg_resolucion = sol_completadas['tiempo_resolucion_dias'].mean() if not sol_completadas.empty else 0

            por_estado = self.df['estado'].value_counts().to_dict()
            por_tipo = self.df['tipo_solicitud'].value_counts().to_dict()
            por_area = self.df['area'].value_counts().to_dict()
            por_proceso = self.df['proceso'].value_counts().to_dict()
            por_territorial = self.df['territorial'].value_counts().to_dict()

            # Monthly distribution
            por_mes = {}
            if 'fecha_solicitud' in self.df.columns:
                df_copia = self.df.copy()
                df_copia['fecha_solicitud_dt'] = pd.to_datetime(df_copia['fecha_solicitud'], errors='coerce')
                mask = df_copia['fecha_solicitud_dt'].notna()
                if mask.any():
                    # Remove timezone info for period conversion
                    df_copia.loc[mask, 'fecha_naive'] = df_copia.loc[mask, 'fecha_solicitud_dt'].dt.tz_localize(None) if df_copia.loc[mask, 'fecha_solicitud_dt'].dt.tz is not None else df_copia.loc[mask, 'fecha_solicitud_dt']
                    try:
                        df_copia.loc[mask, 'mes'] = df_copia.loc[mask, 'fecha_naive'].dt.to_period('M')
                        por_mes = df_copia['mes'].value_counts().sort_index().to_dict()
                        por_mes = {str(k): v for k, v in por_mes.items() if pd.notna(k)}
                    except Exception:
                        por_mes = {}

            return {
                'total_solicitudes': total,
                'solicitudes_activas': activas,
                'solicitudes_completadas': completadas,
                'solicitudes_incompletas': incompletas,
                'tiempo_promedio_respuesta': round(avg_respuesta, 2),
                'tiempo_promedio_resolucion': round(avg_resolucion, 2),
                'solicitudes_por_estado': por_estado,
                'solicitudes_por_tipo': por_tipo,
                'solicitudes_por_area': por_area,
                'solicitudes_por_proceso': por_proceso,
                'solicitudes_por_territorial': por_territorial,
                'solicitudes_por_mes': por_mes
            }
        except Exception as e:
            print(f"[MOCK] Error generating summary: {e}")
            return empty_result
