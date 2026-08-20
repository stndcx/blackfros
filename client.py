#!/usr/bin/env python3

import asyncio
import json
import socket
import sys
import threading
import pyfiglet

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea

DEFAULT_PORT = 5050

BG = "#15141f"
ACCENT = "#7c6fee"
ACCENT_DIM = "#59519e"
DIM = "#6b7280"
TEXT = "#d6d3f0"
GREEN = "#4ade80"
RED = "#f87171"
MAGENTA = "#c084fc"

VIOLETA = "\033[38;5;135m"
RESET = "\033[0m"

def print_banner(texto="BACKFROS", font="standard"):
    arte = pyfiglet.figlet_format(texto, font=font)
    print(VIOLETA + arte + RESET)

STYLE = Style.from_dict({
    "": f"bg:{BG} {TEXT}",
    "output": f"bg:{BG} {TEXT}",
    "separator": f"bg:{BG} {ACCENT_DIM}",
    "input": f"bg:{BG} {TEXT}",
    "input.prompt": f"bg:{BG} {ACCENT} bold",
    "statusbar": f"bg:{BG} {DIM}",
    "statusbar.accent": f"bg:{BG} {ACCENT}",
    "line.ok": f"bg:{BG} {GREEN}",
    "line.error": f"bg:{BG} {RED}",
    "line.chat": f"bg:{BG} {MAGENTA}",
    "line.event": f"bg:{BG} {ACCENT}",
    "line.dim": f"bg:{BG} {DIM}",
})


class Client:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.nickname = None
        self.sock = None
        self.loop = None
        self.history = []

        self.output_control = FormattedTextControl(
            text=self._render_output,
            focusable=False,
        )
        self.output_window = Window(
            content=self.output_control,
            wrap_lines=True,
            style="class:output",
            get_vertical_scroll=lambda w: 10 ** 9,
            always_hide_cursor=True,
        )

        self.input_field = TextArea(
            height=1,
            prompt="> ",
            multiline=False,
            wrap_lines=False,
            style="class:input",
            accept_handler=self._on_submit,
        )

        self.status_left = Window(
            FormattedTextControl(self._status_left_text),
            style="class:statusbar",
        )
        self.status_right = Window(
            FormattedTextControl(lambda: "Ctrl+Q quit "),
            style="class:statusbar",
            align=WindowAlign.RIGHT,
        )

        root = HSplit([
            self.output_window,
            Window(height=1, char="─", style="class:separator"),
            self.input_field,
            VSplit([self.status_left, self.status_right]),
        ])

        kb = KeyBindings()

        @kb.add("c-q")
        def _(event):
            event.app.exit()

        @kb.add("c-c")
        def _(event):
            event.app.exit()

        self.app = Application(
            layout=Layout(root, focused_element=self.input_field),
            key_bindings=kb,
            style=STYLE,
            full_screen=True,
            mouse_support=False,
        )


    def _status_left_text(self):
        nick = self.nickname or "..."
        return f" {self.ip}:{self.port} · {nick}"

    def _render_output(self):
        fragments = []
        for style_class, texto in self.history:
            if fragments:
                fragments.append(("", "\n"))
            fragments.append((style_class, texto))
        return fragments

    def append(self, texto, style_class="class:line.dim"):
        self.history.append((style_class, texto))
        self.app.invalidate()


    def _on_submit(self, buff):
        texto = buff.text.strip()
        if texto:
            self.append(f"> {texto}", "class:line.event")
            try:
                self.sock.sendall((texto + "\n").encode("utf-8"))
            except OSError:
                self.append("ERROR se perdió la conexión con el servidor", "class:line.error")
            if texto.upper() == "QUIT":
                self.app.exit()
        buff.reset()
        return False


    def _classify(self, linea):
        if linea.startswith("OK"):
            return "class:line.ok"
        if linea.startswith("ERROR"):
            return "class:line.error"
        if linea.startswith("CHAT ") or linea.startswith("DM "):
            return "class:line.chat"
        if linea.startswith("*"):
            return "class:line.event"
        return "class:line.dim"

    def _pretty(self, linea):
        if linea.startswith("SHOPS "):
            try:
                data = json.loads(linea[len("SHOPS "):])
                if not data:
                    return "(no shops)"
                filas = [f"  {s['hash']}  user: {s['owner']:<15} products: {s['products']}" for s in data]
                return "Online Stores\n" + "\n".join(filas)
            except (json.JSONDecodeError, KeyError):
                return linea

        if linea.startswith("SHOP "):
            try:
                _, hash_id, owner, wallet, avg, count, json_data = linea.split(maxsplit=6)
                productos = json.loads(json_data)
                titulo = f"{owner}'s shop [{hash_id}]  ({count} reviews)"
                if not productos:
                    return titulo + "\n  (sin productos)"
                filas = [
                    f"  [{p['id']}] {p['name']:<20} ${p['price']:<10} stock:{p['stock']}"
                    for p in productos
                ]
                return titulo + "\n" + "\n".join(filas)
            except (ValueError, json.JSONDecodeError):
                return linea

        return linea

    def _net_loop(self):
        buf = self.sock.makefile("r", encoding="utf-8")
        try:
            for linea in buf:
                linea = linea.rstrip("\n")
                if not linea:
                    continue
                texto = self._pretty(linea)
                estilo = self._classify(linea)
                if self.loop:
                    self.loop.call_soon_threadsafe(self.append, texto, estilo)
        except OSError:
            pass
        finally:
            if self.loop:
                self.loop.call_soon_threadsafe(
                    self.append, "* se cerró la conexión", "class:line.error"
                )


    async def run(self):
        self.loop = asyncio.get_running_loop()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.ip, self.port))

        threading.Thread(target=self._net_loop, daemon=True).start()

        print_banner("BACKFROS")

        nickname = input(f"Elegí tu nickname para conectarte a {self.ip}:{self.port}: ").strip()
        self.nickname = nickname or "anon"
        self.sock.sendall((self.nickname + "\n").encode("utf-8"))

        await self.app.run_async()

        try:
            self.sock.close()
        except OSError:
            pass


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 client.py <ip_servidor> [puerto]")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT

    client = Client(ip, port)
    try:
        asyncio.run(client.run())
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == "__main__":
    main()