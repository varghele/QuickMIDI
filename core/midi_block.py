from typing import Dict, Any
from enum import Enum


class MidiMessageType(Enum):
    PROGRAM_CHANGE = "PC"
    CONTROL_CHANGE = "CC"
    NOTE_ON = "NOTE_ON"
    NOTE_OFF = "NOTE_OFF"


class MidiBlock:
    def __init__(self, start_time: float, duration: float):
        self.start_time = start_time
        self.duration = duration
        self.message_type = MidiMessageType.CONTROL_CHANGE
        self.value1 = 0  # CC number, Program number, or Note number
        self.value2 = 127  # CC value, velocity, etc.
        self.name = "MIDI Block"

    def set_program_change(self, program_number: int):
        self.message_type = MidiMessageType.PROGRAM_CHANGE
        self.value1 = program_number
        self.value2 = 0

    def set_control_change(self, cc_number: int, cc_value: int):
        self.message_type = MidiMessageType.CONTROL_CHANGE
        self.value1 = cc_number
        self.value2 = cc_value

    def set_note(self, note_number: int, velocity: int, note_on: bool = True):
        self.message_type = MidiMessageType.NOTE_ON if note_on else MidiMessageType.NOTE_OFF
        self.value1 = note_number
        self.value2 = velocity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time,
            "duration": self.duration,
            "message_type": self.message_type.value,
            "value1": self.value1,
            "value2": self.value2,
            "name": self.name
        }

    def from_dict(self, data: Dict[str, Any]):
        self.start_time = data.get("start_time", 0.0)
        self.duration = data.get("duration", 1.0)
        self.message_type = MidiMessageType(data.get("message_type", "CC"))
        self.value1 = data.get("value1", 0)
        self.value2 = data.get("value2", 127)
        self.name = data.get("name", "MIDI Block")
