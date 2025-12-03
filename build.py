import subprocess

from scripts.version_manager import update_version


def build_executable():
    new_version = update_version()

    subprocess.run([
        "pyinstaller",
        "--name=VoiceScribe",
        "--windowed",
        "--icon=assets/VoiceScribe.ico",
        "--add-data", ".env:.",
        "--add-data", "utils/config.ini:.",
        "--add-data", "service/replacements.txt:.",
        "main.py"
    ])

    print(f"Executable built successfully. Version: {new_version}")
    return new_version


if __name__ == "__main__":
    build_executable()
