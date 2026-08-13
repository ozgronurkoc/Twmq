try:
    from importlib.metadata import version, PackageNotFoundError

    __version__ = version("spor-toto-kapsama")
except PackageNotFoundError:
    __version__ = "4.0.0"
