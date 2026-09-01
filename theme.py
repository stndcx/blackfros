"""
BACKFROS - theme
v3.0.0-pre.1
"""

BG = "#1d1d2d"
TEXT = "#999db5"
SELECT = "#94e1d5"
MUTED = "#525365"
GREEN = "#8ab78a"
RED = "#e08a8a"
MAGENTA = "#b3a1e0"

CSS = f"""
Screen {{
    background: {BG};
    color: {TEXT};
}}

Header {{
    background: {BG};
    color: {SELECT};
    text-style: bold;
}}

Footer {{
    background: {BG};
    color: {MUTED};
}}

#shops-panel {{
    width: 34%;
    border: round {MUTED};
    border-title-color: {SELECT};
}}

#detail-panel {{
    width: 1fr;
    border: round {MUTED};
    border-title-color: {SELECT};
    padding: 1 2;
}}

ListView {{
    background: {BG};
}}

ListView > ListItem {{
    padding: 0 1;
    color: {TEXT};
}}

ListView > ListItem.--highlight {{
    background: {SELECT} 25%;
    color: {SELECT};
}}

#input-bar {{
    dock: bottom;
    height: 3;
    border: round {MUTED};
}}

Input {{
    background: {BG};
    color: {TEXT};
}}

Input:focus {{
    border: round {SELECT};
}}

.ok {{ color: {GREEN}; }}
.error {{ color: {RED}; }}
.chat {{ color: {MAGENTA}; }}
.event {{ color: {SELECT}; }}
.dim {{ color: {MUTED}; }}
"""