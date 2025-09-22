from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QPolygon, QWheelEvent, QBrush
from .lane_widget import TimelineWidget


class MasterTimelineWidget(TimelineWidget):
    """Master timeline widget with playhead that spans all lanes"""

    playhead_moved = pyqtSignal(float)  # Emits new playhead position in seconds
    zoom_changed = pyqtSignal(float)  # Emits new zoom level (pixels per beat)

    def __init__(self, parent=None):
        # Initialize ALL attributes BEFORE calling super()
        self.song_structure = None  # Will be set from main window
        self.playhead_position = 0.0  # Position in seconds
        self.dragging_playhead = False
        self.zoom_factor = 1.0  # Current zoom multiplier
        self.base_pixels_per_beat = 60  # Base zoom level
        self.min_zoom = 0.1  # Minimum zoom (very zoomed out)
        self.max_zoom = 5.0  # Maximum zoom (very zoomed in)

        super().__init__(parent)

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
        """Update timeline width based on zoom level and song structure"""
        self.pixels_per_beat = self.base_pixels_per_beat * self.zoom_factor

        if hasattr(self, 'song_structure') and self.song_structure and hasattr(self.song_structure,
                                                                               'parts') and self.song_structure.parts:
            try:
                total_duration = self.song_structure.get_total_duration()
                avg_bpm = sum(part.bpm for part in self.song_structure.parts) / len(self.song_structure.parts)
                total_beats = (total_duration / 60.0) * avg_bpm
                new_width = max(2000, int(total_beats * self.pixels_per_beat))
            except (AttributeError, ZeroDivisionError):
                new_width = max(2000, int(128 * self.pixels_per_beat))
        else:
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

    def set_song_structure(self, song_structure):
        """Set the song structure for visualization"""
        self.song_structure = song_structure
        self.update_timeline_width()
        self.update()

    def get_current_bpm(self) -> float:
        """Get BPM at current playhead position"""
        if self.song_structure:
            return self.song_structure.get_bpm_at_time(self.playhead_position)
        return self.bpm

    def get_previous_part_bpm(self, current_part) -> float:
        """Get BPM of the previous part"""
        try:
            if self.song_structure and self.song_structure.parts:
                part_index = self.song_structure.parts.index(current_part)
                if part_index > 0:
                    return self.song_structure.parts[part_index - 1].bpm
        except (ValueError, IndexError, AttributeError):
            pass
        return current_part.bpm

    def paintEvent(self, event):
        """Draw the master timeline - simplified approach"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Draw song structure parts as colored backgrounds FIRST
        if (hasattr(self, 'song_structure') and self.song_structure and
            hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            try:
                self.draw_song_structure(painter, width, height)
            except Exception as e:
                print(f"Error drawing song structure: {e}")

        # Draw grid
        self.draw_grid(painter, width, height)

        # Draw playhead
        self.draw_playhead(painter, width, height)

        # Draw info text
        #try:
        #    self.draw_info_text(painter)
        #except Exception as e:
        #    print(f"Error drawing info text: {e}")

    def draw_song_structure(self, painter, width, height):
        """Draw song structure parts as colored segments"""
        try:
            for part in self.song_structure.parts:
                start_x = self.time_to_pixel(part.start_time)
                end_x = self.time_to_pixel(part.start_time + part.duration)

                if end_x < 0 or start_x > width:
                    continue

                # Draw colored background
                color = QColor(part.color)
                color.setAlpha(100)
                painter.fillRect(int(start_x), 0, int(end_x - start_x), height, color)

                # Draw part border
                border_pen = QPen(QColor(part.color), 2)
                painter.setPen(border_pen)
                painter.drawRect(int(start_x), 0, int(end_x - start_x), height)

                # Draw part name
                if end_x - start_x > 50:
                    painter.setPen(QPen(QColor("#000000"), 1))
                    font = painter.font()
                    font.setPointSize(9)
                    font.setBold(True)
                    painter.setFont(font)

                    text_rect = QRectF(start_x + 5, 5, end_x - start_x - 10, 20)
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft, part.name)

                    # Draw BPM info - FIXED TYPO
                    font.setPointSize(8)
                    font.setBold(False)
                    painter.setFont(font)
                    bpm_text = f"{part.bpm} BPM"
                    if part.transition == "gradual":
                        prev_bpm = self.get_previous_part_bpm(part)
                        if prev_bpm != part.bpm:
                            bpm_text = f"{prev_bpm}->{part.bpm} BPM"  # FIXED: removed special character

                    bpm_rect = QRectF(start_x + 5, 25, end_x - start_x - 10, 15)
                    painter.drawText(bpm_rect, Qt.AlignmentFlag.AlignLeft, bpm_text)
        except Exception as e:
            print(f"Error in draw_song_structure: {e}")

    def draw_grid(self, painter, width, height):
        """Override to draw song structure-aware grid"""
        if (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'parts') and self.song_structure.parts):
            try:
                # Draw grid based on song structure
                bar_pen = QPen(QColor("#999999"), 2)

                for part in self.song_structure.parts:
                    start_x = self.time_to_pixel(part.start_time)

                    # Draw bar lines for this part
                    for bar in range(part.num_bars + 1):
                        if part.num_bars > 0:
                            bar_time = part.start_time + (bar / part.num_bars) * part.duration
                            bar_x = self.time_to_pixel(bar_time)

                            if 0 <= bar_x <= width:
                                painter.setPen(bar_pen)
                                painter.drawLine(int(bar_x), 0, int(bar_x), height)
            except (AttributeError, ZeroDivisionError, TypeError):
                # Fall back to parent's grid drawing
                super().draw_grid(painter, width, height)
        else:
            # Fall back to parent's grid drawing
            super().draw_grid(painter, width, height)

    def draw_playhead(self, painter, width, height):
        """Override to draw enhanced playhead with triangle"""
        try:
            playhead_x = self.time_to_pixel(self.playhead_position)

            if 0 <= playhead_x <= width:
                # Playhead line
                playhead_pen = QPen(QColor("#FF4444"), 3)
                painter.setPen(playhead_pen)
                painter.drawLine(int(playhead_x), 0, int(playhead_x), height)

                # Playhead triangle at top
                triangle_size = 8
                triangle = QPolygon([
                    QPoint(int(playhead_x), 0),
                    QPoint(int(playhead_x) - triangle_size, triangle_size),
                    QPoint(int(playhead_x) + triangle_size, triangle_size)
                ])

                painter.setBrush(QBrush(QColor("#FF4444")))
                painter.drawPolygon(triangle)
        except (AttributeError, TypeError):
            # Fall back to parent's playhead drawing
            super().draw_playhead(painter, width, height)

    def draw_info_text(self, painter):
        """Draw time, BPM, and zoom information"""
        painter.setPen(QPen(QColor("#333333"), 1))
        font = painter.font()
        font.setPointSize(9)
        font.setBold(True)
        painter.setFont(font)

        # Current time
        time_text = f"{self.playhead_position:.2f}s"
        painter.drawText(10, self.height() - 35, time_text)

        # Current BPM
        current_bpm = self.get_current_bpm()
        bpm_text = f"BPM: {current_bpm:.1f}"
        painter.drawText(10, self.height() - 20, bpm_text)

        # Zoom level
        zoom_text = f"Zoom: {self.zoom_factor:.1f}x"
        painter.drawText(10, self.height() - 5, zoom_text)

        # Current song part
        if (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'get_part_at_time')):
            try:
                current_part = self.song_structure.get_part_at_time(self.playhead_position)
                if current_part:
                    part_text = f"Part: {current_part.name}"
                    painter.drawText(120, self.height() - 20, part_text)
            except Exception as e:
                print(f"Error getting current part: {e}")

    def time_to_pixel(self, time: float) -> float:
        """Convert time in seconds to pixel position"""
        try:
            if (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'get_bpm_at_time')):
                current_bpm = self.song_structure.get_bpm_at_time(time)
                beats = (time / 60.0) * current_bpm
                return beats * self.pixels_per_beat / (current_bpm / 60.0)
            else:
                beats = (time / 60.0) * self.bpm
                return beats * self.pixels_per_beat / (self.bpm / 60.0)
        except (AttributeError, ZeroDivisionError):
            # Fallback calculation
            beats = (time / 60.0) * self.bpm
            return beats * self.pixels_per_beat / (self.bpm / 60.0)

    def pixel_to_time(self, pixel: float) -> float:
        """Convert pixel position to time in seconds"""
        try:
            if (hasattr(self, 'song_structure') and self.song_structure and
                hasattr(self.song_structure, 'parts') and self.song_structure.parts):
                avg_bpm = sum(part.bpm for part in self.song_structure.parts) / len(self.song_structure.parts)
                beats = pixel * (avg_bpm / 60.0) / self.pixels_per_beat
                return (beats / avg_bpm) * 60.0
            else:
                beats = pixel * (self.bpm / 60.0) / self.pixels_per_beat
                return (beats / self.bpm) * 60.0
        except (AttributeError, ZeroDivisionError):
            beats = pixel * (self.bpm / 60.0) / self.pixels_per_beat
            return (beats / self.bpm) * 60.0

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
        time_position = self.pixel_to_time(x_pos)

        # Apply snap to grid if enabled
        if self.snap_to_grid:
            # Snap to beat based on current BPM
            current_bpm = self.get_current_bpm()
            beat_duration = 60.0 / current_bpm
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
        layout = QVBoxLayout(self)  # FIXED: Changed from QHBoxLayout to QVBoxLayout
        layout.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(95)
        self.setMaximumHeight(100)

        # Top row with timeline label and info
        top_row_layout = QHBoxLayout()

        # Timeline label (matches lane control width)
        timeline_label = QWidget()
        timeline_label.setFixedWidth(250)
        label_layout = QHBoxLayout(timeline_label)
        label_layout.addWidget(QLabel("Master Timeline"))
        label_layout.addStretch()

        # Info display widget
        self.info_widget = QLabel()
        self.info_widget.setStyleSheet("color: #333; font-size: 10px; font-weight: bold;")
        self.info_widget.setText("Time: 0.00s | BPM: 120.0 | Zoom: 1.0x")

        top_row_layout.addWidget(timeline_label)
        top_row_layout.addWidget(self.info_widget, 1)

        # Bottom row with scrollable timeline
        bottom_row_layout = QHBoxLayout()

        # Empty space to align with timeline label
        spacer_widget = QWidget()
        spacer_widget.setFixedWidth(250)

        # Scrollable timeline area
        self.timeline_scroll = QScrollArea()
        self.timeline_widget = MasterTimelineWidget()
        self.timeline_widget.playhead_moved.connect(self.playhead_moved.emit)
        self.timeline_widget.zoom_changed.connect(self.zoom_changed.emit)
        self.timeline_widget.playhead_moved.connect(self.update_info_display)  # New connection

        self.timeline_scroll.setWidget(self.timeline_widget)
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Connect scroll events
        self.timeline_scroll.horizontalScrollBar().valueChanged.connect(
            self.scroll_position_changed.emit)

        bottom_row_layout.addWidget(spacer_widget)
        bottom_row_layout.addWidget(self.timeline_scroll, 1)

        # FIXED: Add both rows to the main layout (removed the incorrect lines)
        layout.addLayout(top_row_layout)
        layout.addLayout(bottom_row_layout)

    def update_info_display(self, position: float):
        """Update the info display with current values"""
        current_bpm = self.timeline_widget.get_current_bpm()
        zoom_factor = self.timeline_widget.zoom_factor

        # Get current song part if available
        part_info = ""
        if (hasattr(self.timeline_widget, 'song_structure') and
                self.timeline_widget.song_structure):
            current_part = self.timeline_widget.song_structure.get_part_at_time(position)
            if current_part:
                part_info = f" | Part: {current_part.name}"

        info_text = f"Time: {position:.2f}s | BPM: {current_bpm:.1f} | Zoom: {zoom_factor:.1f}x{part_info}"
        self.info_widget.setText(info_text)

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
