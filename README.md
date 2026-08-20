# simple-tsdb

A minimal **time-series database built from scratch in pure Python** — storage engine,
indexing, a query engine, and a TCP API — with **zero runtime dependencies**.

It started as a 6-week, 36-exercise learning journey (see [the learning story](#-the-learning-story))
and has since "graduated" into a real, importable library under `src/tsdb/`.

```python
from tsdb import TimeSeriesDB

db = TimeSeriesDB("data/")
db.write("cpu", tags={"host": "server1"}, fields={"usage": 75.5})
print(db.query("SELECT mean(usage) FROM cpu WHERE host = 'server1'"))
# -> [{'value': 75.5}]
```

## ✨ Features

- **Embedded API** — one `TimeSeriesDB` class: `write()` / `write_many()` / `query()`
- **SQL-like queries** — `SELECT <agg>(field) FROM measurement WHERE ... GROUP BY ...`
- **Storage engine** — append-only, JSON, time-partitioned files with a WAL/cache
- **Indexing** — inverted tag index + binary-search time index + bloom filters
- **Query engine** — filtering, aggregations, percentiles, time windows, group-by, rate/derivative
- **TCP layer** — length-prefixed framing, a versioned text protocol, parser, client
- **Pure standard library** — no third-party runtime deps; runs anywhere Python ≥ 3.8 does

## 📦 Requirements & Installation

- Python **3.8+** (developed on 3.13)
- No runtime dependencies

```bash
git clone <your-repo-url> simple-tsdb
cd simple-tsdb
pip install -e .          # installs the `tsdb` package from src/
```

> Prefer not to install? You can run straight from source with `PYTHONPATH=src`:
> ```bash
> PYTHONPATH=src python -c "from tsdb import TimeSeriesDB; print('ok')"
> ```

## 🚀 Quickstart

```python
from tsdb import TimeSeriesDB

# Opens (creates) an on-disk database at ./data
db = TimeSeriesDB("data/", partition_interval="1d", retention_days=30)

# Write points: measurement, tags (indexed strings), fields (any value)
db.write("cpu", tags={"host": "server1", "region": "us"}, fields={"usage": 70.0})
db.write("cpu", tags={"host": "server1", "region": "us"}, fields={"usage": 80.0})
db.write("cpu", tags={"host": "server2", "region": "eu"}, fields={"usage": 30.0})

# Bulk write
db.write_many("cpu", [
    {"tags": {"host": "server3", "region": "eu"}, "fields": {"usage": 40.0}, "timestamp": 1700000000},
])

db.measurements()                                   # -> ['cpu']
db.query("SELECT mean(usage) FROM cpu")             # -> [{'value': 55.0}]
db.query("SELECT max(usage) FROM cpu GROUP BY region")
# -> [{'region': 'eu', 'value': 40.0}, {'region': 'us', 'value': 80.0}]

db.close()                                          # or use `with TimeSeriesDB(...) as db:`
```

## 🔎 Query language

```
SELECT <agg>(<field>) FROM <measurement> [WHERE <cond> [AND <cond> ...]] [GROUP BY <tag> [, <tag> ...]]
```

- **Aggregations**: `mean`, `sum`, `count`, `min`, `max`
- **WHERE**: comparisons `=  !=  <  <=  >  >=`, combined with `AND` (string literals in `'quotes'`, numbers bare)
- **GROUP BY**: one or more tag keys
- Each result row is `{<group tag>: <value>, ..., "value": <aggregated value>}`

> Advanced operators — **percentiles**, **time windows** (`aggregateWindow`), and
> **rate/derivative** — are available through the library API (`tsdb.query`) but are not
> part of the SQL grammar above.

## 🧩 Library API (per layer)

The facade is enough for most uses, but every layer is importable on its own:

```python
from tsdb.storage import StorageManager, DataPoint          # storage engine
from tsdb.index   import TagIndex, TimeRangeIndex, BloomFilter
from tsdb.query   import (FilterEngine, aggregate_field,     # query building blocks
                          exact_percentile, WindowAggregator, GroupByEngine, rate)
from tsdb.server  import (parse_query, ExecutionEngine,      # API building blocks
                          Client, serve_connection, handle_request)
```

## 🌐 Running the TCP server

The database can also run as a networked server over its own length-prefixed wire
protocol.

**Terminal 1 — start the server:**

```bash
python -m tsdb --host 127.0.0.1 --port 8080 --data ./data
# tsdb: listening on 127.0.0.1:8080 (data → data)
```

(`--port 0` picks a free port automatically; `Ctrl-C` shuts it down cleanly.)

**Terminal 2 — talk to it with the built-in client:**

```python
import socket
from tsdb.server import Client

client = Client(socket.create_connection(("127.0.0.1", 8080)))

client.ping()                                                   # True
client.write("temp", {"room": "server"}, {"celsius": 22.5})     # True
client.write("temp", {"room": "lobby"},  {"celsius": 19.0})
client.query("SELECT mean(celsius) FROM temp GROUP BY room")
# -> [{'room': 'lobby', 'value': 19.0}, {'room': 'server', 'value': 22.5}]
```

Or embed the server in your own process:

```python
import threading
from tsdb import TSDBServer

server = TSDBServer(host="127.0.0.1", port=8080, data_path="data")
threading.Thread(target=server.serve_forever, daemon=True).start()
# ... use a Client to talk to it ...
server.stop()
```

A minimal-dependency loopback example (server thread + client round-trip) also lives
in [`labs/week4_lab.py`](labs/week4_lab.py).

## 🗂️ Project structure

```
simple-tsdb/
├── src/tsdb/                 # ← THE PRODUCT (importable library)
│   ├── __init__.py           #   exports TimeSeriesDB + TSDBServer
│   ├── database.py           #   TimeSeriesDB — embedded engine (write / query)
│   ├── service.py            #   TSDBServer — networked TCP server (wraps TimeSeriesDB)
│   ├── __main__.py           #   `python -m tsdb` → runs the server
│   ├── storage/              #   file ops, serialization, partitioning, WAL, manager
│   ├── index/                #   tag index, time index, series keys, bloom filters
│   ├── query/                #   filtering, aggregation, percentiles, windows, group-by
│   └── server/               #   protocol building blocks: framing, parser, engine, client
├── exercises/                # ← THE LEARNING MATERIAL (36 daily exercises, weeks 1–6)
├── labs/                     #   weekly end-to-end integration demos (week1_lab … week6_lab)
├── docs/                     #   architecture / design notes + capstone report
├── pyproject.toml            #   packaging (pip install -e .)
├── CURRICULUM.md             #   the 6-week plan
└── CONCEPTS.md               #   theory & concepts
```

`src/tsdb/` is what you **import and run**. `exercises/` and `labs/` are the learning
journey behind it — kept as documentation, not imported by the product.

## 🛠️ Development

Run the library quickstart to smoke-test an install:

```bash
python -c "from tsdb import TimeSeriesDB; import tempfile; \
d=TimeSeriesDB(tempfile.mkdtemp()); d.write('m',{'h':'a'},{'v':1}); \
print(d.query('SELECT sum(v) FROM m'))"
```

Run any weekly integration lab (end-to-end demonstrations):

```bash
python labs/week6_lab.py     # capstone: profile → optimize → report
python labs/week4_lab.py     # full TCP round-trip over a real loopback socket
```

Run a single learning exercise:

```bash
python exercises/week3_querying/day16_aggregations.py
```

Optional dev tools: `pip install -e ".[dev]"` (pytest, black, mypy).

## 📚 The learning story

This database was built the hard way, on purpose — implementing every core algorithm
from first principles over six weeks:

| Week | Theme | Highlights |
|------|-------|-----------|
| 1 | Storage | file I/O, line protocol, partitioning, batch writes, compression |
| 2 | Indexing | inverted tag index, binary-search time index, series cardinality, bloom filters |
| 3 | Query processing | filters, streaming aggregations, percentiles, time windows, group-by, rate |
| 4 | API layer | TCP framing, wire protocol, lexer/parser, execution engine, client, monitoring |
| 5 | Comparison | benchmark harness, write/query performance, architecture analysis vs InfluxDB |
| 6 | Production | bottleneck profiling, optimization with proof, applied recommendations, docs |

See [CURRICULUM.md](CURRICULUM.md) for the day-by-day plan and [CONCEPTS.md](CONCEPTS.md)
for the theory. Each exercise is self-contained with its own tests.

## ⚠️ Limitations

This is a **learning-grade** database, not a production one. JSON storage, in-memory
indexes, single-node, no authentication, and no crash-safe durability guarantees.
For production time-series workloads use a mature engine (e.g. InfluxDB) — the point
here is to understand how one works.

## 📄 License

MIT
