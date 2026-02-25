import os
import subprocess
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class RestartHandler(FileSystemEventHandler):
    def __init__(self, run_command, env=None):
        self.run_command = run_command
        self.env = env
        self.process = None
        self.start_app()

    def start_app(self):
        if self.process:
            print("Stopping application...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        print(f"Starting application: {' '.join(self.run_command)}")
        self.process = subprocess.Popen(self.run_command, env=self.env)

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(".py"):
            print(f"File changed: {event.src_path}. Restarting...")
            self.start_app()


if __name__ == "__main__":
    path = "sshive"
    # Using 'sshive' console script
    # Use python -m with PYTHONPATH=. to ensure local source is used and bypass caching
    command = [sys.executable, "-m", "sshive.main"]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    print(f"Watching directory '{path}' for changes...")
    event_handler = RestartHandler(command, env=env)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
