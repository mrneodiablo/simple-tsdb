"""Entry point so `python -m tsdb ...` starts the TCP server."""
from .service import main

if __name__ == "__main__":
    main()
