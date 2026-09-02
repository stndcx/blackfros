<p align="center">
	<a href="https://gitlab.com/stndc/blackfros/">
		<img src="https://gitlab.com/stndc/blackfros/-/raw/main/docs/screenshots/blackfros.jpg" alt="Blackfros logo" width="180">
	</a>
</p>

<p align="center">
	<strong>Blackfros</strong><br>
	<em>A minimal peer-to-peer shop network over TCP.</em>
</p>

Each connected node gets its own shop, stored as a Markdown file on the server, plus simple chat commands to coordinate trades.

### Collaborate
You can support me by [buying me a coffee](https://buymeacoffee.com/stndc).

## Features
- Each nickname gets its own shop (`shops/<hash>.md`)
- Browse shops, add/remove products, buy from others
- Simple broadcast chat (`CHAT`) and private messages (`MSG`)
- Optional Tor support, so nodes can connect without exposing their real IP

## Requirements
- Python 3.9+
- `pip install prompt_toolkit pyfiglet`
- `pip install pysocks` (only needed on the client if you plan to use `--tor`)

## Usage

### Linux / macOS

Server:
```bash
python3 server.py [port]
```

Client:
```bash
python3 client.py <server_ip> [port]
```

### Windows

Same scripts, no changes needed — just run them with `py` (or `python`)
from PowerShell or CMD:

Server:
```powershell
py server.py [port]
```

Client:
```powershell
py client.py <server_ip> [port]
```

If `py` isn't recognized, use `python` instead, or reinstall Python from
python.org making sure to check "Add python.exe to PATH" during setup.

Once connected, type `HELP` for the full command list.

## Running over Tor (optional)

By default `server.py` binds to `127.0.0.1` only, so it's not reachable
directly from the internet or LAN — it's meant to be exposed through a Tor
hidden service instead. See `TOR_SETUP.md` for the full walkthrough
(works the same way on Windows, using the Tor Expert Bundle instead of the
`tor` package).

Short version once the hidden service is set up:

```bash
python3 client.py <your-address>.onion [port] --tor
```

(on Windows: `py client.py <your-address>.onion [port] --tor`)

If you want the server reachable directly (no Tor), override the bind
address:

```bash
BLACKFROS_HOST=0.0.0.0 python3 server.py [port]        # Linux/macOS
$env:BLACKFROS_HOST="0.0.0.0"; py server.py [port]      # Windows PowerShell
```

Doing this means the server will see and log the real IP of every
connecting client.

## Disclaimer
This project is provided for educational and demonstration purposes. It is a
general-purpose networking tool and is not designed, intended, or endorsed
for use in any illegal activity. The author is not responsible for how third
parties choose to use this software; all responsibility for compliance with
applicable laws rests with the user.

## License
MIT License. Provided "AS IS", without warranty of any kind, express or
implied.