from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QWidget, QPushButton, QScrollArea, QMenuBar,
                             QFileDialog, QMessageBox, QLabel, QSpinBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from core.project import Project
from core.lane import AudioLane, MidiLane
from core.playback_engine import PlaybackEngine
from .lane_widget import LaneWidget
from .master_timeline_widget import MasterTimelineContainer
from utils.file_manager import FileManager
from styles import theme_manager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.project = Project()
        self.file_manager = FileManager()
        self.lane_widgets = []

        # Initialize playback engine
        self.playback_engine = PlaybackEngine()

        self.playback_engine.position_changed.connect(self.on_playhead_position_changed)
        self.playback_engine.playback_started.connect(self.on_playback_started)
        self.playback_engine.playback_halted.connect(self.on_playback_halted)
        self.playback_engine.playback_stopped.connect(self.on_playback_stopped)

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

        self.play_button = QPushButton("▶")  # Play triangle
        self.halt_button = QPushButton("❚❚")  # Halt symbol (pause bars)
        self.stop_button = QPushButton("⏹")  # Stop symbol (move to start)

        # Apply transport button styles
        self.play_button.setStyleSheet(theme_manager.get_transport_button_style("play"))
        self.halt_button.setStyleSheet(theme_manager.get_transport_button_style("stop"))
        self.stop_button.setStyleSheet(theme_manager.get_transport_button_style("halt"))

        # Connect transport buttons
        self.play_button.clicked.connect(self.on_play_clicked)
        self.halt_button.clicked.connect(self.on_halt_clicked)
        self.stop_button.clicked.connect(self.on_stop_clicked)

        grid_label = QLabel("Grid:")
        self.snap_checkbox = QCheckBox("Snap to Grid")
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.toggled.connect(self.on_global_snap_toggled)

        transport_layout.addWidget(self.play_button)
        transport_layout.addWidget(self.halt_button)
        transport_layout.addWidget(self.stop_button)
        transport_layout.addWidget(grid_label)
        transport_layout.addWidget(self.snap_checkbox)
        transport_layout.addStretch()

        # BPM control
        bpm_label = QLabel("BPM:")
        self.bpm_spinbox = QSpinBox()
        self.bpm_spinbox.setRange(60, 200)
        self.bpm_spinbox.setValue(120)
        self.bpm_spinbox.setStyleSheet(theme_manager.get_spinbox_style())

        # Connect BPM changes
        self.bpm_spinbox.valueChanged.connect(self.on_bpm_changed)

        transport_layout.addWidget(bpm_label)
        transport_layout.addWidget(self.bpm_spinbox)

        main_layout.addLayout(transport_layout)

        # Lane controls
        lane_controls_layout = QHBoxLayout()

        self.add_audio_lane_button = QPushButton("Add Audio Lane")
        self.add_midi_lane_button = QPushButton("Add MIDI Lane")

        # Style the lane control buttons
        self.add_audio_lane_button.setStyleSheet(theme_manager.get_action_button_style())
        self.add_midi_lane_button.setStyleSheet(theme_manager.get_action_button_style())

        self.add_audio_lane_button.clicked.connect(self.add_audio_lane)
        self.add_midi_lane_button.clicked.connect(self.add_midi_lane)

        lane_controls_layout.addWidget(self.add_audio_lane_button)
        lane_controls_layout.addWidget(self.add_midi_lane_button)
        lane_controls_layout.addStretch()

        main_layout.addLayout(lane_controls_layout)

        # Master Timeline
        self.master_timeline = MasterTimelineContainer()
        self.master_timeline.playhead_moved.connect(self.on_playhead_moved_by_user)

        self.master_timeline.scroll_position_changed.connect(self.sync_all_timelines_scroll)
        self.master_timeline.zoom_changed.connect(self.sync_all_timelines_zoom)  # New connection
        main_layout.addWidget(self.master_timeline)

        # Lanes area - FIXED FOR PROPER TOP ALIGNMENT
        self.lanes_scroll = QScrollArea()
        self.lanes_widget = QWidget()
        self.lanes_layout = QVBoxLayout(self.lanes_widget)

        # IMPORTANT: Set alignment to top and configure layout
        self.lanes_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.lanes_layout.setSpacing(5)  # Add spacing between lanes
        self.lanes_layout.setContentsMargins(5, 5, 5, 5)  # Add margins

        # Add a stretch at the bottom to push all lanes to the top
        self.lanes_layout.addStretch()

        self.lanes_scroll.setWidget(self.lanes_widget)
        self.lanes_scroll.setWidgetResizable(True)
        self.lanes_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.lanes_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Apply styling to the lanes container
        self.lanes_scroll.setStyleSheet(theme_manager.get_lanes_container_style())

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

        # Add song structure loading
        load_structure_action = QAction("Load Song Structure...", self)
        load_structure_action.setShortcut("Ctrl+Shift+O")
        load_structure_action.triggered.connect(self.load_song_structure)

        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(load_action)
        file_menu.addAction(load_structure_action)

    def load_song_structure(self):
        """Load song structure from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Song Structure", "", "CSV Files (*.csv)")

        if file_path:
            try:
                from core.song_structure import SongStructure
                song_structure = SongStructure()

                if song_structure.load_from_csv(file_path):
                    self.project.song_structure = song_structure

                    # Update master timeline with song structure
                    self.master_timeline.timeline_widget.set_song_structure(song_structure)

                    # Update ALL lane timelines with song structure
                    for lane_widget in self.lane_widgets:
                        lane_widget.set_song_structure(song_structure)

                    # Update playback engine
                    self.playback_engine.set_song_structure(song_structure)

                    QMessageBox.information(self, "Success",
                                            f"Loaded song structure with {len(song_structure.parts)} parts")
                else:
                    QMessageBox.critical(self, "Error", "Failed to load song structure")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load song structure: {str(e)}")

    def add_audio_lane(self):
        lane = self.project.add_lane("audio")
        lane_widget = LaneWidget(lane, self)
        lane_widget.remove_requested.connect(self.remove_lane)
        lane_widget.scroll_position_changed.connect(self.sync_master_timeline_scroll)
        lane_widget.zoom_changed.connect(self.sync_master_timeline_zoom)

        # Pass song structure if it exists
        if hasattr(self.project, 'song_structure') and self.project.song_structure:
            lane_widget.set_song_structure(self.project.song_structure)

        self.lane_widgets.append(lane_widget)
        insert_index = self.lanes_layout.count() - 1
        self.lanes_layout.insertWidget(insert_index, lane_widget)

        # Update playback engine with new lanes
        self.playback_engine.set_lanes(self.project.lanes)

    def add_midi_lane(self):
        lane = self.project.add_lane("midi")
        lane_widget = LaneWidget(lane, self)
        lane_widget.remove_requested.connect(self.remove_lane)
        lane_widget.scroll_position_changed.connect(self.sync_master_timeline_scroll)
        lane_widget.zoom_changed.connect(self.sync_master_timeline_zoom)

        # Pass song structure if it exists
        if hasattr(self.project, 'song_structure') and self.project.song_structure:
            lane_widget.set_song_structure(self.project.song_structure)

        self.lane_widgets.append(lane_widget)

        insert_index = self.lanes_layout.count() - 1
        self.lanes_layout.insertWidget(insert_index, lane_widget)

        # Update playback engine with new lanes
        self.playback_engine.set_lanes(self.project.lanes)

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

        # Remove the stretch item temporarily if it exists
        if self.lanes_layout.count() > 0:
            stretch_item = self.lanes_layout.takeAt(self.lanes_layout.count() - 1)

        # Recreate lane widgets
        for lane in self.project.lanes:
            lane_widget = LaneWidget(lane, self)
            lane_widget.remove_requested.connect(self.remove_lane)
            # Pass song structure if it exists
            if hasattr(self.project, 'song_structure') and self.project.song_structure:
                lane_widget.set_song_structure(self.project.song_structure)

            self.lane_widgets.append(lane_widget)
            self.lanes_layout.addWidget(lane_widget)

        # Re-add the stretch item at the end
        self.lanes_layout.addStretch()

        # Update BPM
        self.bpm_spinbox.setValue(int(self.project.bpm))

    # Transport control methods
    def on_play_clicked(self):
        """Handle play button click"""
        self.playback_engine.play()

    def on_halt_clicked(self):
        """Handle halt button click"""
        self.playback_engine.halt()

    def on_stop_clicked(self):
        """Handle stop button click"""
        self.playback_engine.stop()

    def sync_all_timelines_scroll(self, position: int):
        """Synchronize scroll position across all lane timelines"""
        for lane_widget in self.lane_widgets:
            lane_widget.sync_scroll_position(position)

    def sync_all_timelines_zoom(self, zoom_factor: float):
        """Synchronize zoom level across all lane timelines"""
        for lane_widget in self.lane_widgets:
            lane_widget.set_zoom_factor(zoom_factor)

    def sync_master_timeline_scroll(self, position: int):
        """Sync master timeline scroll when lane timeline is scrolled"""
        self.master_timeline.sync_scroll_position(position)

        # Sync all other lane timelines
        sender = self.sender()
        for lane_widget in self.lane_widgets:
            if lane_widget != sender:
                lane_widget.sync_scroll_position(position)

    def sync_master_timeline_zoom(self, zoom_factor: float):
        """Sync master timeline zoom when lane timeline is zoomed"""
        self.master_timeline.set_zoom_factor(zoom_factor)

        # Sync all other lane timelines
        sender = self.sender()
        for lane_widget in self.lane_widgets:
            if lane_widget != sender:
                lane_widget.set_zoom_factor(zoom_factor)

    def on_playhead_position_changed(self, position: float):
        """Update playhead position and BPM across all timelines"""
        self.master_timeline.set_playhead_position(position)

        # Update BPM based on song structure
        if hasattr(self.project, 'song_structure') and self.project.song_structure:
            current_bpm = self.project.song_structure.get_bpm_at_time(position)
            self.bpm_spinbox.setValue(int(current_bpm))

        # Update playhead in all lane timelines
        for lane_widget in self.lane_widgets:
            lane_widget.set_playhead_position(position)

    def on_playhead_moved_by_user(self, position: float):
        """Handle user dragging the playhead"""
        self.playback_engine.set_position(position)

    def on_playback_started(self):
        """Handle playback started"""
        self.play_button.setText("⏸")  # Change to pause symbol

    def on_playback_halted(self):
        """Handle playback halted"""
        self.play_button.setText("▶")  # Change back to play symbol

    def on_playback_stopped(self):
        """Handle playback stopped"""
        self.play_button.setText("▶")  # Change back to play symbol

    def on_bpm_changed(self, bpm):
        """Update BPM across all components"""
        self.project.bpm = float(bpm)
        self.playback_engine.set_bpm(bpm)
        self.master_timeline.set_bpm(bpm)
        for lane_widget in self.lane_widgets:
            lane_widget.update_bpm(bpm)

    def on_global_snap_toggled(self, checked):
        """Toggle snap to grid globally"""
        self.playback_engine.set_snap_to_grid(checked)
        self.master_timeline.set_snap_to_grid(checked)
        for lane_widget in self.lane_widgets:
            if hasattr(lane_widget, 'snap_checkbox'):
                lane_widget.snap_checkbox.setChecked(checked)
