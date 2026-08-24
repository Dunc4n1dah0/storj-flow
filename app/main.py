import argparse
import signal
import sys
import time

from rich.console import Console

from .parser import parse_line
from .screen import DiffScreen
from .store import Store
from .tail import LogTail
from .ui import build_view


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="storj-flow", description="Live ASCII chart of storagenode data flow")
    p.add_argument("logfile", nargs="?", help="path to node.log to follow")
    p.add_argument("--title", default="storagenode", help="label shown in the header")
    p.add_argument("--bucket-secs", type=float, default=1.0, help="seconds per chart bucket")
    p.add_argument("--history", type=int, default=60, help="buckets visible in chart")
    p.add_argument("--refresh", type=float, default=0.5, help="redraw interval seconds")
    p.add_argument("--from-start", action="store_true", help="read whole file instead of starting at EOF")
    p.add_argument("--replay", metavar="FILE", help="replay a sample/fixture file instead of following")
    p.add_argument("--speed", type=float, default=10.0, help="replay acceleration factor")
    args = p.parse_args(argv)
    if bool(args.logfile) == bool(args.replay):
        p.error("give LOGFILE to follow, or --replay FILE, not both")
    return args


def run_replay(store: Store, path: str, speed: float, refresh: float, title: str, console: Console):
    events = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            ev = parse_line(line)
            if ev is not None:
                events.append(ev)
    if not events:
        print(f"no parsable events in {path}", file=sys.stderr)
        return 1
    screen = DiffScreen(console)
    try:
        prev_ts = None
        last_render = 0.0
        for ev in events:
            if prev_ts is not None:
                delay = min((ev.ts - prev_ts) / speed, 2.0)
                if delay > 0:
                    time.sleep(delay)
            store.add(ev)
            now = time.monotonic()
            if now - last_render >= refresh:
                screen.draw(build_view(store, title, False))
                last_render = now
            prev_ts = ev.ts
        screen.draw(build_view(store, title, False))
        while True:
            time.sleep(1)
    finally:
        screen.close()
    return 0


def run_live(store: Store, path: str, refresh: float, title: str, console: Console, from_start: bool):
    tail = LogTail(path, from_start=from_start)
    screen = DiffScreen(console)
    try:
        last_state = None
        while True:
            for line in tail.poll():
                ev = parse_line(line)
                if ev is not None:
                    store.add(ev)
            state = (store.total_ops, tail.waiting, int(time.time() // store.bucket_secs))
            if state != last_state:
                screen.draw(build_view(store, title, True, tail.waiting))
                last_state = state
            time.sleep(refresh)
    finally:
        screen.close()
    return 0


def _raise_kbint():
    raise KeyboardInterrupt


def main(argv=None) -> int:
    args = parse_args(argv)
    store = Store(args.bucket_secs, args.history)
    console = Console()
    signal.signal(signal.SIGTERM, lambda *_: _raise_kbint())
    try:
        if args.replay:
            return run_replay(store, args.replay, args.speed, args.refresh, args.title, console)
        return run_live(store, args.logfile, args.refresh, args.title, console, args.from_start)
    except KeyboardInterrupt:
        return 0
