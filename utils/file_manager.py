import json
from typing import Optional
from core.project import Project


class FileManager:
    def save_project(self, project: Project, file_path: str):
        """Save project to JSON file"""
        try:
            with open(file_path, 'w') as f:
                json.dump(project.to_dict(), f, indent=2)
        except Exception as e:
            raise Exception(f"Failed to save project: {str(e)}")

    def load_project(self, file_path: str) -> Project:
        """Load project from JSON file"""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            project = Project()
            project.from_dict(data)
            return project
        except Exception as e:
            raise Exception(f"Failed to load project: {str(e)}")

    def load_song_structure(self, file_path: str):
        """Load song structure from file (to be implemented)"""
        pass
