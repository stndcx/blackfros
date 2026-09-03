#!/usr/bin/env python3
"""
BLACKFROS - shop server.
v3.0.0-pre.2
"""

import socket
import threading
import sys
import json
import os
import hashlib
import re
import base64

HOST = os.environ.get("BACKFROS_HOST", "127.0.0.1")
DEFAULT_PORT = 5050
SESSION_TIMEOUT = 3600

MAX_NICKNAME_LEN = 24
MAX_PRODUCT_NAME_LEN = 40
MAX_LINE_LEN = 512
NICKNAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]+$")

MAX_TOTAL_CONNECTIONS = 200
MAX_CONNECTIONS_PER_IP = 5
MAX_COMMANDS_PER_SECOND = 10

MAX_IMAGE_B64_LEN = 400_000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SHOPS_DIR = os.path.join(BASE_DIR, "shops")
os.makedirs(SHOPS_DIR, exist_ok=True)


def valid_nickname(nickname):

    return bool(nickname) and len(nickname) <= MAX_NICKNAME_LEN and NICKNAME_RE.match(nickname)


def clean_product_name(name):

    name = name.replace("|", "").strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return name[:MAX_PRODUCT_NAME_LEN]


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"


BANNER = (
    Color.GREEN + Color.BOLD +
    "┌" + "─" * 58 + "┐\n" +
    "│{:^58}│\n".format("BACKFROS") +
    "│{:^58}│\n".format("distributed peer shop server") +
    "└" + "─" * 58 + "┘" +
    Color.RESET
)

nodes = {}
lock = threading.RLock()

active_total = 0
active_by_ip = {}


def shop_hash(nickname):
    return hashlib.sha256(nickname.strip().lower().encode("utf-8")).hexdigest()[:10]


def shop_path(hash_id):
    return os.path.join(SHOPS_DIR, f"{hash_id}.md")


def shop_exists(hash_id):
    return os.path.isfile(shop_path(hash_id))


def create_default_shop(nickname, hash_id):
    products = [
        {"id": 1, "name": "Sample product", "price": 1000, "stock": 5},
    ]
    save_shop(nickname, hash_id, products)


def load_shop(hash_id):
    path = shop_path(hash_id)
    if not os.path.isfile(path):
        return None, []

    owner = None
    products = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            m = re.match(r"^#\s*Shop of\s+(.+)$", line.strip(), re.IGNORECASE)
            if m:
                owner = m.group(1).strip()
                continue

            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 4:
                    continue
                if cells[0].lower() == "id" or set(cells[0]) <= {"-", " "}:
                    continue
                try:
                    products.append({
                        "id": int(cells[0]),
                        "name": cells[1],
                        "price": float(cells[2]),
                        "stock": int(cells[3]),
                    })
                except ValueError:
                    continue

    return owner, products


def save_shop(nickname, hash_id, products):
    path = shop_path(hash_id)
    lines = [
        f"# Shop of {nickname}",
        f"hash: {hash_id}",
        "",
        "| id | name | price | stock |",
        "|----|------|-------|-------|",
    ]
    for p in products:
        lines.append(f"| {p['id']} | {p['name']} | {p['price']} | {p['stock']} |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def log_transaction(hash_id, text):
    from datetime import datetime
    path = os.path.join(SHOPS_DIR, f"{hash_id}.log")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {text}\n")


def list_shops():
    result = []
    for file_name in sorted(os.listdir(SHOPS_DIR)):
        if not file_name.endswith(".md"):
            continue
        hash_id = file_name[:-3]
        owner, products = load_shop(hash_id)
        result.append((hash_id, owner or "?", len(products)))
    return result


def ensure_shop(nickname):
    hash_id = shop_hash(nickname)
    with lock:
        if not shop_exists(hash_id):
            create_default_shop(nickname, hash_id)
    return hash_id


def rating_path(hash_id):
    return os.path.join(SHOPS_DIR, f"{hash_id}.rating")


def add_rating(hash_id, score):
    with open(rating_path(hash_id), "a", encoding="utf-8") as f:
        f.write(f"{score}\n")


def get_rating(hash_id):
    path = rating_path(hash_id)
    if not os.path.isfile(path):
        return 0.0, 0
    with open(path, encoding="utf-8") as f:
        scores = [int(l.strip()) for l in f if l.strip().isdigit()]
    if not scores:
        return 0.0, 0
    return sum(scores) / len(scores), len(scores)


def wallet_path(hash_id):
    return os.path.join(SHOPS_DIR, f"{hash_id}.wallet")


def log_path(hash_id):
    return os.path.join(SHOPS_DIR, f"{hash_id}.log")


def image_path(hash_id, product_id):
    return os.path.join(SHOPS_DIR, f"{hash_id}_{product_id}.img")


def save_product_image(hash_id, product_id, raw_bytes):
    with open(image_path(hash_id, product_id), "wb") as f:
        f.write(raw_bytes)


def load_product_image(hash_id, product_id):
    path = image_path(hash_id, product_id)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def wipe_shop(hash_id):

    for path in (shop_path(hash_id), rating_path(hash_id),
                 wallet_path(hash_id), log_path(hash_id)):
        try:
            os.remove(path)
        except OSError:
            pass
    for file_name in os.listdir(SHOPS_DIR):
        if file_name.startswith(f"{hash_id}_") and file_name.endswith(".img"):
            try:
                os.remove(os.path.join(SHOPS_DIR, file_name))
            except OSError:
                pass


def set_wallet(hash_id, address):
    with open(wallet_path(hash_id), "w", encoding="utf-8") as f:
        f.write(address.strip())


def get_wallet(hash_id):
    path = wallet_path(hash_id)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip() or None


def send_msg(conn, text):
    try:
        conn.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


def broadcast(text, exclude=None):
    with lock:
        for nick, info in nodes.items():
            if nick != exclude:
                send_msg(info["conn"], text)


def log(text, color=Color.DIM):
    print(f"{color}{text}{Color.RESET}")


def register_connection(ip):

    global active_total
    with lock:
        if active_total >= MAX_TOTAL_CONNECTIONS:
            return False
        if active_by_ip.get(ip, 0) >= MAX_CONNECTIONS_PER_IP:
            return False
        active_total += 1
        active_by_ip[ip] = active_by_ip.get(ip, 0) + 1
        return True


def release_connection(ip):
    global active_total
    with lock:
        active_total = max(0, active_total - 1)
        if ip in active_by_ip:
            active_by_ip[ip] -= 1
            if active_by_ip[ip] <= 0:
                del active_by_ip[ip]


class RateLimiter:

    def __init__(self, limit):
        self.limit = limit
        self.window_start = 0.0
        self.count = 0

    def allow(self):
        import time
        now = time.monotonic()
        if now - self.window_start >= 1.0:
            self.window_start = now
            self.count = 0
        self.count += 1
        return self.count <= self.limit


def handle_client(conn, addr):
    conn.settimeout(SESSION_TIMEOUT)
    nickname = None
    registered = False
    ip = addr[0]

    if not register_connection(ip):
        send_msg(conn, "ERROR server is at capacity, try again later")
        conn.close()
        return

    rate_limiter = RateLimiter(MAX_COMMANDS_PER_SECOND)

    try:
        send_msg(conn, "Welcome to BACKFROS\nby STNDC\nv3.0.0-pre.1\nSend your nickname:")
        buf = conn.makefile("r", encoding="utf-8")
        first_line = buf.readline().strip()

        if not first_line:
            conn.close()
            return

        nickname = first_line

        if not valid_nickname(nickname):
            send_msg(conn, "ERROR invalid nickname (letters/numbers/_-. only, max "
                            f"{MAX_NICKNAME_LEN} chars)")
            conn.close()
            return

        with lock:
            if nickname in nodes:
                send_msg(conn, "ERROR that nickname is already taken.\nReconnect with another one.")
                conn.close()
                return
            nodes[nickname] = {"conn": conn, "addr": addr}
        registered = True

        my_hash = ensure_shop(nickname)

        log(f"[+] Node connected: {nickname} from {addr} (shop {my_hash})", Color.GREEN)
        send_msg(conn, f"OK registered as '{nickname}'\nYour shop: {my_hash}\nType HELP to see the commands")
        broadcast(f"* {nickname} joined the network (shop {my_hash})", exclude=nickname)

        for line in buf:
            line = line.strip()
            if not line:
                continue
            if len(line) > MAX_LINE_LEN:
                is_image_cmd = line[:6].upper() == "SETIMG"
                if not (is_image_cmd and len(line) <= MAX_IMAGE_B64_LEN):
                    send_msg(conn, "ERROR line too long")
                    continue
            if not rate_limiter.allow():
                send_msg(conn, "ERROR too many commands, slow down")
                continue
            parts = line.split()
            cmd = parts[0].upper()

            if cmd == "HELP":
                send_msg(conn,
                    "Commands:\n"
                    "-  SHOPS                            list every shop on the network\n"
                    "-  VIEW <hash>                      view a shop's catalog\n"
                    "-  MYSHOP                           view your own catalog\n"
                    "-  ADD <name> <price> <stock>       add a product to your shop\n"
                    "-  REMOVE <id>                      remove a product from your shop\n"
                    "-  BUY <hash> <id> <qty>            buy from another shop\n"
                    "-  SETIMG <id> <base64>             attach an image to your product\n"
                    "-  GETIMG <hash> <id>                fetch a product's image\n"
                    "-  CHAT <message>                   send a message to everyone\n"
                    "-  MSG <nick> <message>             send a private message\n"
                    "-  WHO                              list connected nodes\n"
                    "-  WIPE                              permanently delete your shop and all its data\n"
                    "-  QUIT                             disconnect")

            elif cmd == "SHOPS":
                with lock:
                    shops = list_shops()
                data = json.dumps(
                    [{"hash": h, "owner": o, "products": n,
                      "rating": round(get_rating(h)[0], 1), "reviews": get_rating(h)[1]}
                     for h, o, n in shops],
                    ensure_ascii=False,
                )
                send_msg(conn, f"SHOPS {data}")

            elif cmd == "MYSHOP":
                with lock:
                    owner, products = load_shop(my_hash)
                    wallet = get_wallet(my_hash)
                    avg, count = get_rating(my_hash)
                data = json.dumps(products, ensure_ascii=False)
                send_msg(conn, f"SHOP {my_hash} {nickname} {wallet or '-'} {round(avg,1)} {count} {data}")

            elif cmd == "SEARCH":
                if len(parts) < 2:
                    send_msg(conn, "ERROR usage: SEARCH <term>")
                    continue
                term = " ".join(parts[1:]).lower()
                matches = []
                with lock:
                    for hash_id, owner, _ in list_shops():
                        _, products = load_shop(hash_id)
                        for p in products:
                            if term in p["name"].lower():
                                matches.append({"shop": hash_id, "owner": owner, **p})
                data = json.dumps(matches, ensure_ascii=False)
                send_msg(conn, f"SEARCH {data}")

            elif cmd == "WALLET":
                if len(parts) < 2:
                    send_msg(conn, "ERROR usage: WALLET <address>")
                    continue
                address = parts[1]
                with lock:
                    set_wallet(my_hash, address)
                send_msg(conn, f"OK wallet set to {address}")

            elif cmd == "VIEW":
                if len(parts) < 2:
                    send_msg(conn, "ERROR usage: VIEW <hash>")
                    continue
                hash_id = parts[1]
                with lock:
                    owner, products = load_shop(hash_id)
                if owner is None:
                    send_msg(conn, "ERROR that shop doesn't exist")
                else:
                    wallet = get_wallet(hash_id)
                    avg, count = get_rating(hash_id)
                    data = json.dumps(products, ensure_ascii=False)
                    send_msg(conn, f"SHOP {hash_id} {owner} {wallet or '-'} {round(avg,1)} {count} {data}")

            elif cmd == "WHO":
                with lock:
                    connected = list(nodes.keys())
                send_msg(conn, f"NODES {', '.join(connected)}")

            elif cmd == "ADD":
                if len(parts) < 4:
                    send_msg(conn, "ERROR usage: ADD <name> <price> <stock>")
                    continue
                try:
                    price = float(parts[-2])
                    stock = int(parts[-1])
                    name = clean_product_name(" ".join(parts[1:-2]))
                    if not name:
                        raise ValueError
                    if price < 0 or stock < 0:
                        raise ValueError
                except ValueError:
                    send_msg(conn, "ERROR invalid price/stock, or missing name")
                    continue

                with lock:
                    _, products = load_shop(my_hash)
                    new_id = (max((p["id"] for p in products), default=0) + 1)
                    products.append({"id": new_id, "name": name, "price": price, "stock": stock})
                    save_shop(nickname, my_hash, products)
                send_msg(conn, f"OK added [{new_id}] {name} (${price}, stock {stock})")

            elif cmd == "REMOVE":
                if len(parts) < 2:
                    send_msg(conn, "ERROR usage: REMOVE <id>")
                    continue
                try:
                    pid = int(parts[1])
                except ValueError:
                    send_msg(conn, "ERROR invalid id")
                    continue

                with lock:
                    _, products = load_shop(my_hash)
                    before = len(products)
                    products = [p for p in products if p["id"] != pid]
                    if len(products) == before:
                        send_msg(conn, "ERROR you don't have a product with that id")
                        continue
                    save_shop(nickname, my_hash, products)
                send_msg(conn, f"OK removed product {pid}")

            elif cmd == "BUY":
                if len(parts) < 3:
                    send_msg(conn, "ERROR usage: BUY <hash> <id> <qty>")
                    continue
                hash_id = parts[1]
                try:
                    pid = int(parts[2])
                    qty = int(parts[3]) if len(parts) > 3 else 1
                except ValueError:
                    send_msg(conn, "ERROR invalid id/quantity")
                    continue

                with lock:
                    owner, products = load_shop(hash_id)
                    if owner is None:
                        send_msg(conn, "ERROR that shop doesn't exist")
                        continue
                    prod = next((p for p in products if p["id"] == pid), None)
                    if not prod:
                        send_msg(conn, "ERROR product not found")
                    elif prod["stock"] < qty:
                        send_msg(conn, f"ERROR not enough stock (only {prod['stock']} left)")
                    else:
                        prod["stock"] -= qty
                        total = prod["price"] * qty
                        save_shop(owner, hash_id, products)
                        log_transaction(hash_id, f"{nickname} bought {qty}x {prod['name']} for ${total}")
                        send_msg(conn, f"OK you bought {qty}x {prod['name']} for ${total} (shop of {owner})")
                        broadcast(f"* {nickname} bought {qty}x {prod['name']} from {owner}'s shop",
                                  exclude=nickname)

            elif cmd == "CHAT":
                if len(parts) < 2:
                    send_msg(conn, "ERROR usage: CHAT <message>")
                    continue
                text = " ".join(parts[1:])
                broadcast(f"CHAT {nickname} {text}")

            elif cmd == "RATE":
                if len(parts) < 3:
                    send_msg(conn, "ERROR usage: RATE <hash> <score 1-5>")
                    continue
                hash_id = parts[1]
                try:
                    score = int(parts[2])
                    if not (1 <= score <= 5):
                        raise ValueError
                except ValueError:
                    send_msg(conn, "ERROR score must be a number from 1 to 5")
                    continue
                with lock:
                    if not shop_exists(hash_id):
                        send_msg(conn, "ERROR that shop doesn't exist")
                        continue
                    add_rating(hash_id, score)
                send_msg(conn, f"OK rated {hash_id} with {score}/5")

            elif cmd == "MSG":
                if len(parts) < 3:
                    send_msg(conn, "ERROR usage: MSG <nick> <message>")
                    continue
                target = parts[1]
                text = " ".join(parts[2:])
                with lock:
                    target_info = nodes.get(target)
                if not target_info:
                    send_msg(conn, f"ERROR {target} is not connected")
                    continue
                send_msg(target_info["conn"], f"DM {nickname} {text}")
                send_msg(conn, f"OK message sent to {target}")

            elif cmd == "SETIMG":
                if len(parts) < 3:
                    send_msg(conn, "ERROR usage: SETIMG <id> <base64 image data>")
                    continue
                try:
                    pid = int(parts[1])
                except ValueError:
                    send_msg(conn, "ERROR invalid id")
                    continue
                with lock:
                    _, products = load_shop(my_hash)
                    if not any(p["id"] == pid for p in products):
                        send_msg(conn, "ERROR you don't have a product with that id")
                        continue
                    try:
                        raw_bytes = base64.b64decode(parts[2], validate=True)
                    except (ValueError, base64.binascii.Error):
                        send_msg(conn, "ERROR invalid base64 image data")
                        continue
                    save_product_image(my_hash, pid, raw_bytes)
                send_msg(conn, f"OK image set for product {pid} ({len(raw_bytes)} bytes)")

            elif cmd == "GETIMG":
                if len(parts) < 3:
                    send_msg(conn, "ERROR usage: GETIMG <hash> <id>")
                    continue
                hash_id = parts[1]
                try:
                    pid = int(parts[2])
                except ValueError:
                    send_msg(conn, "ERROR invalid id")
                    continue
                with lock:
                    raw_bytes = load_product_image(hash_id, pid)
                if raw_bytes is None:
                    send_msg(conn, "ERROR no image for that product")
                else:
                    b64 = base64.b64encode(raw_bytes).decode("ascii")
                    send_msg(conn, f"IMG {hash_id} {pid} {b64}")

            elif cmd == "WIPE":
                with lock:
                    wipe_shop(my_hash)
                send_msg(conn, "OK your shop and all its data have been permanently deleted")
                log(f"[x] Shop wiped: {nickname} ({my_hash})", Color.YELLOW)
                break

            elif cmd == "QUIT":
                send_msg(conn, "OK bye")
                break

            else:
                send_msg(conn, "ERROR unknown command.\nType HELP to see the list.")

    except (ConnectionResetError, socket.timeout):
        pass
    finally:
        release_connection(ip)
        if registered:
            with lock:
                nodes.pop(nickname, None)
            broadcast(f"* {nickname} disconnected", exclude=nickname)
            log(f"[-] Node disconnected: {nickname}", Color.RED)
        conn.close()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, port))
    server.listen()

    print(BANNER)
    print(f"{Color.CYAN}[*] Listening on {HOST}:{port}{Color.RESET}")
    if HOST in ("127.0.0.1", "localhost"):
        print(f"{Color.YELLOW}[*] Bound to localhost only -- only reachable via a local"
              f" forwarder (e.g. Tor hidden service). See TOR_SETUP.md{Color.RESET}")
    print(f"{Color.CYAN}[*] Shops stored in: {SHOPS_DIR}{Color.RESET}")
    print(f"{Color.DIM}[*] Waiting for nodes (Ctrl+C to stop)...{Color.RESET}\n")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}[*] Shutting down server...{Color.RESET}")
    finally:
        server.close()


if __name__ == "__main__":
    main()