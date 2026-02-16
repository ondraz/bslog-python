"""bslog - CLI tool for querying Better Stack logs via ClickHouse SQL."""

from dotenv import load_dotenv

from bslog._version import __version__

__all__ = ["__version__"]

load_dotenv()
