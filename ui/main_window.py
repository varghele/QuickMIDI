from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QWidget, QPushButton, QScrollArea, QMenuBar,
                             QFileDialog, QMessageBox, QLabel, QSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from core.project import Project
from core.lane import AudioLane, MidiLane
from .lane_widget import LaneWidget
from utils.file_manager import FileManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self.file_manager = FileManager()
        self.lane_widgets = []

        self.setWindowTitle("MIDI Track Creator")
        self.setGeometry(100, 100, 1200, 800)

        self.setup_ui()
        self.setup_menu()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Transport controls
        transport_layout = QHBoxLayout()

        self.play_button = QPushButton("Play")
        self.stop_button = QPushButton("Stop")
        self.record_button = QPushButton("Record")

        grid_label = QLabel("Grid:")
        self.snap_checkbox = QCheckBox("Snap to Grid")
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.toggled.connect(self.on_global_snap_toggled)

        transport_layout.addWidget(self.play_button)
        transport_layout.addWidget(self.stop_button)
        transport_layout.addWidget(self.record_button)
        transport_layout.addWidget(grid_label)
        transport_layout.addWidget(self.snap_checkbox)
        transport_layout.addStretch()

        # BPM control
        bpm_label = QLabel("BPM:")
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(60, 200)
        self.bpm_spinbox.setValue(120)

        # Connect BPM changes
        self.bpm_spinbox.valueChanged.connect(self.on_bpm_changed)

        transport_layout.addWidget(bpm_label)
        transport_layout.addWidget(self.bpm_spinbox)

        main_layout.addLayout(transport_layout)

        # Lane controls
        lane_controls_layout = QHBoxLayout()

        self.add_audio_lane_button = QPushButton("Add Audio Lane")
        self.add_midi_lane_button = QPushButton("Add MIDI Lane")

        self.add_audio_lane_button.clicked.connect(self.add_audio_lane)
        self.add_midi_lane_button.clicked.connect(self.add_midi_lane)

        lane_controls_layout.addWidget(self.add_audio_lane_button)
        lane_controls_layout.addWidget(self.add_midi_lane_button)
        lane_controls_layout.addStretch()

        main_layout.addLayout(lane_controls_layout)

        # Lanes area
        self.lanes_scroll = QScrollArea()
        self.lanes_widget = QWidget()
        self.lanes_layout = QVBoxLayout(self.lanes_widget)

        self.lanes_scroll.setWidget(self.lanes_widget)
        self.lanes_scroll.setWidgetResizable(True)

        main_layout.addWidget(self.lanes_scroll)

    def setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)

        load_action = QAction("Load", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_project)

        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(load_action)

    def add_audio_lane(self):
        lane = self.project.add_lane("audio")
        lane_widget = LaneWidget(lane, self)
        lane_widget.remove_requested.connect(self.remove_lane)

        self.lane_widgets.append(lane_widget)
        self.lanes_layout.addWidget(lane_widget)

    def add_midi_lane(self):
        lane = self.project.add_lane("midi")
        lane_widget = LaneWidget(lane, self)
        lane_widget.remove_requested.connect(self.remove_lane)

        self.lane_widgets.append(lane_widget)
        self.lanes_layout.addWidget(lane_widget)

    def remove_lane(self, lane_widget):
        self.project.remove_lane(lane_widget.lane)
        self.lane_widgets.remove(lane_widget)
        self.lanes_layout.removeWidget(lane_widget)
        lane_widget.deleteLater()

    def save_project(self):
        if hasattr(self, 'current_file_path'):
            self.file_manager.save_project(self.project, self.current_file_path)
        else:
            self.save_project_as()

    def save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "JSON Files (*.json)")

        if file_path:
            self.file_manager.save_project(self.project, file_path)
            self.current_file_path = file_path

    def load_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "JSON Files (*.json)")

        if file_path:
            try:
                self.project = self.file_manager.load_project(file_path)
                self.current_file_path = file_path
                self.refresh_ui()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load project: {str(e)}")

    def refresh_ui(self):
        # Clear existing lane widgets
        for widget in self.lane_widgets:
            self.lanes_layout.removeWidget(widget)
            widget.deleteLater()
        self.lane_widgets.clear()

        # Recreate lane widgets
        for lane in self.project.lanes:
            lane_widget = LaneWidget(lane, self)
            lane_widget.remove_requested.connect(self.remove_lane)
            self.lane_widgets.append(lane_widget)
            self.lanes_layout.addWidget(lane_widget)

        # Update BPM
        self.bpm_spinbox.setValue(int(self.project.bpm))

    def on_bpm_changed(self, bpm):
        """Update BPM across all lanes"""
        self.project.bpm = float(bpm)
        for lane_widget in self.lane_widgets:
            lane_widget.update_bpm(bpm)

    def on_global_snap_toggled(self, checked):
        """Toggle snap to grid globally"""
        for lane_widget in self.lane_widgets:
            if hasattr(lane_widget, 'snap_checkbox'):
                lane_widget.snap_checkbox.setChecked(checked)
