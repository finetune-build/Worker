import sys
from pathlib import Path

# 👇 Importing from submodule explicitly to avoid shadowing issues
import importlib.util

AGENT_REGISTRY = {}

def register_agent(fn):
    AGENT_REGISTRY[fn.__name__] = fn
    return fn

def autodiscover_agents(project_root=None):
    """Recursively import all .py files in the project directory"""
    if project_root is None:
        project_root = Path.cwd()

    imported_modules = set()

    for py_file in project_root.rglob("*.py"):
        # Skip virtual environments or irrelevant files
        if "site-packages" in str(py_file) or "__pycache__" in str(py_file):
            continue
        if py_file.name.startswith("__"):
            continue
        if py_file.name == Path(__file__).name:
            continue  # skip this file itself

        rel_path = py_file.relative_to(project_root)
        module_name = ".".join(rel_path.with_suffix("").parts)

        if module_name in sys.modules:
            continue

        try:
            spec = importlib.util.spec_from_file_location(module_name, str(py_file))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                imported_modules.add(module_name)
        except Exception as e:
            print(f"[autodiscover_agents] Failed to import {py_file}: {e.__class__.__name__}: {e}")

    return imported_modules
