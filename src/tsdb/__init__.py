__version__ = "1.0.0"
__author__ = "Time-Series Database Learning Project"

# Core components will be imported as they are implemented
from .storage import FileManager, DataPoint, TimeSeriesSerializer
from .index import TagIndex, SeriesManager
from .query import QueryEngine, Aggregator
from .server import TCPServer, Client

# Main database interface (will be implemented in Week 4)
# from .database import TimeSeriesDB

__all__ = [
    # Will be populated as components are implemented
    "TimeSeriesDB",
    "DataPoint",
    "FileManager",
    "TagIndex",
    "QueryEngine",
    "TCPServer",
    "Client"
]