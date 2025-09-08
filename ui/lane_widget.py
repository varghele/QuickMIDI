from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QCheckBox, QSpinBox, QLineEdit,
                             QFrame, QFileDialog, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPalette
from core.lane import Lane, AudioLane, MidiLane
from .midi_block_widget import MidiBlockWidget


class LaneWidget(QFrame):
    remove_requested = pyqtSignal(object)  # Emits self when removal is requested

    def __init__(self, lane: Lane, parent=None):
        super().__init__(parent)
        self.lane = lane
        self.midi_block_widgets = []

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setMinimumHeight(80)
        self.setMaximumHeight(120)

        self.setup_ui()
        self.setup_drag_drop()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)

        # Lane controls section (left side)
        controls_widget = QWidget()
        controls_widget.setFixedWidth(200)
        controls_layout = QVBoxLayout(controls_widget)

        # Lane name and type
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit(self.lane.name)
        self.name_edit.textChanged.connect(self.on_name_changed)

        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(25, 25)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

        name_layout.addWidget(QLabel("Name:"))
        name_layout.addWidget(self.name_edit)
        name_layout.addWidget(self.remove_button)

        controls_layout.addLayout(name_layout)

        # Lane-specific controls
        lane_specific_layout = QHBoxLayout()

        # Mute and Solo buttons
        self.mute_checkbox = QCheckBox("Mute")
        self.solo_checkbox = QCheckBox("Solo")
        self.mute_checkbox.setChecked(self.lane.muted)
        self.solo_checkbox.setChecked(self.lane.solo)

        self.mute_checkbox.toggled.connect(self.on_mute_toggled)
        self.solo_checkbox.toggled.connect(self.on_solo_toggled)

        lane_specific_layout.addWidget(self.mute_checkbox)
        lane_specific_layout.addWidget(self.solo_checkbox)

        if isinstance(self.lane, MidiLane):
            self.setup_midi_controls(lane_specific_layout)
        elif isinstance(self.lane, AudioLane):
            self.setup_audio_controls(lane_specific_layout)

        controls_layout.addLayout(lane_specific_layout)

        main_layout.addWidget(controls_widget)

        # Timeline section (right side)
        self.timeline_widget = QWidget()
        self.timeline_widget.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        self.timeline_layout = QHBoxLayout(self.timeline_widget)
        self.timeline_layout.setContentsMargins(5, 5, 5, 5)

        if isinstance(self.lane, MidiLane):
            self.setup_midi_timeline()
        elif isinstance(self.lane, AudioLane):
            self.setup_audio_timeline()

        main_layout.addWidget(self.timeline_widget, 1)  # Stretch factor 1

    def setup_midi_controls(self, layout):
        # MIDI Channel selection
        layout.addWidget(QLabel("Ch:"))
        self.channel_spinbox = QSpinBox()
        self.channel_spinbox.setRange(1, 16)
        self.channel_spinbox.setValue(self.lane.midi_channel)
        self.channel_spinbox.valueChanged.connect(self.on_channel_changed)
        layout.addWidget(self.channel_spinbox)

        # Channel name
        self.channel_name_edit = QLineEdit(self.lane.channel_name)
        self.channel_name_edit.setPlaceholderText("Channel Name")
        self.channel_name_edit.textChanged.connect(self.on_channel_name_changed)
        layout.addWidget(self.channel_name_edit)

        # Add MIDI block button
        self.add_block_button = QPushButton("Add Block")
        self.add_block_button.clicked.connect(self.add_midi_block)
        layout.addWidget(self.add_block_button)

    def setup_audio_controls(self, layout):
        # Load audio file button
        self.load_audio_button = QPushButton("Load Audio")
        self.load_audio_button.clicked.connect(self.load_audio_file)
        layout.addWidget(self.load_audio_button)

        # Volume control (simplified)
        layout.addWidget(QLabel("Vol:"))
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setValue(int(self.lane.volume * 100))
        self.volume_spinbox.valueChanged.connect(self.on_volume_changed)
        layout.addWidget(self.volume_spinbox)

    def setup_midi_timeline(self):
        # Create MIDI block widgets for existing blocks
        for block in self.lane.midi_blocks:
            self.create_midi_block_widget(block)

    def setup_audio_timeline(self):
        # Show audio file info if loaded
        if self.lane.audio_file_path:
            audio_label = QLabel(f"Audio: {self.lane.audio_file_path.split('/')[-1]}")
            self.timeline_layout.addWidget(audio_label)
        else:
            placeholder_label = QLabel("Drag audio file here or use Load Audio button")
            placeholder_label.setStyleSheet("color: #888; font-style: italic;")
            self.timeline_layout.addWidget(placeholder_label)

    def setup_drag_drop(self):
        if isinstance(self.lane, AudioLane):
            self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if isinstance(self.lane, AudioLane) and event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().lower().endswith(('.wav', '.mp3', '.flac', '.ogg')):
                event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if isinstance(self.lane, AudioLane) and event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.lane.set_audio_file(file_path)
            self.refresh_audio_timeline()
            event.acceptProposedAction()

    def create_midi_block_widget(self, block):
        block_widget = MidiBlockWidget(block, self)
        block_widget.remove_requested.connect(self.remove_midi_block_widget)
        self.midi_block_widgets.append(block_widget)
        self.timeline_layout.addWidget(block_widget)

    def add_midi_block(self):
        if isinstance(self.lane, MidiLane):
            # Add block at current timeline position (simplified to 0 for now)
            block = self.lane.add_midi_block(0.0, 1.0)
            self.create_midi_block_widget(block)

    def remove_midi_block_widget(self, block_widget):
        self.lane.remove_midi_block(block_widget.block)
        self.midi_block_widgets.remove(block_widget)
        self.timeline_layout.removeWidget(block_widget)
        block_widget.deleteLater()

    def load_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg)")

        if file_path:
            self.lane.set_audio_file(file_path)
            self.refresh_audio_timeline()

    def refresh_audio_timeline(self):
        # Clear existing widgets
        for i in reversed(range(self.timeline_layout.count())):
            child = self.timeline_layout.itemAt(i).widget()
            if child:
                child.deleteLater()

        # Re-setup timeline
        self.setup_audio_timeline()

    # Event handlers
    def on_name_changed(self, text):
        self.lane.name = text

    def on_mute_toggled(self, checked):
        self.lane.muted = checked

    def on_solo_toggled(self, checked):
        self.lane.solo = checked

    def on_channel_changed(self, value):
        if isinstance(self.lane, MidiLane):
            self.lane.set_midi_channel(value, self.channel_name_edit.text())

    def on_channel_name_changed(self, text):
        if isinstance(self.lane, MidiLane):
            self.lane.channel_name = text

    def on_volume_changed(self, value):
        if isinstance(self.lane, AudioLane):
            self.lane.volume = value / 100.0
