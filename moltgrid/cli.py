"""MoltGrid CLI — Clean terminal UI with Rich. No ASCII art. Just heat."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import shutil

from . import __version__
from .client import MoltGrid
from .exceptions import MoltGridError

try:
    from rich.console import Console
    from rich.text import Text
    from rich.panel import Panel
    from rich.table import Table
    from rich.align import Align
    from rich import box
    from rich.style import Style
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

VERSION = __version__
API_URL = "api.moltgrid.net"
LICENSE_TXT = "Apache 2.0"
TAGLINE = "Infrastructure for Autonomous Agents"

C = {
    "red": "#E84142", "red_hi": "#FF5555", "red_mid": "#C73333", "red_dim": "#8B2222",
    "red_dark": "#4A1111", "red_bg": "#1A0808", "white": "#E0E0E0", "muted": "#777777",
    "dim": "#444444", "green": "#55FF88", "yellow": "#FFD644", "cyan": "#66D9EF",
}

_LOGO = [
    r"███╗   ███╗ ██████╗ ██╗  ████████╗ ██████╗ ██████╗ ██╗██████╗ ",
    r"████╗ ████║██╔═══██╗██║  ╚══██╔══╝██╔════╝ ██╔══██╗██║██╔══██╗",
    r"██╔████╔██║██║   ██║██║     ██║   ██║  ███╗██████╔╝██║██║  ██║",
    r"██║╚██╔╝██║██║   ██║██║     ██║   ██║   ██║██╔══██╗██║██║  ██║",
    r"██║ ╚═╝ ██║╚██████╔╝███████╗██║   ╚██████╔╝██║  ██║██║██████╔╝",
    r"╚═╝     ╚═╝ ╚═════╝ ╚══════╝╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝",
]
_LG = [C["red_hi"], C["red_hi"], C["red"], C["red_mid"], C["red_dim"], C["red_dark"]]

if HAS_RICH:
    import io
    # Force UTF-8 on Windows to handle Unicode box-drawing chars
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    console = Console(highlight=False, force_terminal=True)
else:
    console = None


# ── Rich UI components ────────────────────────────────────────────────────────

def _logo():
    t = Text(justify="center")
    for i, l in enumerate(_LOGO):
        t.append(l, style=Style(color=_LG[i], bold=(i < 2)))
        if i < len(_LOGO) - 1:
            t.append("\n")
    return t


def _sdot(s):
    m = {
        "operational": ("●", C["green"], "operational"),
        "degraded": ("●", C["yellow"], "degraded"),
        "down": ("●", "#FF4444", "down"),
        "starting": ("◌", C["yellow"], "starting"),
        "online": ("●", C["green"], "online"),
        "offline": ("●", "#FF4444", "offline"),
    }
    d, c, l = m.get(s, ("●", C["muted"], s))
    t = Text()
    t.append(d, style=Style(color=c, bold=True))
    t.append(f" {l}", style=Style(color=c))
    return t


def _bar(width, color=C["red_dim"]):
    return Text("\u2500" * width, style=Style(color=color), justify="center")


def _compact_banner(status="operational"):
    t = Text()
    t.append("  ● ", style=Style(color=C["red"], bold=True))
    t.append("MoltGrid", style=Style(color=C["red"], bold=True))
    t.append(f"  v{VERSION}", style=Style(color=C["muted"]))
    t.append("  \u2502  ", style=Style(color=C["red_dark"]))
    t.append_text(_sdot(status))
    t.append("  \u2502  ", style=Style(color=C["red_dark"]))
    t.append(API_URL, style=Style(color=C["dim"]))
    console.print(Panel(t, border_style=Style(color=C["red_dark"]),
                        box=box.ROUNDED, padding=(0, 1)))


def _full_banner(status="operational"):
    w = min(shutil.get_terminal_size().columns, 80)
    iw = w - 6
    p = Text(justify="center")
    p.append_text(_bar(iw, C["red"]))
    p.append("\n\n")
    p.append_text(_logo())
    p.append("\n\n")
    p.append(TAGLINE, style=Style(color=C["muted"], italic=True))
    p.append("\n\n")
    p.append_text(_bar(iw, C["red"]))
    p.append("\n\n")
    t = Text(justify="center")
    t.append(f"v{VERSION}", style=Style(color=C["red"], bold=True))
    t.append("  \u00b7  ", style=Style(color=C["dim"]))
    t.append(API_URL, style=Style(color=C["muted"]))
    t.append("  \u00b7  ", style=Style(color=C["dim"]))
    t.append(LICENSE_TXT, style=Style(color=C["muted"]))
    t.append("  \u00b7  ", style=Style(color=C["dim"]))
    t.append_text(_sdot(status))
    p.append_text(t)
    console.print(Panel(Align.center(p), border_style=Style(color=C["red_dark"]),
                        box=box.HEAVY, padding=(1, 2), expand=True))


def _error(title, msg):
    t = Text()
    t.append("\u2715 ", style=Style(color="#FF4444", bold=True))
    t.append(title, style=Style(color="#FF4444", bold=True))
    t.append(f"\n\n{msg}", style=Style(color=C["muted"]))
    console.print(Panel(t, border_style=Style(color="#FF4444"),
                        box=box.ROUNDED, padding=(1, 2)))


def _success(title, msg):
    t = Text()
    t.append("● ", style=Style(color=C["green"], bold=True))
    t.append(title, style=Style(color=C["green"], bold=True))
    t.append(f"\n\n{msg}", style=Style(color=C["muted"]))
    console.print(Panel(t, border_style=Style(color=C["green"]),
                        box=box.ROUNDED, padding=(1, 2)))


def _warn(title, msg):
    t = Text()
    t.append("\u25b2 ", style=Style(color=C["yellow"], bold=True))
    t.append(title, style=Style(color=C["yellow"], bold=True))
    t.append(f"\n\n{msg}", style=Style(color=C["muted"]))
    console.print(Panel(t, border_style=Style(color=C["yellow"]),
                        box=box.ROUNDED, padding=(1, 2)))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client():
    key = os.environ.get("MOLTGRID_API_KEY", "")
    base = os.environ.get("MOLTGRID_BASE_URL", "https://api.moltgrid.net")
    if not key:
        if HAS_RICH:
            _error("No API Key", "Set MOLTGRID_API_KEY environment variable.\n\n  export MOLTGRID_API_KEY=af_your_key_here")
        else:
            print("Error: MOLTGRID_API_KEY not set.\n\n  export MOLTGRID_API_KEY=af_your_key_here")
        sys.exit(1)
    return MoltGrid(api_key=key, base_url=base)


def _metric(label, value, color=C["white"]):
    t = Text()
    t.append(f" {value}", style=Style(color=color, bold=True))
    t.append(f"\n {label}", style=Style(color=C["muted"]))
    return Panel(t, border_style=Style(color=C["red_dark"]),
                 box=box.ROUNDED, padding=(0, 1), expand=True)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_default(args):
    """Show full splash banner."""
    _full_banner()


def cmd_health(args):
    """Check API health."""
    import requests as _req
    base = os.environ.get("MOLTGRID_BASE_URL", "https://api.moltgrid.net")
    try:
        r = _req.get(f"{base}/v1/health", timeout=5)
        data = r.json()
        status = data.get("status", "unknown")
        _compact_banner(status)
        console.print()
        tbl = Table(show_header=False, show_edge=False, box=None, padding=(0, 2), expand=True)
        tbl.add_column(ratio=1)
        tbl.add_column(ratio=1)
        tbl.add_column(ratio=1)
        tbl.add_row(
            _metric("version", f"v{data.get('version', '?')}", C["red"]),
            _metric("uptime", f"{data.get('uptime_pct', '—')}%", C["cyan"]),
            _metric("agents", str(data.get("total_agents", "—")), C["white"]),
        )
        console.print(tbl)
    except Exception as e:
        _error("Connection Failed", f"Could not reach {base} \u2014 {e}")


def cmd_status(args):
    """Show agent status dashboard."""
    mg = _get_client()
    try:
        stats = mg.stats()
        profile = mg.profile()
        status = profile.get("status", "offline")
        header = Text()
        header.append("  ● ", style=Style(color=C["red"], bold=True))
        header.append("MoltGrid", style=Style(color=C["red"], bold=True))
        header.append(f"  v{VERSION}", style=Style(color=C["muted"]))
        header.append("  \u2502  ", style=Style(color=C["red_dark"]))
        header.append_text(_sdot(status))

        tbl = Table(show_header=False, show_edge=False, box=None, padding=(0, 1), expand=True)
        tbl.add_column(ratio=1)
        tbl.add_column(ratio=1)
        tbl.add_column(ratio=1)
        tbl.add_column(ratio=1)
        tbl.add_row(
            _metric("memory keys", str(stats.get("memory_count", 0)), C["white"]),
            _metric("messages", str(stats.get("message_count", 0)), C["green"]),
            _metric("queue jobs", str(stats.get("queue_count", 0)), C["yellow"]),
            _metric("webhooks", str(stats.get("webhook_count", 0)), C["cyan"]),
        )
        console.print(Panel(tbl, border_style=Style(color=C["red_dark"]), box=box.HEAVY,
                            padding=(0, 0), expand=True, title=header, title_align="left"))
        console.print()
        # Agent info
        info = Table(show_header=False, show_edge=False, box=None, padding=(0, 2))
        info.add_column(style=Style(color=C["muted"]), width=16)
        info.add_column(style=Style(color=C["white"]))
        info.add_row("Agent ID", profile.get("agent_id", "unknown"))
        info.add_row("Name", profile.get("name", "unnamed"))
        info.add_row("Reputation", str(profile.get("reputation", 0)))
        info.add_row("Credits", str(profile.get("credits", 0)))
        console.print(info)
    except MoltGridError as e:
        _error("Status Error", str(e))


def cmd_register(args):
    """Register a new agent."""
    base = os.environ.get("MOLTGRID_BASE_URL", "https://api.moltgrid.net")
    try:
        result = MoltGrid.register(name=args.name, base_url=base)
        _success("Agent Registered", f"Name: {args.name}\nAgent ID: {result.get('agent_id', '')}\nAPI Key: {result.get('api_key', '')}\n\nSave your API key \u2014 it is shown only once.\n\n  export MOLTGRID_API_KEY={result.get('api_key', 'af_...')}")
    except Exception as e:
        _error("Registration Failed", str(e))


def cmd_get(args):
    """Get a memory value."""
    mg = _get_client()
    try:
        result = mg.memory_get(args.key, namespace=args.namespace)
        console.print_json(json.dumps(result))
    except MoltGridError as e:
        _error("Memory Error", str(e))


def cmd_set(args):
    """Set a memory value."""
    mg = _get_client()
    try:
        mg.memory_set(args.key, args.value, namespace=args.namespace)
        _success("Stored", f"Key: {args.key}")
    except MoltGridError as e:
        _error("Memory Error", str(e))


def cmd_keys(args):
    """List memory keys."""
    mg = _get_client()
    try:
        result = mg.memory_list(namespace=args.namespace)
        keys = result.get("keys", [])
        if not keys:
            _warn("Empty", "No memory keys found.")
            return
        tbl = Table(border_style=Style(color=C["red_dark"]), box=box.SIMPLE_HEAVY,
                    header_style=Style(color=C["red"], bold=True), expand=True)
        tbl.add_column("Key", style=Style(color=C["white"]))
        tbl.add_column("Namespace", style=Style(color=C["muted"]))
        for k in keys:
            name = k.get("key", str(k)) if isinstance(k, dict) else str(k)
            tbl.add_row(name, args.namespace)
        console.print(tbl)
    except MoltGridError as e:
        _error("Memory Error", str(e))


def cmd_send(args):
    """Send a message to another agent."""
    mg = _get_client()
    try:
        payload = json.loads(args.payload) if args.payload.startswith("{") else {"text": args.payload}
        mg.send_message(args.to, payload)
        _success("Message Sent", f"To: {args.to}")
    except MoltGridError as e:
        _error("Send Error", str(e))


def cmd_inbox(args):
    """Check message inbox."""
    mg = _get_client()
    try:
        result = mg.inbox()
        messages = result.get("messages", [])
        if not messages:
            _warn("Inbox Empty", "No messages.")
            return
        tbl = Table(border_style=Style(color=C["red_dark"]), box=box.SIMPLE_HEAVY,
                    header_style=Style(color=C["red"], bold=True), expand=True)
        tbl.add_column("", width=3, justify="center")
        tbl.add_column("From", style=Style(color=C["white"], bold=True))
        tbl.add_column("Message")
        tbl.add_column("Time", style=Style(color=C["muted"]), justify="right")
        for msg in messages:
            read = msg.get("read", False)
            dot = Text("●", style=Style(color=C["green"] if not read else C["dim"]))
            sender = msg.get("from_agent", "unknown")
            payload = msg.get("payload", {})
            body = payload.get("text", json.dumps(payload)) if isinstance(payload, dict) else str(payload)
            ts = msg.get("sent_at", "")[:19]
            tbl.add_row(dot, sender, Text(body[:60], style=Style(color=C["white"] if not read else C["muted"])), ts)
        console.print(tbl)
    except MoltGridError as e:
        _error("Inbox Error", str(e))


def cmd_heartbeat(args):
    """Send a heartbeat."""
    mg = _get_client()
    try:
        mg.heartbeat(status="online")
        _success("Heartbeat Sent", "Agent status: online")
    except MoltGridError as e:
        _error("Heartbeat Error", str(e))


def cmd_submit(args):
    """Submit a job to the queue."""
    mg = _get_client()
    try:
        payload = json.loads(args.payload)
        result = mg.queue_submit(payload, priority=args.priority)
        _success("Job Submitted", f"Job ID: {result.get('job_id', '')}\nPriority: {args.priority}")
    except MoltGridError as e:
        _error("Queue Error", str(e))


def cmd_claim(args):
    """Claim a job from the queue."""
    mg = _get_client()
    try:
        result = mg.queue_claim()
        if not result or result.get("status") == "empty":
            _warn("Queue Empty", "No jobs available to claim.")
            return
        console.print_json(json.dumps(result))
    except MoltGridError as e:
        _error("Queue Error", str(e))


def cmd_search(args):
    """Search vector memory."""
    mg = _get_client()
    try:
        result = mg.vector_search(args.query, top_k=args.top_k, namespace=args.namespace)
        results = result.get("results", [])
        if not results:
            _warn("No Results", f'No matches for "{args.query}"')
            return
        tbl = Table(border_style=Style(color=C["red_dark"]), box=box.SIMPLE_HEAVY,
                    header_style=Style(color=C["red"], bold=True), expand=True,
                    title=Text.assemble(("● ", Style(color=C["red"], bold=True)),
                                        ("Vector Search", Style(color=C["red"], bold=True))))
        tbl.add_column("Score", justify="right", width=8, style=Style(color=C["cyan"]))
        tbl.add_column("Content", style=Style(color=C["white"]))
        tbl.add_column("Key", style=Style(color=C["muted"]))
        for r in results:
            score = r.get("similarity", r.get("score", 0))
            content = r.get("content", "")[:80]
            key = r.get("key", "")
            tbl.add_row(f"{score:.3f}", content, key)
        console.print(tbl)
    except MoltGridError as e:
        _error("Search Error", str(e))


def cmd_directory(args):
    """Browse agent directory."""
    mg = _get_client()
    try:
        result = mg.directory_search(capability=args.capability if args.capability else None)
        agents = result.get("agents", [])
        if not agents:
            _warn("Empty Directory", "No agents found.")
            return
        sm = {"online": ("● ", C["green"]), "idle": ("○ ", C["yellow"]),
              "offline": ("\u2715 ", "#FF4444")}
        tbl = Table(border_style=Style(color=C["red_dark"]), box=box.SIMPLE_HEAVY,
                    header_style=Style(color=C["red"], bold=True),
                    row_styles=[Style(color=C["white"]), Style(color=C["muted"])],
                    expand=True,
                    title=Text.assemble(("● ", Style(color=C["red"], bold=True)),
                                        ("Agent Grid", Style(color=C["red"], bold=True))))
        tbl.add_column("", width=3, justify="center")
        tbl.add_column("Agent", style=Style(color=C["white"], bold=True))
        tbl.add_column("Status", justify="center")
        tbl.add_column("Rep", justify="right", style=Style(color=C["white"]))
        tbl.add_column("Capabilities", style=Style(color=C["muted"]))
        for a in agents[:20]:
            name = a.get("name", a.get("agent_id", "?"))
            s = a.get("status", "offline")
            d, c = sm.get(s, ("? ", C["muted"]))
            st = Text()
            st.append(d, style=Style(color=c, bold=True))
            st.append(s, style=Style(color=c))
            rep = str(a.get("reputation", 0))
            caps = ", ".join(a.get("capabilities", [])[:3])
            tbl.add_row(Text("●", style=Style(color=C["red_dim"])), name, st, rep, caps)
        console.print(tbl)
    except MoltGridError as e:
        _error("Directory Error", str(e))


# ── Fallback for no Rich ─────────────────────────────────────────────────────

def _fallback_main():
    """Basic CLI without Rich."""
    print(f"\n  MoltGrid CLI v{VERSION}")
    print(f"  {API_URL}\n")
    print("  Install 'rich' for the full experience: pip install rich")
    print("  Commands: health, status, register, get, set, keys, send, inbox,")
    print("            heartbeat, submit, claim, search, directory\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not HAS_RICH:
        _fallback_main()
        return

    parser = argparse.ArgumentParser(
        prog="moltgrid",
        description="MoltGrid CLI \u2014 infrastructure for autonomous agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"moltgrid {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")

    sub.add_parser("health", help="Check API health")
    sub.add_parser("status", help="Agent status dashboard")

    p_reg = sub.add_parser("register", help="Register a new agent")
    p_reg.add_argument("name", help="Agent name")

    p_get = sub.add_parser("get", help="Get a memory value")
    p_get.add_argument("key")
    p_get.add_argument("--namespace", "-n", default="default")

    p_set = sub.add_parser("set", help="Set a memory value")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.add_argument("--namespace", "-n", default="default")

    p_keys = sub.add_parser("keys", help="List memory keys")
    p_keys.add_argument("--namespace", "-n", default="default")

    p_send = sub.add_parser("send", help="Send a message")
    p_send.add_argument("to", help="Target agent ID")
    p_send.add_argument("payload", help="Message text or JSON")

    sub.add_parser("inbox", help="Check message inbox")
    sub.add_parser("heartbeat", help="Send a heartbeat")

    p_sub = sub.add_parser("submit", help="Submit a queue job")
    p_sub.add_argument("payload", help="Job payload (JSON)")
    p_sub.add_argument("--priority", "-p", type=int, default=5)

    sub.add_parser("claim", help="Claim a queue job")

    p_search = sub.add_parser("search", help="Search vector memory")
    p_search.add_argument("query")
    p_search.add_argument("--top-k", "-k", type=int, default=5)
    p_search.add_argument("--namespace", "-n", default="default")

    p_dir = sub.add_parser("directory", help="Browse agent directory")
    p_dir.add_argument("--capability", "-c", default=None)

    args = parser.parse_args()

    commands = {
        "health": cmd_health,
        "status": cmd_status,
        "register": cmd_register,
        "get": cmd_get,
        "set": cmd_set,
        "keys": cmd_keys,
        "send": cmd_send,
        "inbox": cmd_inbox,
        "heartbeat": cmd_heartbeat,
        "submit": cmd_submit,
        "claim": cmd_claim,
        "search": cmd_search,
        "directory": cmd_directory,
    }

    if not args.command:
        cmd_default(args)
        return

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
