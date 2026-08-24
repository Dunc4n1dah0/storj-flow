# storj-flow

Terminal ASCII live chart for **Storj storagenode** logs. It tails `node.log`,
parses `downloaded` / `uploaded` piecestore events (plus errors and canceled
transfers) and renders a real-time data-flow dashboard: IN/OUT bandwidth
sparklines, per-satellite traffic, piece counts and cancel counters.

```text
node1       now    589.5 KiB/s ↓   274.0 KiB/s ↑
           peak      4.7 MiB/s ↓     4.3 MiB/s ↑
        session    416.1 MiB   ↓   273.2 MiB   ↑ ops=9912 err=0 cxl=279/32

OUT ▂▅▂▂▂▂█▂▂▂▂▂·▂▂▂▂▂▂▂▂▂▂▅▂▂▂▂▂▂▂▂·▂▃▂▂▂▂▂▂▂██▂▂▂▂▇▂▂▂▂▂▂▂▂▆▂▃
IN  ▇▂▃▂▂▂▂▂▂▂▆▂▂·▂▂·▂·█▂·▂·▂▂▂···▂▂▂·▂▂·▂·▂▂·▂···▂·▂··▂·▂·▂·▂·▂
    10:27:18                                            10:28:17

  satellite      session ↓      session ↑       window ↓       window ↑
  us1            263.3 MiB      156.1 MiB        6.2 MiB        5.1 MiB
  eu1            135.6 MiB      102.3 MiB       10.0 MiB        5.5 MiB
  ap1             17.2 MiB       14.8 MiB      249.5 KiB        0.0   B

  satellite       pieces ↓       pieces ↑       cancel ↓       cancel ↑
  us1                5,403            937            249              ·
  eu1                2,097            942             30             30
  ap1                  175             47              ·              2
```

- **now / peak / session** — current, peak and cumulative bandwidth
  (`↓` out / egress, `↑` in / ingress), plus operation, error and cancel counts
- **chart** — one column per time bucket, autoscaled, green = OUT, yellow = IN
- **satellite tables** — bandwidth per satellite (session totals + current
  window), then piece counts and canceled transfers per satellite (session)

## Requirements

- Docker **or** Python 3.10+ with `rich` (`pip install -r requirements.txt`)
- A TTY (it's an interactive terminal UI)
- Read access to the storagenode log directory

## Build (Docker)

```sh
docker build -t storj-flow .
```

## Run

One container per node; mount the node's log dir read-only and pass the
in-container log path as the first argument:

```sh
docker run --rm -it -e TERM \
  -v /mnt/disk1/storagenode1/log:/log:ro \
  storj-flow /log/node.log --title node1
```

Or without Docker:

```sh
python3 -m app /mnt/disk1/storagenode1/log/node.log --title node1
```

### Multiple nodes (docker compose)

Edit `docker-compose.yml` — one service per node with its log path — then:

```sh
docker compose run --rm node1
```

### Options

| Option | Default | Description |
|---|---|---|
| `logfile` (positional) | — | path to `node.log` to follow |
| `--title` | `storagenode` | label shown in the header |
| `--bucket-secs` | `1` | seconds per chart column |
| `--history` | `60` | columns visible (span = `bucket-secs × history`) |
| `--refresh` | `0.5` | redraw interval in seconds |
| `--from-start` | off | read the whole file instead of starting at EOF |
| `--replay FILE` | — | replay a saved log file instead of following a live one |
| `--speed` | `10` | replay acceleration factor |

Examples:

```sh
# last 10 minutes at 10-second resolution
python3 -m app /var/log/node.log --bucket-secs 10

# last hour
python3 -m app /var/log/node.log --bucket-secs 30 --history 120
```

### Replay a saved log

Any captured log file can be replayed at accelerated speed instead of
following a live file:

```sh
python3 -m app --replay /path/to/saved.log --speed 300
```

## Behavior notes

- Follows the log like `tail -f`, starting at EOF; use `--from-start` to
  include existing content. Missing file → shows "waiting" until it appears.
- Survives log rotation and truncation (reopens the file automatically).
- `ERROR` lines are counted; `download canceled` / `upload canceled` are
  counted as cancels, never as transferred traffic.
- Screen updates only rewrite changed lines (no full-panel flicker).
- Ctrl-C exits. In Docker the app handles SIGTERM, so `docker stop` is clean.
- For 24/7 viewing over SSH run it inside `tmux`/`screen` so it survives
  disconnects:
  ```sh
  tmux new -s node1 'docker run --rm -it -e TERM -v /mnt/disk1/storagenode1/log:/log:ro storj-flow /log/node.log --title node1'
  ```
- After editing `app/` rebuild the image — code is copied at build time.

## Repo layout

```
app/                 the TUI (parser, tailer, aggregation, rendering, entrypoint)
Dockerfile           python:3.12-slim + rich
docker-compose.yml   per-node service definitions
```
