from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QSpinBox, QLineEdit,
                             QFrame, QDialog, QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPalette, QMouseEvent, QPainter, QPen
from core.midi_block import MidiBlock, MidiMessageType


class MidiBlockWidget(QFrame):
    remove_requested = pyqtSignal(object)
    position_changed = pyqtSignal(object, float)  # Emits self and new start_time

    def __init__(self, block: MidiBlock, parent=None):
        super().__init__(parent)
        self.block = block
        self.parent_widget = parent
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.snap_to_grid = True
        self.grid_size = 60  # pixels per beat (will be calculated based on BPM and zoom)

        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(1)
        self.setFixedHeight(50)
        self.setMinimumWidth(80)
        self.setStyleSheet("""
            MidiBlockWidget {
                background-color: #4CAF50;
                border: 2px solid #45a049;
                border-radius: 5px;
            }
            MidiBlockWidget:hover {
                background-color: #5CBF60;
            }
            MidiBlockWidget[dragging="true"] {
                background-color: #66BB6A;
                border: 2px solid #4CAF50;
                opacity: 0.8;
            }
        """)

        self.setup_ui()
        self.update_position()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(1)

        # Block name/type
        self.name_label = QLabel(self.block.name)
        self.name_label.setStyleSheet("color: white; font-weight: bold; font-size: 9px;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        # Message type and values
        self.info_label = QLabel(self.get_block_info())
        self.info_label.setStyleSheet("color: white; font-size: 8px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)

        # Time info
        self.time_label = QLabel(f"{self.block.start_time:.2f}s")
        self.time_label.setStyleSheet("color: white; font-size: 7px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        # Remove button (small, top-right corner)
        self.remove_button = QPushButton("×")
        self.remove_button.setFixedSize(12, 12)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self))

        # Position remove button in top-right corner
        self.remove_button.setParent(self)
        self.remove_button.move(self.width() - 15, 3)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Keep remove button in top-right corner
        if hasattr(self, 'remove_button'):
            self.remove_button.move(self.width() - 15, 3)

    def get_block_info(self):
        """Get display string for block info"""
        if self.block.message_type == MidiMessageType.PROGRAM_CHANGE:
            return f"PC: {self.block.value1}"
        elif self.block.message_type == MidiMessageType.CONTROL_CHANGE:
            return f"CC{self.block.value1}: {self.block.value2}"
        elif self.block.message_type == MidiMessageType.NOTE_ON:
            return f"Note: {self.block.value1}"
        elif self.block.message_type == MidiMessageType.NOTE_OFF:
            return f"Note Off: {self.block.value1}"
        return "MIDI"

    def update_position(self):
        """Update widget position based on block start time"""
        if self.parent_widget:
            # Calculate position based on start time and grid
            x_pos = int(self.block.start_time * self.grid_size)
            self.move(x_pos, self.y())

            # Update width based on duration
            width = max(80, int(self.block.duration * self.grid_size))
            self.setFixedWidth(width)

            # Update time label
            self.time_label.setText(f"{self.block.start_time:.2f}s")

    def set_grid_size(self, pixels_per_beat):
        """Set the grid size for positioning calculations"""
        self.grid_size = pixels_per_beat
        self.update_position()

    def set_snap_to_grid(self, snap):
        """Enable or disable snap to grid"""
        self.snap_to_grid = snap

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.pos()
            self.setProperty("dragging", "true")
            self.setStyleSheet(self.styleSheet())  # Refresh style
            self.raise_()  # Bring to front while dragging
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            # Calculate new position
            delta = event.pos() - self.drag_start_pos
            new_pos = self.pos() + delta

            # Constrain to parent widget bounds
            if self.parent_widget:
                parent_rect = self.parent_widget.rect()
                new_pos.setX(max(0, min(new_pos.x(), parent_rect.width() - self.width())))
                new_pos.setY(self.y())  # Keep Y position fixed

            # Apply snap to grid if enabled
            if self.snap_to_grid:
                grid_x = round(new_pos.x() / self.grid_size) * self.grid_size
                new_pos.setX(int(grid_x))

            self.move(new_pos)

            # Update block start time based on position
            new_start_time = new_pos.x() / self.grid_size
            self.block.start_time = max(0, new_start_time)
            self.time_label.setText(f"{self.block.start_time:.2f}s")

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            self.setProperty("dragging", "false")
            self.setStyleSheet(self.styleSheet())  # Refresh style

            # Emit position changed signal
            self.position_changed.emit(self, self.block.start_time)

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.dragging:
            self.edit_block()
        super().mouseDoubleClickEvent(event)

    def edit_block(self):
        """Open edit dialog for the MIDI block"""
        dialog = MidiBlockEditDialog(self.block, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_display()

    def update_display(self):
        """Update the widget display after block changes"""
        self.name_label.setText(self.block.name)
        self.info_label.setText(self.get_block_info())
        self.update_position()


class MidiBlockEditDialog(QDialog):
    def __init__(self, block: MidiBlock, parent=None):
        super().__init__(parent)
        self.block = block

        self.setWindowTitle("Edit MIDI Block")
        self.setModal(True)
        self.resize(300, 300)

        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Block name
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)

        # Start time and duration
        self.start_time_spinbox = QSpinBox()
        self.start_time_spinbox.setRange(0, 99999)
        self.start_time_spinbox.setSuffix(" ms")
        form_layout.addRow("Start Time:", self.start_time_spinbox)

        self.duration_spinbox = QSpinBox()
        self.duration_spinbox.setRange(100, 99999)
        self.duration_spinbox.setSuffix(" ms")
        form_layout.addRow("Duration:", self.duration_spinbox)

        # Message type
        self.message_type_combo = QComboBox()
        self.message_type_combo.addItems(["Control Change", "Program Change", "Note On", "Note Off"])
        self.message_type_combo.currentTextChanged.connect(self.on_message_type_changed)
        form_layout.addRow("Message Type:", self.message_type_combo)

        # Value 1 (CC number, Program number, Note number)
        self.value1_spinbox = QSpinBox()
        self.value1_spinbox.setRange(0, 127)
        self.value1_label = QLabel("CC Number:")
        form_layout.addRow(self.value1_label, self.value1_spinbox)

        # Value 2 (CC value, velocity, etc.)
        self.value2_spinbox = QSpinBox()
        self.value2_spinbox.setRange(0, 127)
        self.value2_label = QLabel("CC Value:")
        form_layout.addRow(self.value2_label, self.value2_spinbox)

        layout.addLayout(form_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_values(self):
        """Load current block values into the form"""
        self.name_edit.setText(self.block.name)
        self.start_time_spinbox.setValue(int(self.block.start_time * 1000))
        self.duration_spinbox.setValue(int(self.block.duration * 1000))

        # Set message type
        type_map = {
            MidiMessageType.CONTROL_CHANGE: 0,
            MidiMessageType.PROGRAM_CHANGE: 1,
            MidiMessageType.NOTE_ON: 2,
            MidiMessageType.NOTE_OFF: 3
        }
        self.message_type_combo.setCurrentIndex(type_map.get(self.block.message_type, 0))

        self.value1_spinbox.setValue(self.block.value1)
        self.value2_spinbox.setValue(self.block.value2)

        self.on_message_type_changed(self.message_type_combo.currentText())

    def on_message_type_changed(self, text):
        """Update labels based on selected message type"""
        if text == "Control Change":
            self.value1_label.setText("CC Number:")
            self.value2_label.setText("CC Value:")
            self.value2_spinbox.setEnabled(True)
        elif text == "Program Change":
            self.value1_label.setText("Program Number:")
            self.value2_label.setText("(Unused)")
            self.value2_spinbox.setEnabled(False)
        elif text in ["Note On", "Note Off"]:
            self.value1_label.setText("Note Number:")
            self.value2_label.setText("Velocity:")
            self.value2_spinbox.setEnabled(True)

    def accept(self):
        """Save values back to the block"""
        self.block.name = self.name_edit.text()
        self.block.start_time = self.start_time_spinbox.value() / 1000.0
        self.block.duration = self.duration_spinbox.value() / 1000.0

        # Set message type and values
        text = self.message_type_combo.currentText()
        if text == "Control Change":
            self.block.set_control_change(self.value1_spinbox.value(), self.value2_spinbox.value())
        elif text == "Program Change":
            self.block.set_program_change(self.value1_spinbox.value())
        elif text == "Note On":
            self.block.set_note(self.value1_spinbox.value(), self.value2_spinbox.value(), True)
        elif text == "Note Off":
            self.block.set_note(self.value1_spinbox.value(), self.value2_spinbox.value(), False)

        super().accept()
