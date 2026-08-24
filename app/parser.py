import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")

SATELLITES = {
    "121RTSDpyNZVcEU84Ticf2L1ntiuUimbWgfATz21tuvgk3vzoA6": "ap1",
    "12EayRS2V1kEsWESU9QMRseFhdxYxKicsiFmxrsLZHeLUtdps3S": "us1",
    "12tRQrMTWUWwzwGh18i7Fqs67kmdhH9t6aToeiwbo5mfS2rUmo": "us2",
    "12L9ZFwhzVpuEKMUNUqkaTLGzwY9G24tbiigLiXpmZWKwmcNDDs": "eu1",
    "1wFTAgs9DP5RSnCqKV1eLf6N9wtk4EAtmN5DpSxcs8EjT69tGE": "saltlake",
    "12rfG3sh9NCWiX3ivPjq2HtdLmbqCrvHVEzJubnzFzosMuawymB": "europe-north-1",
    "118UWpMCHzs6CvSgWd9BfFVjw5K9pZbJjkfZJexMtSkmKxvvAW": "stefan-benten",
}

EVENT_KINDS = {"downloaded": "out", "uploaded": "in"}
CANCEL_KINDS = {"download": "cancel_out", "upload": "cancel_in"}


@dataclass(slots=True)
class Event:
    ts: float
    kind: str
    size: int = 0
    satellite: str = ""


def _parse_ts(text: str) -> float | None:
    if not TS_RE.match(text):
        return None
    base, dot, frac = text[:-1].partition(".")
    try:
        dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    ms = int(frac.ljust(3, "0")[:3]) if dot else 0
    return dt.replace(tzinfo=timezone.utc).timestamp() + ms / 1000


def parse_line(line: str) -> Event | None:
    parts = line.split(None, 3)
    if len(parts) < 3:
        return None
    ts = _parse_ts(parts[0])
    if ts is None:
        return None
    if parts[1] == "ERROR":
        return Event(ts, "error")
    if len(parts) < 4:
        return None
    rest = parts[3]
    m = re.match(r"^(\S+)\s*(.*)$", rest, re.S)
    message, tail = m.group(1), m.group(2).strip()
    kind = EVENT_KINDS.get(message)
    if kind is None:
        if message in CANCEL_KINDS and tail.startswith("canceled"):
            kind = CANCEL_KINDS[message]
            tail = tail[len("canceled"):].strip()
        else:
            return None
    elif tail and not tail.startswith("{"):
        return None
    size, sat = 0, ""
    if tail.startswith("{"):
        try:
            payload = json.loads(tail)
        except json.JSONDecodeError:
            return None
        size = int(payload.get("size") or 0)
        sid = payload.get("satellite_id") or ""
        sat = SATELLITES.get(sid, sid[:8])
    return Event(ts, kind, size, sat)
