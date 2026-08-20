# BACKFROS

A minimal peer-to-peer shop network over TCP. Each connected node gets its own
shop, stored as a Markdown file on the server, plus simple chat commands to
coordinate trades.

## Features
- Each nickname gets its own shop (`shops/<hash>.md`)
- Browse shops, add/remove products, buy from others
- Simple broadcast chat (`CHAT`) and private messages (`MSG`)

## Usage

Server:
```
python3 server.py [port]
```

Client:
```
python3 client.py <server_ip> [port]
```

Once connected, type `HELP` for the full command list.

## Disclaimer

This project is provided for educational and demonstration purposes. It is a
general-purpose networking tool and is not designed, intended, or endorsed
for use in any illegal activity. The author is not responsible for how third
parties choose to use this software; all responsibility for compliance with
applicable laws rests with the user.

## License

MIT License. Provided "AS IS", without warranty of any kind, express or
implied.