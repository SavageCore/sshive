import os
import subprocess
import sys

from watchfiles import PythonFilter, watch

PATH = "sshive"
COMMAND = [sys.executable, "-m", "sshive.main"]
POLL_TIMEOUT_MS = 1_000


def start_app(env):
    print(f"Starting application: {' '.join(COMMAND)}")
    return subprocess.Popen(COMMAND, env=env)


def stop_app(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."

    process = start_app(env)
    print(f"Watching '{PATH}' for changes...")

    try:
        for changes in watch(
            PATH,
            watch_filter=PythonFilter(),
            yield_on_timeout=True,
            rust_timeout=POLL_TIMEOUT_MS,
        ):
            if process.poll() is not None:
                print("Application exited, stopping watcher.")
                return
            if not changes:
                continue
            print(f"Changes detected: {changes}. Restarting...")
            stop_app(process)
            process = start_app(env)
    except KeyboardInterrupt:
        pass
    finally:
        stop_app(process)


if __name__ == "__main__":
    main()
