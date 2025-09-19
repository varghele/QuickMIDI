from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from typing import List
from .lane import Lane, AudioLane, MidiLane


class PlaybackEngine(QObject):
    """Manages playback across all lanes with playhead synchronization"""

    position_changed = pyqtSignal(float)  # Emits current playback position in seconds
    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_halted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.current_position = 0.0  # Current playback position in seconds
        self.is_playing = False
        self.bpm = 120.0
        self.snap_to_grid = True
        self.pixels_per_beat = 60

        # Timer for playback updates (60 FPS for smooth playhead movement)
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_playback)
        self.playback_timer.setInterval(16)  # ~60 FPS (16ms)

        self.lanes: List[Lane] = []

    def set_lanes(self, lanes: List[Lane]):
        """Set the lanes to be controlled by this engine"""
        self.lanes = lanes

    def set_bpm(self, bpm: float):
        """Set the BPM for playback calculations"""
        self.bpm = bpm

    def set_snap_to_grid(self, snap: bool):
        """Enable/disable snap to grid for playhead"""
        self.snap_to_grid = snap

    def play(self):
        """Start playback from current position"""
        if not self.is_playing:
            self.is_playing = True
            self.playback_timer.start()
            self.playback_started.emit()

    def halt(self):
        """Pause playback at current position"""
        if self.is_playing:
            self.is_playing = False
            self.playback_timer.stop()
            self.playback_halted.emit()

    def stop(self):
        """Stop playback and reset to beginning"""
        self.is_playing = False
        self.playback_timer.stop()
        self.set_position(0.0)
        self.playback_stopped.emit()

    def set_position(self, position: float):
        """Set playback position (in seconds)"""
        if self.snap_to_grid:
            # Snap to nearest beat
            beat_duration = 60.0 / self.bpm  # seconds per beat
            position = round(position / beat_duration) * beat_duration

        self.current_position = max(0.0, position)
        self.position_changed.emit(self.current_position)

    def update_playback(self):
        """Update playback position (called by timer)"""
        if self.is_playing:
            # Advance by timer interval (16ms = 0.016s)
            self.current_position += 0.016
            self.position_changed.emit(self.current_position)

            # TODO: Trigger MIDI events and audio playback based on current position
            self.process_lane_events()

    def process_lane_events(self):
        """Process events for all lanes at current position"""
        for lane in self.lanes:
            if isinstance(lane, MidiLane):
                self.process_midi_lane(lane)
            elif isinstance(lane, AudioLane):
                self.process_audio_lane(lane)

    def process_midi_lane(self, lane: MidiLane):
        """Process MIDI events for a lane at current position"""
        if lane.muted:
            return

        for block in lane.midi_blocks:
            # Check if we should trigger this block
            if (block.start_time <= self.current_position <
                    block.start_time + block.duration):
                # TODO: Send MIDI message
                pass

    def process_audio_lane(self, lane: AudioLane):
        """Process audio playback for a lane at current position"""
        if lane.muted or not lane.audio_file_path:
            return
        # TODO: Handle audio playback
        pass
