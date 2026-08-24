import time
from datetime import datetime, timezone

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

BLOCKS = "▁▂▃▄▅▆▇█"


def human(num: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(num) < 1024:
            return f"{num:7.1f}{unit:>4}"
        num /= 1024
    return f"{num:7.1f} TiB"


def sparkline(values: list[int], vmax: float) -> str:
    if vmax <= 0:
        return "·" * len(values)
    return "".join(
        BLOCKS[min(7, int(v / vmax * (len(BLOCKS) - 1)) + 1)] if v > 0 else "·"
        for v in values
    )


def _axis(idx: int, bucket_secs: float) -> str:
    return datetime.fromtimestamp(idx * bucket_secs, tz=timezone.utc).strftime("%H:%M:%S")


def build_view(store, title: str, live_mode: bool, waiting: bool = False):
    end = store.last_index
    if live_mode and end < int(time.time() // store.bucket_secs):
        end = int(time.time() // store.bucket_secs)
    start, seq = store.window(end)
    out_vals = [b.out_bytes if b else 0 for b in seq]
    in_vals = [b.in_bytes if b else 0 for b in seq]
    vmax = max(max(out_vals), max(in_vals), 1)

    def stat_line(label, lstyle, dstyle, istyle, out_v, in_v, per_sec, tail=()):
        o = human(out_v) + ("/s" if per_sec else "  ")
        i = human(in_v) + ("/s" if per_sec else "  ")
        return Text.assemble(
            (f"{label:>7}  ", lstyle),
            (o + " ", ""),
            ("↓ ", dstyle),
            (i + " ", ""),
            ("↑ ", istyle),
            *tail,
        )

    header = Table.grid(padding=(0, 3))
    header.add_row(
        Text(title, style="bold cyan"),
        stat_line("now", "bold green", "bold green", "bold yellow",
                  out_vals[-1] / store.bucket_secs, in_vals[-1] / store.bucket_secs, True),
    )
    header.add_row(
        "",
        stat_line("peak", "green", "green", "yellow", store.peak_out, store.peak_in, True),
    )
    header.add_row(
        "",
        stat_line("session", "", "", "", store.total_out, store.total_in, False, tail=[
            ("ops=", ""), (f"{store.total_ops} ", ""),
            ("err=", ""), (f"{store.total_errors} ", "magenta bold"),
            ("cxl=", ""), (f"{store.total_cancel_out}", "magenta"),
            ("/", ""), (f"{store.total_cancel_in}", "magenta"),
        ]),
    )

    chart = Group(
        Text.assemble(("OUT ", "bold green"), (sparkline(out_vals, vmax), "green")),
        Text.assemble(("IN  ", "bold yellow"), (sparkline(in_vals, vmax), "yellow")),
        Text(f"{' ' * 4}{_axis(start, store.bucket_secs)}{' ' * max(0, len(seq) - 16)}{_axis(end, store.bucket_secs)}", style="dim"),
    )

    sats_win = store.per_satellite(start, end)
    sats_all = store.session_sats
    names = sorted(set(sats_win) | set(sats_all), key=lambda n: -(sats_all.get(n, [0] * 6)[0] + sats_all.get(n, [0] * 6)[1]))
    body: list = [chart]
    if names:
        name_w = max(9, *(len(n) for n in names[:8]))
        val_w = 11

        def make_table(cols):
            t = Table(box=None, padding=(0, 2))
            t.add_column("satellite", style="cyan", width=name_w)
            for label, style in cols:
                t.add_column(label, justify="right", style=style, width=val_w)
            return t

        bw = make_table([("session ↓", "green"), ("session ↑", "yellow"), ("window ↓", "green"), ("window ↑", "yellow")])
        pcs = make_table([("pieces ↓", "green"), ("pieces ↑", "yellow"), ("cancel ↓", "magenta"), ("cancel ↑", "magenta")])
        for name in names[:8]:
            sess = sats_all.get(name, [0] * 6)
            wob, wib = sats_win.get(name, [0] * 6)[:2]
            bw.add_row(name, human(sess[0]), human(sess[1]), human(wob), human(wib))
            pcs.add_row(
                name,
                f"{sess[2]:,}" if sess[2] else "·",
                f"{sess[3]:,}" if sess[3] else "·",
                f"{sess[4]:,}" if sess[4] else "·",
                f"{sess[5]:,}" if sess[5] else "·",
            )
        body += [Text(""), bw, Text(""), pcs]

    status = "waiting for log file…" if waiting else "[ctrl-c] quit"
    return Panel(
        Group(header, Text(""), *body, Text(status, style="dim")),
        title=f"data flow — last {int(len(seq) * store.bucket_secs)}s",
        border_style="blue",
    )
