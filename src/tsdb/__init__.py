"""
Simple Time-Series Database (tsdb)
==================================

A minimal, from-scratch time-series database. The primary entry point is the
``TimeSeriesDB`` facade:

    from tsdb import TimeSeriesDB

    db = TimeSeriesDB("data/")
    db.write("cpu", tags={"host": "server1"}, fields={"usage": 75.5})
    print(db.query("SELECT mean(usage) FROM cpu WHERE host = 'server1'"))

The individual layers are also importable directly:
    from tsdb.storage import StorageManager
    from tsdb.index import TagIndex, TimeRangeIndex
    from tsdb.query import FilterEngine, WindowAggregator
    from tsdb.server import Client, parse_query
"""

__version__ = "1.0.0"

from .database import TimeSeriesDB   # embedded (in-process) database
from .service import TSDBServer      # networked TCP server wrapping TimeSeriesDB

__all__ = ["TimeSeriesDB", "TSDBServer", "__version__"]
