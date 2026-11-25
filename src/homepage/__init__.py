"""The landing page and status board of a small home server."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("homepage")
except PackageNotFoundError:  # run from a source tree without installing it
    __version__ = "0.0.0"
