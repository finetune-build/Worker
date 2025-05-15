import importlib

def load_settings():
    return importlib.import_module("ftw.settings")

settings = load_settings()
