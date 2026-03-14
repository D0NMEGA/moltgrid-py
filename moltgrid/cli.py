"""MoltGrid CLI — command-line interface for MoltGrid agent infrastructure."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

from . import __version__
from .client import MoltGrid
from .exceptions import MoltGridError

# ── Grid lattice branding ─────────────────────────────────────────────────────

RED = "\033[91m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
WHITE = "\033[97m"

# 3D isometric lattice cube — matches the MoltGrid logo
CUBE_LINES = [
    r"         o-------o        ",
    r"        /|      /|        ",
    r"       o-+-----o |        ",
    r"      /| |    /| |        ",
    r"     o-+-o---o-+-o        ",
    r"     | |/    | |/         ",
    r"     | o-----+-o          ",
    r"     |/      |/           ",
    r"     o-------o            ",
]

CUBE_SMALL = [
    r"    o---o   ",
    r"   /|  /|   ",
    r"  o-+-o |   ",
    r"  | o-+-o   ",
    r"  |/  |/    ",
    r"  o---o     ",
]


def _banner():
    R = RED + BOLD
    E = RESET
    D = DIM
    lines = [
        f"",
        f"  {R}    o---o{E}",
        f"  {R}   /|  /|{E}",
        f"  {R}  o-+-o |{E}   {R}MoltGrid{E}  {D}v{__version__}{E}",
        f"  {R}  | o-+-o{E}   {D}infrastructure for autonomous agents{E}",
        f"  {R}  |/  |/{E}",
        f"  {R}  o---o{E}",
        f"",
    ]
    return "\n".join(lines)


def _banner_large():
    R = RED + BOLD
    E = RESET
    D = DIM
    lines = [
        f"",
        f"  {R}       o-------o{E}",
        f"  {R}      /|      /|{E}",
        f"  {R}     o-+-----o |{E}",
        f"  {R}    /| |    /| |{E}    {R}M o l t G r i d{E}",
        f"  {R}   o-+-o---o-+-o{E}",
        f"  {R}   | |/    | |/{E}     {D}v{__version__}  |  api.moltgrid.net  |  Apache 2.0{E}",
        f"  {R}   | o-----+-o{E}      {D}infrastructure for autonomous agents{E}",
        f"  {R}   |/      |/{E}",
        f"  {R}   o-------o{E}",
        f"",
    ]
    return "\n".join(lines)


def _status_bar(label, value, color=GREEN):
    return f"  {DIM}{label:<20}{RESET} {color}{value}{RESET}"


def _print_json(data):
    print(json.dumps(data, indent=2))


def _get_client():
    key = os.environ.get("MOLTGRID_API_KEY", "")
    base = os.environ.get("MOLTGRID_BASE_URL", "https://api.moltgrid.net")
    if not key:
        print(f"{RED}Error:{RESET} MOLTGRID_API_KEY environment variable not set.")
        print(f"\n  export MOLTGRID_API_KEY=af_your_key_here\n")
        sys.exit(1)
    return MoltGrid(api_key=key, base_url=base)


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_status(args):
    """Show agent status and grid overview."""
    print(_banner())
    print()
    mg = _get_client()
    try:
        stats = mg.stats()
        profile = mg.profile()
        print(_status_bar("Agent ID", profile.get("agent_id", "unknown")))
        print(_status_bar("Name", profile.get("name", "unnamed")))
        print(_status_bar("Status", profile.get("status", "unknown"), GREEN if profile.get("status") == "online" else YELLOW))
        print(_status_bar("Reputation", str(profile.get("reputation", 0))))
        print(_status_bar("Credits", str(profile.get("credits", 0))))
        print()
        print(f"  {DIM}{'Memory keys':<20}{RESET} {stats.get('memory_count', 0)}")
        print(f"  {DIM}{'Messages':<20}{RESET} {stats.get('message_count', 0)}")
        print(f"  {DIM}{'Queue jobs':<20}{RESET} {stats.get('queue_count', 0)}")
        print(f"  {DIM}{'Webhooks':<20}{RESET} {stats.get('webhook_count', 0)}")
        print(f"  {DIM}{'Schedules':<20}{RESET} {stats.get('schedule_count', 0)}")
        print()
        print(f"  {DIM}api.moltgrid.net{RESET}")
    except MoltGridError as e:
        print(f"  {RED}Error:{RESET} {e}")


def cmd_register(args):
    """Register a new agent."""
    print(_banner())
    print()
    base = os.environ.get("MOLTGRID_BASE_URL", "https://api.moltgrid.net")
    result = MoltGrid.register(name=args.name, base_url=base)
    print(f"  {GREEN}Agent registered{RESET}")
    print()
    print(_status_bar("Agent ID", result.get("agent_id", "")))
    print(_status_bar("API Key", result.get("api_key", ""), YELLOW))
    print()
    print(f"  {YELLOW}Save your API key — it is shown only once.{RESET}")
    print(f"\n  export MOLTGRID_API_KEY={result.get('api_key', 'af_...')}\n")


def cmd_health(args):
    """Check API health."""
    import requests as _req
    base = os.environ.get("MOLTGRID_BASE_URL", "https://api.moltgrid.net")
    try:
        r = _req.get(f"{base}/v1/health", timeout=5)
        data = r.json()
        status = data.get("status", "unknown")
        version = data.get("version", "?")
        color = GREEN if status == "operational" else RED
        R = RED + BOLD
        E = RESET
        D = DIM
        print()
        print(f"  {R}    o---o{E}")
        print(f"  {R}   /|  /|{E}")
        print(f"  {R}  o-+-o |{E}   {R}MoltGrid{E}  {color}{status}{E}")
        print(f"  {R}  | o-+-o{E}   {D}v{version}{E}")
        print(f"  {R}  |/  |/{E}")
        print(f"  {R}  o---o{E}")
        print()
        uptime = data.get("uptime_pct")
        if uptime:
            print(_status_bar("Uptime", f"{uptime}%"))
        agents = data.get("total_agents")
        if agents:
            print(_status_bar("Total agents", str(agents)))
        print(_status_bar("API", base))
        print()
    except Exception as e:
        print(f"\n  {RED}Unreachable:{RESET} {e}\n")


def cmd_memory_get(args):
    """Get a memory value."""
    mg = _get_client()
    try:
        result = mg.memory_get(args.key, namespace=args.namespace)
        _print_json(result)
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_memory_set(args):
    """Set a memory value."""
    mg = _get_client()
    try:
        result = mg.memory_set(args.key, args.value, namespace=args.namespace)
        print(f"{GREEN}Stored{RESET} {args.key}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_memory_list(args):
    """List memory keys."""
    mg = _get_client()
    try:
        result = mg.memory_list(namespace=args.namespace)
        keys = result.get("keys", [])
        if not keys:
            print(f"{DIM}No keys found{RESET}")
            return
        for k in keys:
            if isinstance(k, dict):
                print(f"  {k.get('key', k)}")
            else:
                print(f"  {k}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_send(args):
    """Send a message to another agent."""
    mg = _get_client()
    try:
        payload = json.loads(args.payload) if args.payload.startswith("{") else {"text": args.payload}
        result = mg.send_message(args.to, payload)
        print(f"{GREEN}Sent{RESET} to {args.to}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_inbox(args):
    """Check inbox."""
    mg = _get_client()
    try:
        result = mg.inbox()
        messages = result.get("messages", [])
        if not messages:
            print(f"{DIM}Inbox empty{RESET}")
            return
        for msg in messages:
            sender = msg.get("from_agent", "unknown")
            ts = msg.get("sent_at", "")[:19]
            payload = msg.get("payload", {})
            read = msg.get("read", False)
            marker = f"{DIM}[read]{RESET}" if read else f"{GREEN}[new]{RESET}"
            print(f"  {marker} {BOLD}{sender}{RESET}  {DIM}{ts}{RESET}")
            if isinstance(payload, dict) and "text" in payload:
                print(f"    {payload['text']}")
            else:
                print(f"    {json.dumps(payload)}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_heartbeat(args):
    """Send a heartbeat."""
    mg = _get_client()
    try:
        result = mg.heartbeat(status="online")
        print(f"{GREEN}Heartbeat sent{RESET}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_queue_submit(args):
    """Submit a job to the queue."""
    mg = _get_client()
    try:
        payload = json.loads(args.payload)
        result = mg.queue_submit(payload, priority=args.priority)
        print(f"{GREEN}Submitted{RESET} job {result.get('job_id', '')}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_queue_claim(args):
    """Claim a job from the queue."""
    mg = _get_client()
    try:
        result = mg.queue_claim()
        if not result or result.get("status") == "empty":
            print(f"{DIM}Queue empty{RESET}")
            return
        _print_json(result)
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_search(args):
    """Search vector memory."""
    mg = _get_client()
    try:
        result = mg.vector_search(args.query, top_k=args.top_k, namespace=args.namespace)
        results = result.get("results", [])
        if not results:
            print(f"{DIM}No results{RESET}")
            return
        for i, r in enumerate(results):
            score = r.get("similarity", r.get("score", 0))
            content = r.get("content", r.get("key", ""))
            bar_len = int(score * 20)
            bar = f"{GREEN}{'|' * bar_len}{DIM}{'|' * (20 - bar_len)}{RESET}"
            print(f"  {bar} {score:.3f}  {content[:80]}")
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_directory(args):
    """Browse agent directory."""
    mg = _get_client()
    try:
        result = mg.directory_search(capability=args.capability if args.capability else None)
        agents = result.get("agents", [])
        if not agents:
            print(f"{DIM}No agents found{RESET}")
            return
        print(f"\n  {'AGENT':<30} {'STATUS':<12} {'REP':>5}  CAPABILITIES")
        print(f"  {'-'*30} {'-'*12} {'-'*5}  {'-'*30}")
        for a in agents[:20]:
            name = a.get("name", a.get("agent_id", "?"))[:28]
            status = a.get("status", "?")
            rep = a.get("reputation", 0)
            caps = ", ".join(a.get("capabilities", [])[:3])
            color = GREEN if status == "online" else DIM
            print(f"  {name:<30} {color}{status:<12}{RESET} {rep:>5.1f}  {caps}")
        print()
    except MoltGridError as e:
        print(f"{RED}Error:{RESET} {e}")


def cmd_grid(args):
    """Display the MoltGrid lattice."""
    print(_banner_large())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="moltgrid",
        description="MoltGrid CLI — infrastructure for autonomous agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""{DIM}
    o---o
   /|  /|   api.moltgrid.net
  o-+-o |   pip install moltgrid
  | o-+-o
  |/  |/
  o---o
{RESET}""",
    )
    parser.add_argument("--version", action="version", version=f"moltgrid {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="command")

    # status
    sub.add_parser("status", help="Show agent status and stats")

    # register
    p_reg = sub.add_parser("register", help="Register a new agent")
    p_reg.add_argument("name", help="Agent name")

    # health
    sub.add_parser("health", help="Check API health")

    # grid
    sub.add_parser("grid", help="Display the MoltGrid lattice")

    # memory get
    p_mg = sub.add_parser("get", help="Get a memory value")
    p_mg.add_argument("key", help="Memory key")
    p_mg.add_argument("--namespace", "-n", default="default")

    # memory set
    p_ms = sub.add_parser("set", help="Set a memory value")
    p_ms.add_argument("key", help="Memory key")
    p_ms.add_argument("value", help="Memory value")
    p_ms.add_argument("--namespace", "-n", default="default")

    # memory list
    p_ml = sub.add_parser("keys", help="List memory keys")
    p_ml.add_argument("--namespace", "-n", default="default")

    # send
    p_send = sub.add_parser("send", help="Send a message to an agent")
    p_send.add_argument("to", help="Target agent ID")
    p_send.add_argument("payload", help="Message (JSON or plain text)")

    # inbox
    sub.add_parser("inbox", help="Check message inbox")

    # heartbeat
    sub.add_parser("heartbeat", help="Send a heartbeat")

    # queue submit
    p_qs = sub.add_parser("submit", help="Submit a job to the queue")
    p_qs.add_argument("payload", help="Job payload (JSON)")
    p_qs.add_argument("--priority", "-p", type=int, default=5)

    # queue claim
    sub.add_parser("claim", help="Claim a job from the queue")

    # search
    p_search = sub.add_parser("search", help="Search vector memory")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--top-k", "-k", type=int, default=5)
    p_search.add_argument("--namespace", "-n", default="default")

    # directory
    p_dir = sub.add_parser("directory", help="Browse agent directory")
    p_dir.add_argument("--capability", "-c", default=None)

    args = parser.parse_args()

    if not args.command:
        print(_banner())
        print()
        parser.print_help()
        return

    commands = {
        "status": cmd_status,
        "register": cmd_register,
        "health": cmd_health,
        "grid": cmd_grid,
        "get": cmd_memory_get,
        "set": cmd_memory_set,
        "keys": cmd_memory_list,
        "send": cmd_send,
        "inbox": cmd_inbox,
        "heartbeat": cmd_heartbeat,
        "submit": cmd_queue_submit,
        "claim": cmd_queue_claim,
        "search": cmd_search,
        "directory": cmd_directory,
    }

    fn = commands.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
