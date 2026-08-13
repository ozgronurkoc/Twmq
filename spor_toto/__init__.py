from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("spor-toto-kapsama")
except PackageNotFoundError:
    __version__ = "0.0.0"
