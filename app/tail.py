import os
import time


class LogTail:
    def __init__(self, path: str, from_start: bool = False, poll: float = 0.25):
        self.path = path
        self._interval = poll
        self.waiting = True
        self._seek_end = not from_start
        self._fh = None
        self._ino = None
        self._buf = ""

    def poll(self) -> list[str]:
        lines: list[str] = []
        fh = self._ensure_open()
        if fh is None:
            time.sleep(self._interval)
            return lines
        while True:
            chunk = fh.readline()
            if not chunk:
                break
            self._buf += chunk
            if self._buf.endswith("\n"):
                lines.append(self._buf)
                self._buf = ""
        self._check_rotation()
        return lines

    def _ensure_open(self):
        if self._fh is not None:
            self.waiting = False
            return self._fh
        try:
            fh = open(self.path, encoding="utf-8", errors="replace")
        except OSError:
            time.sleep(self._interval)
            return None
        self._fh = fh
        self._ino = os.fstat(fh.fileno()).st_ino
        fh.seek(0, os.SEEK_END) if self._seek_end else fh.seek(0)
        self._seek_end = True
        self.waiting = False
        return fh

    def _check_rotation(self):
        try:
            st = os.stat(self.path)
        except OSError:
            self._close()
            self._seek_end = False
            return
        if st.st_ino != self._ino or st.st_size < self._fh.tell():
            self._close()
            self._seek_end = False

    def _close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None
