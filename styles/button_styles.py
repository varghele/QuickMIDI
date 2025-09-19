"""
Button style definitions for the MIDI Track Creator application.
All button styles are centralized here for easy maintenance and theming.
"""


class ButtonStyles:
    """Centralized button style definitions"""

    # Base button styles
    BASE_BUTTON = """
        QPushButton {
            background-color: #f5f5f5;
            color: #333;
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
    """

    # Mute button styles
    MUTE_BUTTON_ACTIVE = """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: 2px solid #d32f2f;
            border-radius: 4px;
            padding: 4px 8px;
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #e53935;
        }
        QPushButton:pressed {
            background-color: #c62828;
        }
    """

    MUTE_BUTTON_INACTIVE = BASE_BUTTON

    # Solo button styles
    SOLO_BUTTON_ACTIVE = """
        QPushButton {
            background-color: #ffeb3b;
            color: #333;
            border: 2px solid #fbc02d;
            border-radius: 4px;
            padding: 4px 8px;
            font-weight: bold;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #fff176;
        }
        QPushButton:pressed {
            background-color: #ffee58;
        }
    """

    SOLO_BUTTON_INACTIVE = BASE_BUTTON

    # Action button styles (Add Block, Load Audio, etc.)
    ACTION_BUTTON = """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: 1px solid #1976D2;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #1565C0;
        }
    """

    # Remove button styles
    REMOVE_BUTTON = """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #da190b;
        }
        QPushButton:pressed {
            background-color: #b71c1c;
        }
    """

    # Transport button styles
    TRANSPORT_BUTTON = """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: 1px solid #45a049;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """

    TRANSPORT_BUTTON_PLAY = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: 1px solid #45a049;
            border-radius: 6px;
            padding: 8px;
            font-size: 18px;
            font-weight: bold;
            min-width: 45px;
            min-height: 35px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
    """

    TRANSPORT_BUTTON_STOP = """
        QPushButton {
            background-color: #FF5722;
            color: white;
            border: 1px solid #E64A19;
            border-radius: 6px;
            padding: 8px;
            font-size: 18px;
            font-weight: bold;
            min-width: 45px;
            min-height: 35px;
        }
        QPushButton:hover {
            background-color: #E64A19;
        }
        QPushButton:pressed {
            background-color: #D84315;
        }
    """

    TRANSPORT_BUTTON_HALT = """
        QPushButton {
            background-color: #9E9E9E;
            color: white;
            border: 1px solid #757575;
            border-radius: 6px;
            padding: 8px;
            font-size: 18px;
            font-weight: bold;
            min-width: 45px;
            min-height: 35px;
        }
        QPushButton:hover {
            background-color: #757575;
        }
        QPushButton:pressed {
            background-color: #616161;
        }
    """

    # Compact Mute button styles (for smaller buttons)
    MUTE_BUTTON_COMPACT_ACTIVE = """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: 2px solid #d32f2f;
            border-radius: 3px;
            padding: 2px;
            font-weight: bold;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #e53935;
        }
        QPushButton:pressed {
            background-color: #c62828;
        }
    """

    MUTE_BUTTON_COMPACT_INACTIVE = """
        QPushButton {
            background-color: #f5f5f5;
            color: #333;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 2px;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QPushButton:pressed {
            background-color: #d0d0d0;
        }
    """

    # Compact Solo button styles
    SOLO_BUTTON_COMPACT_ACTIVE = """
        QPushButton {
            background-color: #ffeb3b;
            color: #333;
            border: 2px solid #fbc02d;
            border-radius: 3px;
            padding: 2px;
            font-weight: bold;
            font-size: 11px;
        }
        QPushButton:hover {
            background-color: #fff176;
        }
        QPushButton:pressed {
            background-color: #ffee58;
        }
    """

    SOLO_BUTTON_COMPACT_INACTIVE = MUTE_BUTTON_COMPACT_INACTIVE
