class Bucket:
    __slots__ = ("in_bytes", "out_bytes", "errors", "ops", "sats")

    def __init__(self):
        self.in_bytes = 0
        self.out_bytes = 0
        self.errors = 0
        self.ops = 0
        self.sats: dict[str, list[int]] = {}


class Store:
    def __init__(self, bucket_secs: float, history: int):
        self.bucket_secs = bucket_secs
        self.history = history
        self.buckets: dict[int, Bucket] = {}
        self.total_in = 0
        self.total_out = 0
        self.total_errors = 0
        self.total_ops = 0
        self.total_cancel_out = 0
        self.total_cancel_in = 0
        self.peak_in = 0.0
        self.peak_out = 0.0
        self.last_ts = 0.0
        self.session_sats: dict[str, list[int]] = {}

    def add(self, ev) -> None:
        idx = int(ev.ts // self.bucket_secs)
        b = self.buckets.setdefault(idx, Bucket())
        b.ops += 1
        self.total_ops += 1
        if ev.kind == "error":
            b.errors += 1
            self.total_errors += 1
        else:
            pair = b.sats.setdefault(ev.satellite or "?", [0, 0, 0, 0, 0, 0])
            sess = self.session_sats.setdefault(ev.satellite or "?", [0, 0, 0, 0, 0, 0])
            if ev.kind == "out":
                b.out_bytes += ev.size
                self.total_out += ev.size
                self.peak_out = max(self.peak_out, b.out_bytes / self.bucket_secs)
                pair[0] += ev.size
                pair[2] += 1
                sess[0] += ev.size
                sess[2] += 1
            elif ev.kind == "in":
                b.in_bytes += ev.size
                self.total_in += ev.size
                self.peak_in = max(self.peak_in, b.in_bytes / self.bucket_secs)
                pair[1] += ev.size
                pair[3] += 1
                sess[1] += ev.size
                sess[3] += 1
            elif ev.kind == "cancel_out":
                self.total_cancel_out += 1
                pair[4] += 1
                sess[4] += 1
            elif ev.kind == "cancel_in":
                self.total_cancel_in += 1
                pair[5] += 1
                sess[5] += 1
        if ev.ts > self.last_ts:
            self.last_ts = ev.ts
            cutoff = idx - self.history
            for k in [k for k in self.buckets if k < cutoff]:
                del self.buckets[k]

    def window(self, end_index: int | None = None):
        end = self.last_index if end_index is None else end_index
        start = end - self.history + 1
        return start, [self.buckets.get(i) for i in range(start, end + 1)]

    @property
    def last_index(self) -> int:
        return int(self.last_ts // self.bucket_secs)

    def per_satellite(self, start: int, end: int) -> dict[str, list[int]]:
        agg: dict[str, list[int]] = {}
        for i in range(start, end + 1):
            b = self.buckets.get(i)
            if b is None:
                continue
            for name, vals in b.sats.items():
                t = agg.setdefault(name, [0, 0, 0, 0, 0, 0])
                for j in range(6):
                    t[j] += vals[j]
        return agg
