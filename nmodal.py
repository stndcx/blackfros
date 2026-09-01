"""
BACKFROS - nickname modal
v3.0.0-pre.1
"""

from textual.screen import ModalScreen
from textual.containers import Center, Middle, Vertical
from textual.widgets import Label, Input, Button

import theme

CSS = f"""
NicknameModal {{
    align: center middle;
    background: {theme.BG} 80%;
}}

#nickname-box {{
    width: 44;
    height: auto;
    border: round {theme.SELECT};
    background: {theme.BG};
    padding: 1 2;
}}

#nickname-title {{
    color: {theme.SELECT};
    text-style: bold;
    padding-bottom: 1;
}}

#nickname-input {{
    margin-bottom: 1;
}}

#nickname-error {{
    color: {theme.RED};
    height: 1;
}}
"""


class NicknameModal(ModalScreen[str]):

    CSS = CSS

    def compose(self):
        with Center():
            with Middle():
                with Vertical(id="nickname-box"):
                    yield Label("Choose your nickname", id="nickname-title")
                    yield Input(placeholder="anon", id="nickname-input")
                    yield Label("", id="nickname-error")
                    yield Button("Connect", id="nickname-submit", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#nickname-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._try_submit(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "nickname-submit":
            self._try_submit(self.query_one("#nickname-input", Input).value)

    def _try_submit(self, value: str) -> None:
        nickname = value.strip()
        if not nickname:
            self.query_one("#nickname-error", Label).update("Nickname can't be empty")
            return
        self.dismiss(nickname)