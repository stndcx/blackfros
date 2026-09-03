"""
BLACKFROS - confirm modal
v3.0.0-pre.2
"""

from textual.screen import ModalScreen
from textual.containers import Center, Middle, Vertical, Horizontal
from textual.widgets import Label, Button

import theme

CSS = f"""
ConfirmModal {{
    align: center middle;
    background: {theme.BG} 80%;
}}

#confirm-box {{
    width: 50;
    height: auto;
    border: round {theme.RED};
    background: {theme.BG};
    padding: 1 2;
}}

#confirm-title {{
    color: {theme.RED};
    text-style: bold;
    padding-bottom: 1;
}}

#confirm-message {{
    padding-bottom: 1;
}}

#confirm-buttons {{
    height: auto;
    align: right middle;
}}

#confirm-buttons Button {{
    margin-left: 1;
}}
"""


class ConfirmModal(ModalScreen[bool]):

    CSS = CSS

    def __init__(self, title: str, message: str, confirm_label: str = "Confirm"):
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label

    def compose(self):
        with Center():
            with Middle():
                with Vertical(id="confirm-box"):
                    yield Label(self._title, id="confirm-title")
                    yield Label(self._message, id="confirm-message")
                    with Horizontal(id="confirm-buttons"):
                        yield Button("Cancel", id="confirm-cancel")
                        yield Button(self._confirm_label, id="confirm-yes", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(False)