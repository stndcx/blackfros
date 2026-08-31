# Setting Up a Tor Hidden Service (Linux / macOS / Windows)

This guide covers how to expose a local TCP server (e.g. the BACKFROS server, bound to `127.0.0.1`) as a Tor hidden service, and how to connect to it from a client through Tor.

## How it works

- The server process only ever binds to `127.0.0.1` — it is never reachable directly from the internet or LAN.
- Tor runs alongside it and creates a `.onion` address that forwards incoming connections to that local port.
- Neither side ever learns the other's real IP address: the server only ever sees connections from `127.0.0.1` (the local Tor daemon), and the client's traffic is routed through the Tor network.

---

## 1. Linux

### 1.1 Install

```bash
sudo apt install tor        # Debian/Ubuntu
sudo pacman -S tor          # Arch
```

### 1.2 Configure

Edit `/etc/tor/torrc`:

```
SocksPort 9050
HiddenServiceDir /var/lib/tor/backfros/
HiddenServicePort 5050 127.0.0.1:5050
```

Create the directory with the right owner (the Tor daemon usually runs as `debian-tor`):

```bash
sudo mkdir -p /var/lib/tor/backfros
sudo chown debian-tor:debian-tor /var/lib/tor/backfros
```

### 1.3 Run

```bash
sudo systemctl start tor
sudo systemctl status tor    # confirm it bootstrapped
```

### 1.4 Get the `.onion` address

```bash
sudo cat /var/lib/tor/backfros/hostname
```

---

## 2. macOS

### 2.1 Install

```bash
brew install tor
```

### 2.2 Configure

Edit the config file (created by Homebrew):

- Apple Silicon: `/opt/homebrew/etc/tor/torrc`
- Intel: `/usr/local/etc/tor/torrc`

```
SocksPort 9050
HiddenServiceDir /opt/homebrew/var/lib/tor/backfros
HiddenServicePort 5050 127.0.0.1:5050
```

### 2.3 Run

```bash
brew services start tor
# or run in the foreground:
tor -f /opt/homebrew/etc/tor/torrc
```

### 2.4 Get the `.onion` address

```bash
cat /opt/homebrew/var/lib/tor/backfros/hostname
```

---

## 3. Windows

### 3.1 Install

Download the [Tor Expert Bundle](https://www.torproject.org/download/tor/) for Windows and extract it. Inside you'll find a folder structure like:

```
tor-expert-bundle-windows-x86_64-<version>/
├── data/
├── docs/
└── tor/
    ├── tor.exe
    └── torrc
```

`tor.exe` and the `torrc` config file live in the `tor/` subfolder.

### 3.2 Configure `torrc`

Open PowerShell **in the `tor/` folder** (where `tor.exe` is), and create the config file line by line (avoid pasting multiple lines at once — PowerShell can execute them out of order):

```powershell
"SocksPort 9050" | Out-File -Encoding ascii torrc
"HiddenServiceDir C:\Tor\hidden_service_backfros" | Out-File -Encoding ascii -Append torrc
"HiddenServicePort 5050 127.0.0.1:5050" | Out-File -Encoding ascii -Append torrc
```

> **Important:** do **not** end `HiddenServiceDir` with a trailing backslash (`\`). In Tor's config parser, a trailing backslash at the end of a line is treated as a line-continuation character, which merges the next line into it and breaks parsing (`Invalid argument` / `no ports configured` errors).

Verify the file:

```powershell
type torrc
```

Expected output:

```
SocksPort 9050
HiddenServiceDir C:\Tor\hidden_service_backfros
HiddenServicePort 5050 127.0.0.1:5050
```

### 3.3 Run Tor

```powershell
.\tor.exe -f torrc
```

(Note the `.\` prefix — PowerShell doesn't run executables from the current folder by name alone, unlike `cmd`.)

Wait until you see:

```
Bootstrapped 100% (done)
```

Leave this window open — Tor keeps running as long as it's open.

### 3.4 Get your `.onion` address

Once bootstrapped, Tor creates `hostname` and `private_key` files inside your `HiddenServiceDir`:

```
C:\Tor\hidden_service_backfros\hostname
```

Open it with Notepad — it contains your public address, e.g. `abcd1234....onion`.

### 3.5 Run the server

In a **separate** terminal:

```powershell
python server.py
```

The server listens on `127.0.0.1:5050`; Tor forwards traffic from the `.onion` address to it.

---

## 4. Connecting a client through Tor

If your client script already supports Tor natively (SOCKS5 proxy via `pysocks`, `rdns=True`), just point it at the `.onion` address:

```bash
python3 client.py xxxxxxxxxxxxxxxx.onion 5050 --tor
```

Otherwise, on macOS/Linux you can wrap any TCP client with `torsocks`:

```bash
sudo apt install torsocks     # or: brew install torsocks
torsocks python3 client.py xxxxxxxxxxxxxxxx.onion 5050
```

On Windows there's no native `torsocks`; use a client that supports a SOCKS5 proxy directly (pointing to `127.0.0.1:9050`), such as `pysocks`-based Python code, or an SSH client like Bitvise/PuTTY-based tools with SOCKS proxy support.

---

## 5. Optional: exposing SSH the same way

You can add a second hidden service in the same `torrc` to tunnel SSH:

```
HiddenServiceDir /var/lib/tor/ssh/
HiddenServicePort 22 127.0.0.1:22
```

(Windows: `sshd` via OpenSSH Server listens on port 22; Termux's `sshd` defaults to port 8022 — use that port number instead.)

Connect with:

```bash
torsocks ssh user@xxxxxxxxxxxxxxxx.onion
```

---

## Why Tor instead of a VPN for a peer-to-peer node network

| | VPN | Tor hidden service |
|---|---|---|
| Who sees your real IP | The VPN provider | Nobody |
| Reachable behind NAT/CGNAT without port-forwarding | No | Yes |
| Anonymous from other peers in the network | No — peers can often see each other's IPs | Yes |
| Protects against direct bandwidth/DoS attacks on your IP | Partial | Yes |

For a network where every machine is meant to be an anonymous, mutually-reachable node — without relying on port-forwarding or a shared trusted VPN mesh — Tor hidden services are the more appropriate architecture.

## Security notes (independent of Tor)

Tor hides *who* is connecting and *where* the server physically is, but it does not fix application-level weaknesses. Regardless of whether you route through Tor:

- Add authentication before accepting commands from new connections.
- Add rate limiting / a cap on concurrent connections (unbounded `threading.Thread` per connection is a trivial DoS vector).
- Validate and sanitize all user-supplied input (nicknames, product names, etc.) before writing it to disk.