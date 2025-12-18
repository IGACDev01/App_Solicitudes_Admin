"""
Gestor de Flujo de Estados - State Flow Manager
================================================

Módulo encargado de gestionar las transiciones de estado de solicitudes según
reglas de negocio definidas. Implementa una máquina de estados finita con
validación de transiciones y tracking de historial.

Estados del sistema:
- Asignada: Solicitud recién creada, pendiente de comenzar trabajo
- En Proceso: Trabajo activo en curso
- Incompleta: Pausada, esperando información adicional del solicitante
- Completada: Finalizada exitosamente (estado terminal)
- Cancelada: Cancelada por administrador o solicitante (estado terminal)

Reglas de transición:
- Estados terminales (Completada, Cancelada) NO pueden cambiar
- Cada estado define explícitamente a qué estados puede transicionar
- El historial de cambios se mantiene con timestamps en hora de Colombia (COT)

Autor: Equipo IGAC
Fecha: 2024-2025
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pandas as pd
from shared_timezone_utils import obtener_fecha_actual_colombia

# Estados válidos del sistema
VALID_STATES = ["Asignada", "En Proceso", "Incompleta", "Completada", "Cancelada"]

# Reglas de transición de estados: define qué estados pueden cambiar a cuáles
STATE_TRANSITIONS = {
    "Asignada": {
        "allowed": ["En Proceso", "Incompleta", "Cancelada"],
        "description": "Puede moverse a: En Proceso (iniciar trabajo), Incompleta (pausar), o Cancelada"
    },
    "En Proceso": {
        "allowed": ["Completada", "Incompleta", "Cancelada"],
        "description": "Puede moverse a: Completada (finalizar), Incompleta (pausar por info faltante), o Cancelada"
    },
    "Incompleta": {
        "allowed": ["En Proceso", "Cancelada"],
        "description": "Puede resumir a: En Proceso (continuar trabajo) o Cancelada"
    },
    "Completada": {
        "allowed": [],
        "description": "Estado terminal - no puede transicionar a ningún otro estado"
    },
    "Cancelada": {
        "allowed": [],
        "description": "Estado terminal - no puede transicionar a ningún otro estado"
    }
}


class StateFlowValidator:
    """
    Validador de transiciones de estado según reglas de negocio

    Implementa la lógica de validación para asegurar que las transiciones
    de estado cumplan con las reglas definidas en STATE_TRANSITIONS.
    Todos los métodos son estáticos ya que no mantienen estado interno.
    """

    @staticmethod
    def is_valid_transition(estado_actual: str, nuevo_estado: str) -> Tuple[bool, str]:
        """
        Validar si una transición de estado está permitida según las reglas de negocio

        Args:
            estado_actual (str): Estado actual de la solicitud
            nuevo_estado (str): Estado propuesto al que se desea transicionar

        Returns:
            Tuple[bool, str]: (es_válida, mensaje_descriptivo)
                - es_válida: True si la transición es permitida, False en caso contrario
                - mensaje_descriptivo: Mensaje explicativo del resultado de la validación

        Reglas especiales:
            - Permite mantener el mismo estado para 'En Proceso' e 'Incompleta'
              (útil cuando solo se agregan comentarios sin cambiar estado)
            - Estados terminales (Completada, Cancelada) no pueden transicionar
        """
        # Validar que ambos estados existan en el sistema
        if estado_actual not in VALID_STATES:
            return False, f"Estado actual inválido: '{estado_actual}'"

        if nuevo_estado not in VALID_STATES:
            return False, f"Nuevo estado inválido: '{nuevo_estado}'"

        # Permitir mismo estado para 'En Proceso' e 'Incompleta' (para agregar comentarios)
        if estado_actual == nuevo_estado:
            if estado_actual in ['En Proceso', 'Incompleta']:
                return True, f"✅ Manteniendo estado '{nuevo_estado}' (agregando comentarios)"
            else:
                return False, f"El estado ya es '{nuevo_estado}'"

        # Verificar si la transición está en la lista de transiciones permitidas
        allowed_states = STATE_TRANSITIONS[estado_actual]["allowed"]

        if nuevo_estado not in allowed_states:
            return False, (
                f"❌ Transición no permitida: '{estado_actual}' → '{nuevo_estado}'\n"
                f"Estados permitidos: {', '.join(allowed_states) if allowed_states else 'Ninguno (estado terminal)'}"
            )

        return True, f"✅ Transición válida: '{estado_actual}' → '{nuevo_estado}'"

    @staticmethod
    def get_allowed_transitions(estado_actual: str) -> List[str]:
        """
        Obtener lista de estados a los que puede transicionar desde el estado actual

        Args:
            estado_actual (str): Estado actual de la solicitud

        Returns:
            List[str]: Lista de estados permitidos. Lista vacía si es estado terminal.
        """
        if estado_actual in STATE_TRANSITIONS:
            return STATE_TRANSITIONS[estado_actual]["allowed"]
        return []

    @staticmethod
    def get_state_description(estado: str) -> str:
        """
        Obtener descripción de un estado y sus transiciones permitidas

        Args:
            estado (str): Estado a describir

        Returns:
            str: Descripción textual del estado y sus transiciones posibles
        """
        if estado in STATE_TRANSITIONS:
            return STATE_TRANSITIONS[estado]["description"]
        return "Estado desconocido"


class StateHistoryTracker:
    """
    Rastreador de historial de cambios de estado

    Gestiona el registro y visualización del historial de cambios de estado
    de cada solicitud. Mantiene un registro cronológico con timestamps en
    hora de Colombia (COT) para auditoría y trazabilidad.

    Formato de historial:
        [DD/MM/YYYY HH:MM:SS COT] Estado
        Ejemplo: [17/12/2024 14:30:00 COT] En Proceso

    Atributos de clase:
        HISTORY_COLUMN (str): Nombre de la columna en SharePoint que contiene el historial
    """

    HISTORY_COLUMN = "HistorialEstados"

    @staticmethod
    def create_history_entry(
        nuevo_estado: str,
        responsable: str = "Admin",
        comentario: str = ""
    ) -> str:
        """
        Crear una entrada individual para el historial de cambios de estado

        Args:
            nuevo_estado (str): Estado al que se está transicionando
            responsable (str): Usuario responsable del cambio (no usado actualmente)
            comentario (str): Comentario adicional (no usado actualmente)

        Returns:
            str: Entrada de historial formateada con timestamp y estado
                 Formato: "[DD/MM/YYYY HH:MM:SS COT] Estado"

        Nota:
            Actualmente solo incluye estado y timestamp. Los parámetros responsable
            y comentario están disponibles para extensiones futuras.
        """
        timestamp = obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M:%S COT')
        entry = f"[{timestamp}] {nuevo_estado}"
        return entry

    @staticmethod
    def add_to_history(
        historial_actual: str,
        nuevo_estado: str,
        responsable: str = "Admin",
        comentario: str = ""
    ) -> str:
        """
        Agregar nueva entrada al historial existente

        Args:
            historial_actual (str): Historial acumulado actual (puede estar vacío)
            nuevo_estado (str): Nuevo estado a registrar
            responsable (str): Usuario responsable del cambio
            comentario (str): Comentario adicional

        Returns:
            str: Historial actualizado con la nueva entrada agregada al final
        """
        nueva_entrada = StateHistoryTracker.create_history_entry(
            nuevo_estado, responsable, comentario
        )

        # Agregar al final del historial existente
        if historial_actual and str(historial_actual).strip():
            return f"{historial_actual}\n{nueva_entrada}"
        else:
            return nueva_entrada

    @staticmethod
    def parse_history(historial: str) -> List[Dict]:
        """
        Parsear cadena de historial a lista estructurada de diccionarios

        Args:
            historial (str): Cadena de historial con formato "[timestamp] Estado\n..."

        Returns:
            List[Dict]: Lista de entradas parseadas
                       Cada entrada: {"timestamp": str, "estado": str}

        Nota:
            Ignora líneas vacías y maneja errores de formato gracefully.
            Formato esperado: [DD/MM/YYYY HH:MM:SS COT] Estado
        """
        if not historial or not str(historial).strip():
            return []

        entries = []
        historia_limpia = str(historial).strip()
        bloques = historia_limpia.split('\n')

        for bloque in bloques:
            if not bloque.strip():
                continue

            try:
                # Formato: [DD/MM/YYYY HH:MM:SS COT] Estado
                if bloque.startswith('[') and ']' in bloque:
                    timestamp_part = bloque.split('] ')[0] + ']'
                    estado_part = bloque.split('] ', 1)[1] if '] ' in bloque else ""

                    entries.append({
                        "timestamp": timestamp_part,
                        "estado": estado_part.strip()
                    })

            except Exception as e:
                print(f"Error parseando entrada de historial: {e}")
                continue

        return entries

    @staticmethod
    def get_current_state_from_history(historial: str) -> Optional[str]:
        """
        Obtener el estado más reciente del historial (última entrada)

        Args:
            historial (str): Cadena de historial completa

        Returns:
            Optional[str]: Estado más reciente, None si no hay historial
        """
        entries = StateHistoryTracker.parse_history(historial)
        if entries:
            return entries[-1].get('estado')
        return None

    @staticmethod
    def format_history_for_display(historial: str) -> str:
        """
        Formatear historial para visualización en UI de Streamlit

        Args:
            historial (str): Historial crudo desde SharePoint

        Returns:
            str: Historial formateado en Markdown con emojis y orden cronológico invertido
                 (más reciente primero)

        Nota:
            Cada estado tiene un emoji asociado para mejor visualización:
            - Asignada: 🟡 (amarillo)
            - En Proceso: 🔵 (azul)
            - Incompleta: 🟠 (naranja)
            - Completada: ✅ (check verde)
            - Cancelada: ❌ (X roja)
        """
        entries = StateHistoryTracker.parse_history(historial)

        if not entries:
            return "Sin historial de cambios"

        formatted = "**Historial de Cambios de Estado:**\n\n"

        # Mapa de emojis para cada estado
        emoji_map = {
            'Asignada': '🟡',
            'En Proceso': '🔵',
            'Incompleta': '🟠',
            'Completada': '✅',
            'Cancelada': '❌'
        }

        # Mostrar en orden cronológico invertido (más reciente primero)
        for i, entry in enumerate(reversed(entries)):
            emoji = emoji_map.get(entry['estado'], '📋')
            formatted += f"{i+1}. {emoji} **{entry['estado']}** - {entry['timestamp']}\n\n"

        return formatted


def validate_and_get_transition_message(
    estado_actual: str,
    nuevo_estado: str
) -> Tuple[bool, str]:
    """
    Función helper para validar transición y obtener mensaje amigable para el usuario

    Args:
        estado_actual (str): Estado actual de la solicitud
        nuevo_estado (str): Estado propuesto

    Returns:
        Tuple[bool, str]: (es_válida, mensaje_detallado)
            - es_válida: True si la transición es permitida
            - mensaje_detallado: Mensaje descriptivo con estados permitidos si aplica

    Nota:
        Esta es la función principal que debe usarse para validar transiciones
        desde la UI. Provee mensajes detallados incluyendo estados permitidos.
    """
    validator = StateFlowValidator()
    is_valid, message = validator.is_valid_transition(estado_actual, nuevo_estado)

    if not is_valid:
        # Si la transición no es válida, agregar lista de estados permitidos
        allowed = validator.get_allowed_transitions(estado_actual)
        if allowed:
            return False, f"{message}\n\n📋 Estados permitidos desde '{estado_actual}': {', '.join(allowed)}"
        else:
            return False, f"{message}\n\n⚠️ '{estado_actual}' es un estado terminal y no puede cambiar."

    return True, message
