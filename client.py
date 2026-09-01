#!/usr/bin/env python3
"""
BACKFROS - client
v3.0.0-pre.1
"""

import argparse
import json

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, ListView, ListItem, Label, Input, Log
from textual.binding import Binding
from textual import work

import theme
from network import Connection, classify, DEFAULT_PORT, DEFAULT_TOR_PROXY_HOST, DEFAULT_TOR_PROXY_PORT
from nmodal import NicknameModal


class BackfrosClient(App):

    CSS = theme.CSS
    TITLE = "BACKFROS"
    SUB_TITLE = "peer shop network"

    BINDINGS = [
        Binding("q", "quit_app", "Quit"),
        Binding("ctrl+q", "quit_app", "Quit"),
        Binding("r", "refresh_shops", "Refresh shops"),
        Binding("/", "focus_input", "Command"),
    ]

    def __init__(self, ip, port, use_tor=False, proxy_host=DEFAULT_TOR_PROXY_HOST, proxy_port=DEFAULT_TOR_PROXY_PORT):
        super().__init__()
        self.conn = Connection(ip, port, use_tor, proxy_host, proxy_port)
        self.nickname = None
        self.shops = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="shops-panel"):
                yield Label(" Shops", classes="dim")
                yield ListView(id="shops-list")
            with Vertical(id="detail-panel"):
                yield Log(id="log-view", auto_scroll=True, highlight=False)
        yield Input(placeholder="Type a command (HELP for list)...", id="input-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#detail-panel").border_title = "Activity"
        self.query_one("#shops-panel").border_title = "Shops"
        self.push_screen(NicknameModal(), self._on_nickname_chosen)

    def _on_nickname_chosen(self, nickname: str) -> None:
        self.nickname = nickname
        self.sub_title = f"peer shop network · {nickname}"
        self.connect_and_listen()

    # --- Networking ---

    @work(thread=True)
    def connect_and_listen(self) -> None:
        self.conn.connect(self.nickname)
        self.conn.send("SHOPS")
        for line in self.conn.lines():
            self.call_from_thread(self.handle_line, line)
        self.call_from_thread(self.log_line, "* connection closed", "error")

    def send_command(self, text: str) -> None:
        try:
            self.conn.send(text)
        except OSError:
            self.log_line("ERROR lost connection to server", "error")

    # --- UI updates ---

    def handle_line(self, line: str) -> None:
        if line.startswith("SHOPS "):
            try:
                self.shops = json.loads(line[len("SHOPS "):])
                self.refresh_shop_list()
                return
            except json.JSONDecodeError:
                pass
        elif line.startswith("SHOP "):
            pretty = self._pretty_shop(line)
            if pretty is not None:
                self.log_line(pretty, "event")
                return
        self.log_line(line, classify(line))

    def _pretty_shop(self, line: str):
        parts = line.split(maxsplit=6)
        if len(parts) < 7:
            return None
        _, hash_id, owner, wallet, avg, count, raw_products = parts
        try:
            products = json.loads(raw_products)
        except json.JSONDecodeError:
            return None

        header = f"{owner}'s shop [{hash_id}]  rating {avg}/5 ({count} reviews)  wallet: {wallet}"
        if not products:
            return header + "\n  (no products)"
        rows = [
            f"  [{p['id']}] {p['name']:<20} ${p['price']:<10} stock:{p['stock']}"
            for p in products
        ]
        return header + "\n" + "\n".join(rows)

    def log_line(self, text: str, style: str = "dim") -> None:
        self.query_one("#log-view", Log).write_line(text)

    def refresh_shop_list(self) -> None:
        list_view = self.query_one("#shops-list", ListView)
        list_view.clear()
        for shop in self.shops:
            label = f"{shop.get('owner', '?'):<15} {shop.get('products', 0)} items"
            list_view.append(ListItem(Label(label)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "shops-list":
            return
        index = event.list_view.index
        if index is None or index >= len(self.shops):
            return
        shop = self.shops[index]
        hash_id = shop.get("hash")
        if hash_id:
            self.send_command(f"VIEW {hash_id}")

    # --- Actions ---

    def action_refresh_shops(self) -> None:
        self.send_command("SHOPS")

    def action_focus_input(self) -> None:
        self.query_one("#input-bar", Input).focus()

    def action_quit_app(self) -> None:
        self.send_command("QUIT")
        self.conn.close()
        self.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        event.input.value = ""
        if text:
            self.log_line(f"> {text}", "event")
            self.send_command(text)


def main():
    parser = argparse.ArgumentParser(description="Client BACKFROS")
    parser.add_argument("ip", help="Server IP, or address .onion --tor")
    parser.add_argument("port", nargs="?", type=int, default=DEFAULT_PORT)
    parser.add_argument("--tor", action="store_true")
    parser.add_argument("--proxy-host", default=DEFAULT_TOR_PROXY_HOST)
    parser.add_argument("--proxy-port", type=int, default=DEFAULT_TOR_PROXY_PORT)
    args = parser.parse_args()

    app = BackfrosClient(args.ip, args.port, use_tor=args.tor, proxy_host=args.proxy_host, proxy_port=args.proxy_port)
    app.run()


if __name__ == "__main__":
    main()