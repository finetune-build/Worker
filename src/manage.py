import subprocess
import time
import sys

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# WATCH_PATHS = ["./"]
WATCH_PATHS = []
IGNORED_DIRS = ["__pycache__", "venv", "tests", "migrations"]


class RestartOnChangeHandler(FileSystemEventHandler):
    def __init__(self, restart_callback, debounce_time=1.0):
        super().__init__()
        self.restart_callback = restart_callback
        self.debounce_time = debounce_time
        self.last_modified = 0

    def on_any_event(self, event):
        if event.src_path.endswith(".py") and not any(
            ignored in event.src_path for ignored in IGNORED_DIRS
        ):
            now = time.time()
            if now - self.last_modified > self.debounce_time:
                print(f"[hot-reload] Detected change in: {event.src_path}")
                self.last_modified = now
                self.restart_callback()


def start_worker_subprocess():
    return subprocess.Popen(
        [sys.executable, "-m", "finetune.sse.run"]
    )


def start_celery_worker():
    return subprocess.Popen(
        ["celery", "-A", "finetune.celery.app.celery", "worker", "--loglevel=info"]
    )


def main():
    print("[startup] Starting Celery worker...")
    celery_proc = start_celery_worker()

    print("[startup] Starting worker process with hot reload...")
    worker_proc = start_worker_subprocess()

    def restart_worker():
        nonlocal worker_proc
        if worker_proc:
            print("[hot-reload] Restarting worker subprocess...")
            worker_proc.terminate()
            worker_proc.wait()
        worker_proc = start_worker_subprocess()

    observer = Observer()
    event_handler = RestartOnChangeHandler(restart_worker)
    for path in WATCH_PATHS:
        observer.schedule(event_handler, path=path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[shutdown] Cleaning up...")
        observer.stop()
        worker_proc.terminate()
        celery_proc.terminate()

    observer.join()
    print("[shutdown] Done.")


if __name__ == "__main__":
    main()
