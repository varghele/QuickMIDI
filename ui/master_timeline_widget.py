from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QPolygon, QWheelEvent
from .lane_widget import TimelineWidget


class MasterTimelineWidget(TimelineWidget):
    """Master timeline widget with playhead that spans all lanes"""

    playhead_moved = pyqtSignal(float)  # Emits new playhead position in seconds
    zoom_changed = pyqtSignal(float)  # Emits new zoom level (pixels per beat)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.playhead_position = 0.0  # Position in seconds
        self.dragging_playhead = False
        self.zoom_factor = 1.0  # Current zoom multiplier
        self.base_pixels_per_beat = 60  # Base zoom level
        self.min_zoom = 0.1  # Minimum zoom (very zoomed out)
        self.max_zoom = 5.0  # Maximum zoom (very zoomed in)

        self.setMinimumHeight(40)
        self.setMinimumWidth(2000)  # Wide timeline for scrolling
        self.setStyleSheet("""
            MasterTimelineWidget {
                background-color: #e8e8e8;
                border: 2px solid #bbb;
                border-radius: 4px;
            }
        """)

    def update_timeline_width(self):
        """Update timeline width based on zoom level"""
        self.pixels_per_beat = self.base_pixels_per_beat * self.zoom_factor
        # Set width for 32 bars (128 beats) at current zoom
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

    def set_playhead_position(self, position: float):
        """Set playhead position and update display"""
        self.playhead_position = position
        self.update()

        # Auto-scroll to keep playhead visible
        self.ensure_playhead_visible()

    def ensure_playhead_visible(self):
        """Ensure playhead is visible by scrolling if necessary"""
        if hasattr(self.parent(), 'ensureWidgetVisible'):
            playhead_x = int(self.playhead_position * self.pixels_per_beat * (self.bpm / 60.0))
            margin = 100
            self.parent().ensureVisible(playhead_x, 0, margin, self.height())

    def paintEvent(self, event):
        """Draw the timeline grid and playhead"""
        super().paintEvent(event)  # Draw the grid from parent class

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw playhead
        playhead_x = int(self.playhead_position * self.pixels_per_beat * (self.bpm / 60.0))

        # Draw playhead line (full height)
        playhead_pen = QPen(QColor("#FF4444"), 3)
        painter.setPen(playhead_pen)
        painter.drawLine(playhead_x, 0, playhead_x, self.height())

        # Playhead triangle at top
        triangle_size = 8
        triangle = QPolygon([
            QPoint(playhead_x, 0),
            QPoint(playhead_x - triangle_size, triangle_size),
            QPoint(playhead_x + triangle_size, triangle_size)
        ])

        painter.setBrush(QColor("#FF4444"))
        painter.drawPolygon(triangle)

        # Draw time display
        painter.setPen(QPen(QColor("#333333"), 1))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        time_text = f"{self.playhead_position:.2f}s"
        zoom_text = f"Zoom: {self.zoom_factor:.1f}x"
        painter.drawText(10, self.height() - 10, time_text)
        #painter.drawText(10, self.height() - 3, zoom_text)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for playhead dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = True
            self.update_playhead_from_mouse(event.pos().x())

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for playhead dragging"""
        if self.dragging_playhead:
            self.update_playhead_from_mouse(event.pos().x())

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to stop playhead dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_playhead = False

    def update_playhead_from_mouse(self, x_pos: int):
        """Update playhead position based on mouse position"""
        # Convert pixel position to time
        time_position = x_pos / (self.pixels_per_beat * (self.bpm / 60.0))

        # Apply snap to grid if enabled
        if self.snap_to_grid:
            beat_duration = 60.0 / self.bpm
            time_position = round(time_position / beat_duration) * beat_duration

        time_position = max(0.0, time_position)
        self.playhead_position = time_position
        self.playhead_moved.emit(time_position)
        self.update()


class MasterTimelineContainer(QWidget):
    """Container for master timeline with label"""

    playhead_moved = pyqtSignal(float)
    scroll_position_changed = pyqtSignal(int) # Emits horizontal scroll position
    zoom_changed = pyqtSignal(float)  # New signal for zoom changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(60)  # Instead of setFixedHeight
        self.setMaximumHeight(65)  # Optional: set a maximum height too

        # Timeline label (matches lane control width)
        timeline_label = QWidget()
        timeline_label.setFixedWidth(250)
        label_layout = QHBoxLayout(timeline_label)
        label_layout.addWidget(QLabel("Master Timeline"))
        label_layout.addStretch()

        # Scrollable timeline area
        self.timeline_scroll = QScrollArea()
        # Master timeline widget
        self.timeline_widget = MasterTimelineWidget()
        self.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)
        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)

        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)

        layout.addWidget(timeline_label)
        layout.addWidget(self.timeline_scroll, 1)

    def set_bpm(self, bpm: float):
        """Set BPM for timeline calculations"""
        self.timeline_widget.set_bpm(bpm)

    def set_playhead_position(self, position: float):
        """Set playhead position"""
        self.timeline_widget.set_playhead_position(position)

    def set_snap_to_grid(self, snap: bool):
        """Set snap to grid for playhead"""
        self.timeline_widget.set_snap_to_grid(snap)

    def sync_scroll_position(self, position: int):
        """Sync scroll position with other timelines"""
        self.timeline_scroll.horizontalScrollBar().setValue(position)

    def set_zoom_factor(self, zoom_factor: float):
        """Set zoom factor for timeline"""
        self.timeline_widget.zoom_factor = zoom_factor
        self.timeline_widget.update_timeline_width()
        self.timeline_widget.update()
