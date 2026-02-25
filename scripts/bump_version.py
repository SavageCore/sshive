import re
import subprocess
import sys
from pathlib import Path


def bump_version(new_version):
    files_to_update = [
        ("pyproject.toml", r'^version = "[^"]+"', f'version = "{new_version}"'),
        ("nfpm.yml", r'^version: "[^"]+"', f'version: "{new_version}"'),
        (
            "sshive/__init__.py",
            r'^__version__ = "[^"]+"',
            f'__version__ = "{new_version}"',
        ),
        (
            "sshive/main.py",
            r'app\.setApplicationVersion\("[^"]+"\)',
            f'app.setApplicationVersion("{new_version}")',
        ),
    ]

    for file_path, pattern, replacement in files_to_update:
        path = Path(file_path)
        if not path.exists():
            print(f"Warning: {file_path} not found")
            continue

        content = path.read_text()
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        path.write_text(new_content)
        print(f"Updated {file_path}")

    # Update uv.lock
    print("Updating uv.lock...")
    subprocess.run(["uv", "lock"], check=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <new_version>")
        sys.exit(1)

    version = sys.argv[1]
    if version.startswith("v"):
        version = version[1:]

    bump_version(version)
