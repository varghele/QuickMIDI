from typing import List, Dict, Any


class SongPart:
    def __init__(self, name: str, start_time: float, duration: float):
        self.name = name
        self.start_time = start_time
        self.duration = duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_time": self.start_time,
            "duration": self.duration
        }

    def from_dict(self, data: Dict[str, Any]):
        self.name = data.get("name", "")
        self.start_time = data.get("start_time", 0.0)
        self.duration = data.get("duration", 0.0)


class SongStructure:
    def __init__(self):
        self.parts: List[SongPart] = []
        self.bpm = 120.0

    def add_part(self, name: str, start_time: float, duration: float) -> SongPart:
        part = SongPart(name, start_time, duration)
        self.parts.append(part)
        return part

    def remove_part(self, part: SongPart):
        if part in self.parts:
            self.parts.remove(part)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bpm": self.bpm,
            "parts": [part.to_dict() for part in self.parts]
        }

    def from_dict(self, data: Dict[str, Any]):
        self.bpm = data.get("bpm", 120.0)
        self.parts.clear()
        for part_data in data.get("parts", []):
            part = SongPart("", 0, 0)
            part.from_dict(part_data)
            self.parts.append(part)
