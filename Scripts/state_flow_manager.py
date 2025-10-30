"""
State Flow Manager
Manages request state transitions with validation rules and history tracking
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pandas as pd
from timezone_utils_admin import obtener_fecha_actual_colombia, formatear_fecha_colombia

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
        "description": "Terminal state - cannot transition (except through history audit)"
    },
    "Cancelada": {
        "allowed": [],
        "description": "Terminal state - cannot transition (except through history audit)"
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

        # Same state transition is always invalid
        if estado_actual == nuevo_estado:
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
        """
        Get list of allowed next states

        Args:
            estado_actual: Current state

        Returns:
            List of allowed states
        """
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

    # Column name in SharePoint
    HISTORY_COLUMN = "HistorialEstados"

    @staticmethod
    def create_history_entry(
        nuevo_estado: str,
        responsable: str = "Admin",
        comentario: str = ""
    ) -> str:
        """
        Create a single history entry for a state change

        Args:
            nuevo_estado: New state
            responsable: Person making the change
            comentario: Optional comment about the change

        Returns:
            Formatted history entry string
        """
        timestamp = obtener_fecha_actual_colombia().strftime('%d/%m/%Y %H:%M:%S COT')

        entry = f"[{timestamp}] Estado: '{nuevo_estado}' | Responsable: {responsable}"
        if comentario and comentario.strip():
            # Clean up comment
            comentario_limpio = comentario.strip()[:100]  # Max 100 chars
            entry += f" | Nota: {comentario_limpio}"

        return entry

    @staticmethod
    def add_to_history(
        historial_actual: str,
        nuevo_estado: str,
        responsable: str = "Admin",
        comentario: str = ""
    ) -> str:
        """
        Add a new entry to the state history

        Args:
            historial_actual: Current history string (or empty)
            nuevo_estado: New state
            responsable: Person making the change
            comentario: Optional comment

        Returns:
            Updated history string
        """
        nueva_entrada = StateHistoryTracker.create_history_entry(
            nuevo_estado, responsable, comentario
        )

        if historial_actual and str(historial_actual).strip():
            # Append to existing history
            return f"{historial_actual}\n\n{nueva_entrada}"
        else:
            # First entry
            return nueva_entrada

    @staticmethod
    def parse_history(historial: str) -> List[Dict]:
        """
        Parse history string into structured list

        Args:
            historial: History string from SharePoint

        Returns:
            List of dictionaries with parsed history entries
        """
        if not historial or not str(historial).strip():
            return []

        entries = []
        # Split by double newlines (entry separators)
        historia_limpia = str(historial).strip()
        bloques = historia_limpia.split('\n\n')

        for bloque in bloques:
            if not bloque.strip():
                continue

            try:
                # Parse: [DD/MM/YYYY HH:MM:SS COT] Estado: 'XXX' | Responsable: XXX | Nota: XXX
                partes = bloque.split(' | ')

                timestamp_estado = partes[0] if len(partes) > 0 else ""
                responsable = partes[1].replace('Responsable: ', '') if len(partes) > 1 else "Unknown"
                nota = partes[2].replace('Nota: ', '') if len(partes) > 2 else ""

                # Extract estado from first part
                # Format: [DD/MM/YYYY HH:MM:SS COT] Estado: 'XXXX'
                estado_match = ""
                if "Estado: '" in timestamp_estado:
                    estado_match = timestamp_estado.split("Estado: '")[1].split("'")[0]
                    timestamp = timestamp_estado.split('] ')[0] + ']'
                else:
                    timestamp = timestamp_estado

                entries.append({
                    "timestamp": timestamp,
                    "estado": estado_match,
                    "responsable": responsable.strip(),
                    "nota": nota.strip()
                })

            except Exception as e:
                print(f"Error parsing history entry: {e}")
                continue

        return entries

    @staticmethod
    def get_current_state_from_history(historial: str) -> Optional[str]:
        """
        Get the most recent state from history

        Args:
            historial: History string

        Returns:
            Most recent state or None
        """
        entries = StateHistoryTracker.parse_history(historial)
        if entries:
            return entries[-1].get('estado')
        return None

    @staticmethod
    def format_history_for_display(historial: str) -> str:
        """
        Format history for display in UI

        Args:
            historial: History string

        Returns:
            Formatted markdown string
        """
        entries = StateHistoryTracker.parse_history(historial)

        if not entries:
            return "Sin historial de cambios"

        formatted = "**Historial de Cambios de Estado:**\n\n"

        # Display in reverse order (newest first)
        for i, entry in enumerate(reversed(entries)):
            emoji_map = {
                'Asignada': '🟡',
                'En Proceso': '🔵',
                'Incompleta': '🟠',
                'Completada': '✅',
                'Cancelada': '❌'
            }
            emoji = emoji_map.get(entry['estado'], '📋')

            formatted += f"{i+1}. {emoji} **{entry['estado']}** - {entry['timestamp']}\n"
            formatted += f"   👤 {entry['responsable']}"

            if entry['nota']:
                formatted += f" | 📝 {entry['nota']}"

            formatted += "\n\n"

        return formatted


def validate_and_get_transition_message(
    estado_actual: str,
    nuevo_estado: str
) -> Tuple[bool, str]:
    """
    Validate transition and get user-friendly message

    Args:
        estado_actual: Current state
        nuevo_estado: Proposed new state

    Returns:
        Tuple of (is_valid, message)
    """
    validator = StateFlowValidator()
    is_valid, message = validator.is_valid_transition(estado_actual, nuevo_estado)

    if not is_valid:
        # Provide helpful information
        allowed = validator.get_allowed_transitions(estado_actual)
        if allowed:
            return False, f"{message}\n\n📋 Estados permitidos desde '{estado_actual}': {', '.join(allowed)}"
        else:
            return False, f"{message}\n\n⚠️ '{estado_actual}' es un estado terminal y no puede cambiar."

    return True, message


def get_state_flow_diagram() -> str:
    """
    Get ASCII diagram of valid state flows

    Returns:
        Formatted state flow diagram
    """
    diagram = """
╔════════════════════════════════════════════════════════════════╗
║              FLUJO DE ESTADOS DE SOLICITUDES                   ║
╚════════════════════════════════════════════════════════════════╝

    🟡 ASIGNADA
        ↓
    ├─→ 🔵 EN PROCESO ──→ ✅ COMPLETADA (Terminal)
    │       ↓
    │   🟠 INCOMPLETA (Pausa)
    │       ↓
    │   (Reanudar) ──→ 🟡 ASIGNADA o 🔵 EN PROCESO
    │
    ├─→ 🟠 INCOMPLETA (Pausa)
    │
    └─→ ❌ CANCELADA (Terminal)

════════════════════════════════════════════════════════════════
Reglas:
  • No se puede volver atrás (salvo desde Incompleta)
  • Incompleta: pausa temporal entre cualquier estado
  • Completada y Cancelada: estados terminales
  • Cambios se registran con timestamp
════════════════════════════════════════════════════════════════
"""
    return diagram


# Example usage and tests
if __name__ == "__main__":
    print("State Flow Manager - Testing")
    print("=" * 60)

    validator = StateFlowValidator()

    # Test transitions
    test_cases = [
        ("Asignada", "En Proceso", True),
        ("Asignada", "Completada", False),
        ("En Proceso", "Completada", True),
        ("Completada", "En Proceso", False),
        ("Incompleta", "Asignada", True),
        ("Cancelada", "Asignada", False),
    ]

    print("\n📋 Testing State Transitions:")
    for current, next_state, expected in test_cases:
        is_valid, msg = validator.is_valid_transition(current, next_state)
        status = "✅" if is_valid == expected else "❌"
        print(f"{status} {current} → {next_state}: {is_valid}")

    # Test history tracking
    print("\n📝 Testing History Tracking:")
    history = ""
    history = StateHistoryTracker.add_to_history(
        history, "Asignada", "Admin", "Solicitud asignada inicialmente"
    )
    history = StateHistoryTracker.add_to_history(
        history, "En Proceso", "Juan", "Comenzó el procesamiento"
    )
    history = StateHistoryTracker.add_to_history(
        history, "Incompleta", "Juan", "Requiere información adicional"
    )
    history = StateHistoryTracker.add_to_history(
        history, "En Proceso", "Juan", "Reanudada después de obtener información"
    )

    print("\n📊 History:")
    print(history)

    print("\n📖 Formatted for display:")
    print(StateHistoryTracker.format_history_for_display(history))

    print("\n🔄 State Flow Diagram:")
    print(get_state_flow_diagram())

    print("\n" + "=" * 60)
    print("Testing complete!")
