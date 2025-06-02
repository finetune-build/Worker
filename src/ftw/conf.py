import importlib

def load_settings():
    return importlib.import_module("ftw.settings")

settings = load_settings()

print("Settings")
print(f"DJANGO_HOST: {settings.DJANGO_HOST}")
print(f"WORKER_HOST: {settings.WORKER_HOST}")
print(f"WORKER_ID: {settings.WORKER_ID}")
print(f"SESSION_UUID: {str(settings.SESSION_UUID)}")
print(f"PROCESS_ID: {settings.PROCESS_ID}")