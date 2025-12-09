"""
State Flow Manager
Manages request state transitions with validation rules and history tracking
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pandas as pd
from shared_timezone_utils import obtener_fecha_actual_colombia

# Define valid state transitions
VALID_STATES = ["Asignada", "En Proceso", "Incompleta", "Completada", "Cancelada"]

# State flow rules: Define which states can transition to which
STATE_TRANSITIONS = {
    "Asignada": {
        "allowed": ["En Proceso", "Incompleta", "Cancelada"],
        "description": "Can move to: En Proceso (start work), Incompleta (pause), or Cancelada"
    },
    "En Proceso": {
        "allowed": ["Completada", "Incompleta", "Cancelada"],
        "description": "Can move to: Completada (finish), Incompleta (pause for info), or Cancelada"
    },
    "Incompleta": {
        "allowed": ["En Proceso", "Cancelada"],
        "description": "Can resume to: En Proceso (continue work) or Cancelada"
    },
    "Completada": {
        "allowed": [],
        "description": "Terminal state - cannot transition"
    },
    "Cancelada": {
        "allowed": [],
        "description": "Terminal state - cannot transition"
    }
}


class StateFlowValidator:
    """Validate state transitions according to business rules"""

    @staticmethod
    def is_valid_transition(estado_actual: str, nuevo_estado: str) -> Tuple[bool, str]:
        """
        Validate if a state transition is allowed

        Args:
            estado_actual: Current state of the request
            nuevo_estado: Proposed new state

        Returns:
            Tuple of (is_valid: bool, message: str)
        """
        # Check if states are valid
        if estado_actual not in VALID_STATES:
            return False, f"Estado actual inválido: '{estado_actual}'"

        if nuevo_estado not in VALID_STATES:
            return False, f"Nuevo estado inválido: '{nuevo_estado}'"

        # Allow same state for En Proceso and Incompleta (for adding comments)
        if estado_actual == nuevo_estado:
            if estado_actual in ['En Proceso', 'Incompleta']:
                return True, f"✅ Manteniendo estado '{nuevo_estado}' (agregando comentarios)"
            else:
                return False, f"El estado ya es '{nuevo_estado}'"

        # Check if transition is allowed
        allowed_states = STATE_TRANSITIONS[estado_actual]["allowed"]

        if nuevo_estado not in allowed_states:
            return False, (
                f"❌ Transición no permitida: '{estado_actual}' → '{nuevo_estado}'\n"
                f"Estados permitidos: {', '.join(allowed_states) if allowed_states else 'Ninguno (estado terminal)'}"
            )

        return True, f"✅ Transición válida: '{estado_actual}' → '{nuevo_estado}'"

    @staticmethod
    def get_allowed_transitions(estado_actual: str) -> List[str]:
        """Get list of allowed next states"""
        if estado_actual in STATE_TRANSITIONS:
            return STATE_TRANSITIONS[estado_actual]["allowed"]
        return []

    @staticmethod
    def get_state_description(estado: str) -> str:
        """Get description of a state and its allowed transitions"""
        if estado in STATE_TRANSITIONS:
            return STATE_TRANSITIONS[estado]["description"]
        return "Estado desconocido"


class StateHistoryTracker:
    """Track and manage state change history"""

    HISTORY_COLUMN = "HistorialEstados"

    @staticmethod
    def create_history_entry(
        nuevo_estado: str,
        responsable: str = "Admin",
        comentario: str = ""
    ) -> str:
        """Create a single history entry for a state change - only includes state and timestamp"""
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
        """Add a new entry to the state history"""
        nueva_entrada = StateHistoryTracker.create_history_entry(
            nuevo_estado, responsable, comentario
        )

        if historial_actual and str(historial_actual).strip():
            return f"{historial_actual}\n{nueva_entrada}"
        else:
            return nueva_entrada

    @staticmethod
    def parse_history(historial: str) -> List[Dict]:
        """Parse history string into structured list"""
        if not historial or not str(historial).strip():
            return []

        entries = []
        historia_limpia = str(historial).strip()
        bloques = historia_limpia.split('\n')

        for bloque in bloques:
            if not bloque.strip():
                continue

            try:
                # New format: [DD/MM/YYYY HH:MM:SS COT] Estado
                if bloque.startswith('[') and ']' in bloque:
                    timestamp_part = bloque.split('] ')[0] + ']'
                    estado_part = bloque.split('] ', 1)[1] if '] ' in bloque else ""

                    entries.append({
                        "timestamp": timestamp_part,
                        "estado": estado_part.strip()
                    })

            except Exception as e:
                print(f"Error parsing history entry: {e}")
                continue

        return entries

    @staticmethod
    def get_current_state_from_history(historial: str) -> Optional[str]:
        """Get the most recent state from history"""
        entries = StateHistoryTracker.parse_history(historial)
        if entries:
            return entries[-1].get('estado')
        return None

    @staticmethod
    def format_history_for_display(historial: str) -> str:
        """Format history for display in UI"""
        entries = StateHistoryTracker.parse_history(historial)

        if not entries:
            return "Sin historial de cambios"

        formatted = "**Historial de Cambios de Estado:**\n\n"

        emoji_map = {
            'Asignada': '🟡',
            'En Proceso': '🔵',
            'Incompleta': '🟠',
            'Completada': '✅',
            'Cancelada': '❌'
        }

        for i, entry in enumerate(reversed(entries)):
            emoji = emoji_map.get(entry['estado'], '📋')
            formatted += f"{i+1}. {emoji} **{entry['estado']}** - {entry['timestamp']}\n\n"

        return formatted


def validate_and_get_transition_message(
    estado_actual: str,
    nuevo_estado: str
) -> Tuple[bool, str]:
    """Validate transition and get user-friendly message"""
    validator = StateFlowValidator()
    is_valid, message = validator.is_valid_transition(estado_actual, nuevo_estado)

    if not is_valid:
        allowed = validator.get_allowed_transitions(estado_actual)
        if allowed:
            return False, f"{message}\n\n📋 Estados permitidos desde '{estado_actual}': {', '.join(allowed)}"
        else:
            return False, f"{message}\n\n⚠️ '{estado_actual}' es un estado terminal y no puede cambiar."

    return True, message
