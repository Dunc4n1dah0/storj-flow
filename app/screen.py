class DiffScreen:
    def __init__(self, console):
        self.console = console
        self.prev: list[str] = []
        self.width: int | None = None

    def draw(self, renderable) -> None:
        w = self.console.width
        with self.console.capture() as cap:
            self.console.print(renderable, width=w)
        frame = cap.get().splitlines()
        while frame and not frame[-1]:
            frame.pop()
        if self.width != w:
            self.prev = []
            self.width = w
        out = []
        if not self.prev:
            out.append("\x1b[?25l")
            for line in frame:
                out.append(line + "\x1b[K\r\n")
        else:
            out.append(f"\x1b[{len(self.prev)}A\r")
            for i, line in enumerate(frame):
                if i >= len(self.prev) or line != self.prev[i]:
                    out.append(line + "\x1b[K")
                out.append("\r\n")
            extra = len(self.prev) - len(frame)
            if extra > 0:
                out.append("\x1b[2K\r\n" * extra)
                out.append(f"\x1b[{extra}A")
        self.console.file.write("".join(out))
        self.console.file.flush()
        self.prev = frame

    def close(self):
        self.console.file.write("\x1b[?25h")
        self.console.file.flush()
