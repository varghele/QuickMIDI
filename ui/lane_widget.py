from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                             QPushButton, QCheckBox, QSpinBox, QLineEdit,
                             QFrame, QFileDialog, QMessageBox, QComboBox,
                             QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPalette, QPainter, QPen, QColor, QWheelEvent
from core.lane import Lane, AudioLane, MidiLane
from .midi_block_widget import MidiBlockWidget
from styles import theme_manager


class TimelineWidget(QWidget):
    """Custom timeline widget with grid drawing and snap functionality"""

    zoom_changed = pyqtSignal(float)  # New signal for zoom changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bpm = 120.0
        self.zoom_factor = 1.0
        self.base_pixels_per_beat = 60
        self.pixels_per_beat = self.base_pixels_per_beat
        self.snap_to_grid = True
        self.playhead_position = 0.0  # Position in seconds
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        self.setMinimumHeight(60)
        self.setMinimumWidth(2000)  # Wide timeline for scrolling
        self.setStyleSheet("background-color: #f8f8f8; border: 1px solid #ddd;")

    def update_timeline_width(self):
        """Update timeline width based on zoom level"""
        self.pixels_per_beat = self.base_pixels_per_beat * self.zoom_factor
        new_width = max(2000, int(128 * self.pixels_per_beat))
        self.setMinimumWidth(new_width)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming"""
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # Shift + wheel = zoom
            delta = event.angleDelta().y()
            zoom_in = delta > 0

            # Get mouse position for zoom center
            mouse_x = event.position().x()

            # Calculate time position at mouse cursor before zoom
            time_at_mouse = mouse_x / self.pixels_per_beat * (60.0 / self.bpm)

            # Apply zoom
            old_zoom = self.zoom_factor
            if zoom_in:
                self.zoom_factor = min(self.max_zoom, self.zoom_factor * 1.2)
            else:
                self.zoom_factor = max(self.min_zoom, self.zoom_factor / 1.2)

            if self.zoom_factor != old_zoom:
                self.update_timeline_width()
                self.zoom_changed.emit(self.zoom_factor)

                # Maintain mouse position after zoom
                new_mouse_x = time_at_mouse * self.pixels_per_beat / (60.0 / self.bpm)
                scroll_offset = new_mouse_x - mouse_x

                # Notify parent scroll area to adjust position
                if hasattr(self.parent(), 'horizontalScrollBar'):
                    current_scroll = self.parent().horizontalScrollBar().value()
                    self.parent().horizontalScrollBar().setValue(int(current_scroll + scroll_offset))

                self.update()

            event.accept()
        else:
            # Normal wheel = scroll horizontally
            super().wheelEvent(event)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor externally"""
        self.zoom_factor = zoom_factor
        self.update_timeline_width()
        self.update()

    def set_bpm(self, bpm):
        """Set BPM for grid calculations"""
        self.bpm = bpm
        self.update()

    def set_pixels_per_beat(self, pixels):
        """Set zoom level (pixels per beat)"""
        self.pixels_per_beat = pixels
        self.update()

    def set_snap_to_grid(self, snap):
        """Enable/disable snap to grid"""
        self.snap_to_grid = snap

    def set_playhead_position(self, position: float):
        """Set playhead position and update display"""
        self.playhead_position = position
        self.update()

    def paintEvent(self, event):
        """Draw the grid lines"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw beat lines (every beat)
        beat_pen = QPen(QColor("#cccccc"), 1)
        painter.setPen(beat_pen)

        width = self.width()
        height = self.height()

        # Draw vertical grid lines for beats
        x = 0
        beat_count = 0
        while x < width:
            if beat_count % 4 == 0:  # Bar line (every 4 beats)
                bar_pen = QPen(QColor("#999999"), 2)
                painter.setPen(bar_pen)
            else:  # Beat line
                painter.setPen(beat_pen)

            # Convert float to int for drawLine
            x_int = int(x)
            painter.drawLine(x_int, 0, x_int, height)
            x += self.pixels_per_beat
            beat_count += 1

        # Draw time markers
        painter.setPen(QPen(QColor("#666666"), 1))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        x = 0.0  # Start as float for calculations
        bar_number = 1
        while x < width:
            if x > 0:  # Don't draw at x=0
                time_seconds = (bar_number - 1) * 4 * (60.0 / self.bpm)
                # Convert float to int for drawText
                x_int = int(x)
                painter.drawText(x_int + 2, 12, f"Bar {bar_number} ({time_seconds:.1f}s)")
            x += self.pixels_per_beat * 4  # Every 4 beats (1 bar)
            bar_number += 1

        # Draw playhead cursor
        playhead_x = int(self.playhead_position * self.pixels_per_beat * (self.bpm / 60.0))

        if 0 <= playhead_x <= width:
            # Playhead line
            playhead_pen = QPen(QColor("#FF4444"), 2)
            painter.setPen(playhead_pen)
            painter.drawLine(playhead_x, 0, playhead_x, height)


class LaneWidget(QFrame):
    remove_requested = pyqtSignal(object)
    scroll_position_changed = pyqtSignal(int)  # Emits horizontal scroll position
    zoom_changed = pyqtSignal(float)  # Signal for zoom changes

    def __init__(self, lane: Lane, parent=None):
        super().__init__(parent)
        self.lane = lane
        self.midi_block_widgets = []
        self.main_window = parent

        # Apply widget style
        self.setStyleSheet(theme_manager.get_lane_widget_style())

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
        controls_widget.setFixedWidth(250)
        controls_layout = QVBoxLayout(controls_widget)

        # Lane name and type (first row)
        name_layout = QHBoxLayout()
        self.name_edit = QLineEdit(self.lane.name)
        self.name_edit.textChanged.connect(self.on_name_changed)

        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(25, 25)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

        name_layout.addWidget(QLabel("Name:"))
        name_layout.addWidget(self.name_edit)
        name_layout.addWidget(self.remove_button)

        # Apply styles to input fields
        self.name_edit.setStyleSheet(theme_manager.get_line_edit_style())
        # Style the remove button
        self.remove_button.setStyleSheet(theme_manager.get_remove_button_style())

        controls_layout.addLayout(name_layout)

        # Lane-specific controls (second row)
        lane_specific_layout = QHBoxLayout()

        if isinstance(self.lane, MidiLane):
            self.setup_midi_controls(lane_specific_layout)
        elif isinstance(self.lane, AudioLane):
            self.setup_audio_controls(lane_specific_layout)

        controls_layout.addLayout(lane_specific_layout)

        # Mute, Solo, and Snap controls (third row)
        control_buttons_layout = QHBoxLayout()

        # Mute and Solo buttons
        self.mute_button = QPushButton("M")
        self.solo_button = QPushButton("S")

        # Make buttons smaller and more compact
        self.mute_button.setFixedSize(30, 25)
        self.solo_button.setFixedSize(30, 25)

        # Style the buttons
        self.mute_button.setCheckable(True)
        self.solo_button.setCheckable(True)

        self.mute_button.setChecked(self.lane.muted)
        self.solo_button.setChecked(self.lane.solo)

        # Set initial styles
        self.update_mute_button_style()
        self.update_solo_button_style()

        self.mute_button.toggled.connect(self.on_mute_toggled)
        self.solo_button.toggled.connect(self.on_solo_toggled)

        control_buttons_layout.addWidget(self.mute_button)
        control_buttons_layout.addWidget(self.solo_button)

        # Add snap to grid control for MIDI lanes
        if isinstance(self.lane, MidiLane):
            # Add some spacing between buttons and checkbox
            control_buttons_layout.addSpacing(10)

            self.snap_checkbox = QCheckBox("Snap")
            self.snap_checkbox.setChecked(True)
            self.snap_checkbox.toggled.connect(self.on_snap_toggled)
            control_buttons_layout.addWidget(self.snap_checkbox)

        control_buttons_layout.addStretch()  # Push everything to the left

        controls_layout.addLayout(control_buttons_layout)

        main_layout.addWidget(controls_widget)

        # Timeline section (right side) - scrollable
        self.timeline_scroll = QScrollArea()
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)  # Connect zoom signal
        #self.timeline_widget.setMinimumWidth(2000)  # Wide timeline

        if isinstance(self.lane, MidiLane):
            self.setup_midi_timeline()
        elif isinstance(self.lane, AudioLane):
            self.setup_audio_timeline()

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)

        main_layout.addWidget(self.timeline_scroll, 1)

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

        # Apply styles
        self.channel_spinbox.setStyleSheet(theme_manager.get_spinbox_style())
        self.channel_name_edit.setStyleSheet(theme_manager.get_line_edit_style())
        self.add_block_button.setStyleSheet(theme_manager.get_action_button_style())


    def setup_audio_controls(self, layout):
        # Load audio file button
        self.load_audio_button = QPushButton("Load Audio")
        self.load_audio_button.clicked.connect(self.load_audio_file)
        layout.addWidget(self.load_audio_button)

        # Volume control
        layout.addWidget(QLabel("Vol:"))
        self.volume_spinbox = QSpinBox()
        self.volume_spinbox.setRange(0, 100)
        self.volume_spinbox.setValue(int(self.lane.volume * 100))
        self.volume_spinbox.valueChanged.connect(self.on_volume_changed)
        layout.addWidget(self.volume_spinbox)
        layout.addStretch()  # Push controls to the left

        # Apply styles
        self.load_audio_button.setStyleSheet(theme_manager.get_action_button_style())
        self.volume_spinbox.setStyleSheet(theme_manager.get_spinbox_style())

    def set_playhead_position(self, position: float):
        """Set playhead position for this lane's timeline"""
        self.timeline_widget.set_playhead_position(position)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor for this lane's timeline"""
        self.timeline_widget.set_zoom_factor(zoom_factor)

        # Update MIDI block positions
        for block_widget in self.midi_block_widgets:
            if hasattr(block_widget, 'set_grid_size'):
                block_widget.set_grid_size(self.timeline_widget.pixels_per_beat)
            if hasattr(block_widget, 'update_position'):
                block_widget.update_position()

    def sync_scroll_position(self, position: int):
        """Sync scroll position with master timeline"""
        self.timeline_scroll.horizontalScrollBar().setValue(position)

    def setup_midi_timeline(self):
        # Create MIDI block widgets for existing blocks
        for block in self.lane.midi_blocks:
            self.create_midi_block_widget(block)

    def setup_audio_timeline(self):
        # Show audio file info if loaded
        if self.lane.audio_file_path:
            audio_label = QLabel(f"Audio: {self.lane.audio_file_path.split('/')[-1]}")
            audio_label.setParent(self.timeline_widget)
            audio_label.move(10, 20)
        else:
            placeholder_label = QLabel("Drag audio file here or use Load Audio button")
            placeholder_label.setStyleSheet("color: #888; font-style: italic;")
            placeholder_label.setParent(self.timeline_widget)
            placeholder_label.move(10, 20)

    def setup_drag_drop(self):
        if isinstance(self.lane, AudioLane):
            self.setAcceptDrops(True)

    def update_bpm(self, bpm):
        """Update BPM for grid calculations"""
        self.timeline_widget.set_bpm(bpm)
        for block_widget in self.midi_block_widgets:
            if hasattr(block_widget, 'update_position'):
                block_widget.update_position()

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
        block_widget = MidiBlockWidget(block, self.timeline_widget)
        block_widget.remove_requested.connect(self.remove_midi_block_widget)
        block_widget.position_changed.connect(self.on_block_position_changed)

        # Set grid properties
        block_widget.set_grid_size(self.timeline_widget.pixels_per_beat)
        block_widget.set_snap_to_grid(self.timeline_widget.snap_to_grid)

        self.midi_block_widgets.append(block_widget)
        block_widget.show()

    def add_midi_block(self):
        if isinstance(self.lane, MidiLane):
            # Add block at timeline start
            block = self.lane.add_midi_block(0.0, 1.0)
            self.create_midi_block_widget(block)

    def remove_midi_block_widget(self, block_widget):
        self.lane.remove_midi_block(block_widget.block)
        self.midi_block_widgets.remove(block_widget)
        block_widget.deleteLater()

    def on_block_position_changed(self, block_widget, new_start_time):
        """Handle when a MIDI block is moved"""
        # The block's start_time is already updated in the widget
        # We could add additional logic here if needed
        pass

    def load_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Audio File", "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg)")

        if file_path:
            self.lane.set_audio_file(file_path)
            self.refresh_audio_timeline()

    def refresh_audio_timeline(self):
        # Clear existing widgets
        for child in self.timeline_widget.findChildren(QLabel):
            child.deleteLater()

        # Re-setup timeline
        self.setup_audio_timeline()

    # Event handlers
    def on_name_changed(self, text):
        self.lane.name = text

    def on_mute_toggled(self, checked):
        self.lane.muted = checked
        self.update_mute_button_style()

    def on_solo_toggled(self, checked):
        self.lane.solo = checked
        self.update_solo_button_style()

    def on_channel_changed(self, value):
        if isinstance(self.lane, MidiLane):
            self.lane.set_midi_channel(value, self.channel_name_edit.text())

    def on_channel_name_changed(self, text):
        if isinstance(self.lane, MidiLane):
            self.lane.channel_name = text

    def on_volume_changed(self, value):
        if isinstance(self.lane, AudioLane):
            self.lane.volume = value / 100.0

    def on_snap_toggled(self, checked):
        """Toggle snap to grid for all MIDI blocks in this lane"""
        if isinstance(self.lane, MidiLane):
            self.timeline_widget.set_snap_to_grid(checked)
            for block_widget in self.midi_block_widgets:
                block_widget.set_snap_to_grid(checked)

    def update_mute_button_style(self):
        """Update mute button appearance based on state"""
        style = theme_manager.get_mute_button_compact_style(self.mute_button.isChecked())
        self.mute_button.setStyleSheet(style)

    def update_solo_button_style(self):
        """Update solo button appearance based on state"""
        style = theme_manager.get_solo_button_compact_style(self.solo_button.isChecked())
        self.solo_button.setStyleSheet(style)

