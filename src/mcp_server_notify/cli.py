"""Standalone CLI — the same notifications without running the MCP server.

`notify` sends one toast (and speaks it); `notify-setup` does the one-time
model download + skill install. Both reuse NotificationServer, so the MCP
tool and the CLI can never drift apart.
"""
import argparse
import logging
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from .schemas import NotificationRequest
from .server import (
    MODEL_FILES,
    MODEL_URL_BASE,
    NotificationServer,
    config_path,
    default_model_dir,
    load_config,
    save_config,
)

# plyer shows the toast on its own thread, then sleeps for `timeout` seconds
# before tearing the window down. Waiting for that would make every call take
# as long as the toast is visible, so we only give it long enough to draw.
TOAST_GRACE = 0.35


def _quiet() -> None:
    """Only surface real failures. Apprise and kokoro-onnx are chatty at INFO
    and WARNING, and none of it is the user's business on a successful toast.
    """
    logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    for noisy in ("apprise", "kokoro_onnx", "kokoro"):
        logging.getLogger(noisy).setLevel(logging.ERROR)


def _finish(speech, started: float) -> None:
    """Wait for speech (if any), let the toast draw, then leave immediately.

    plyer's balloon thread is non-daemon and sleeps for the full `timeout`
    before tearing its window down, so a normal interpreter exit would block
    that long. Windows decides how long the toast actually stays on screen, not
    us, so waiting buys nothing. os._exit skips the join.
    """
    if speech is not None:
        speech.join()
    remaining = TOAST_GRACE - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def notify() -> int:
    p = argparse.ArgumentParser(
        prog="notify",
        description="Desktop notification with an optional spoken line.",
        epilog='examples:\n  notify "Build done" "All 42 tests passed"\n'
               '  notify "Deploy" "prod is live" --agent Sisyphus\n'
               '  notify --say "hey, that one finished"\n',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("title", nargs="?", help="toast title")
    p.add_argument("message", nargs="?", default="", help="toast body")
    p.add_argument("--say", metavar="TEXT", help="speak this, no toast at all")
    p.add_argument("--speak", metavar="TEXT", help="spoken line to use instead of title+message")
    p.add_argument("--agent", metavar="NAME", help="shown as [NAME] prefix and spoken aloud")
    p.add_argument("--voice", metavar="V", help=f"Kokoro voice (default {NotificationServer.TTS_VOICE_DEFAULT})")
    p.add_argument("--no-voice", action="store_true", help="toast only, stay silent")
    p.add_argument("--no-sound", action="store_true", help="skip the notification chime")
    p.add_argument("--timeout", type=int, default=10, metavar="SEC", help="toast lifetime (default 10)")
    p.add_argument("--list-voices", action="store_true", help="print available Kokoro voices and exit")
    a = p.parse_args()

    _quiet()
    started = time.monotonic()
    if a.voice:
        os.environ[NotificationServer.TTS_VOICE_ENV] = a.voice

    if a.list_voices:
        kokoro = NotificationServer.__new__(NotificationServer)._tts
        if not kokoro:
            print("Kokoro not loaded — run notify-setup first.", file=sys.stderr)
            return 1
        print("\n".join(sorted(kokoro.get_voices())))
        return 0

    if a.say:
        # Voice-only: skip __init__ entirely, nothing but TTS is needed.
        server = NotificationServer.__new__(NotificationServer)
        speech = server._speak(NotificationRequest(title="", message="", speak=a.say, agent=a.agent))
        if speech is None:
            print("Voice is off - enable it with: notify-setup --voice yes", file=sys.stderr)
            return 1
        speech.join()
        return 0

    if not a.title:
        p.error("title is required (or use --say to only speak)")

    speech = NotificationServer()._send_notification(NotificationRequest(
        title=a.title,
        message=a.message,
        agent=a.agent,
        speak=a.speak,
        voice=not a.no_voice,
        play_sound=not a.no_sound,
        timeout=a.timeout,
    ))
    _finish(speech, started)
    return 0


def _download(name: str, dest: Path) -> None:
    url = f"{MODEL_URL_BASE}/{name}"
    total = MODEL_FILES[name]
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  {name} ({total / 1e6:.0f} MB) <- {url}")
    done = 0
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            print(f"\r    {done / 1e6:6.0f} / {total / 1e6:.0f} MB", end="", file=sys.stderr)
    print(file=sys.stderr)
    tmp.replace(dest)  # atomic — a killed download never leaves a half file in place


def _skill_targets() -> list[Path]:
    home = Path.home()
    targets = [home / ".claude" / "skills" / "notify"]
    for oc in (home / ".config" / "opencode", Path(os.environ.get("APPDATA", "")) / "opencode"):
        if oc.is_dir():
            targets.append(oc / "skills" / "notify")
    return targets


def _ask_voice() -> bool:
    """Yes/no on the voice extension. A non-interactive run keeps whatever was
    chosen before, and stays quiet on a fresh machine rather than downloading
    330 MB nobody asked for.
    """
    current = load_config().get("voice")
    if not sys.stdin.isatty():
        if current is None:
            print("Not a terminal - leaving voice off. Enable it with: notify-setup --voice yes")
        return bool(current)
    print("\nVoice is optional. Notifications can also be read out loud by a local")
    print("TTS model - fully offline, no API keys, ~330 MB one-time download.")
    prompt = "Y/n" if current is not False else "y/N"
    answer = input(f"Enable voice? [{prompt}] ").strip().lower()
    if not answer:
        return current is not False
    return answer.startswith("y")


def setup() -> int:
    p = argparse.ArgumentParser(
        prog="notify-setup",
        description="One-time setup: choose whether you want voice, install the agent skill.",
        epilog="Change your mind later by re-running: notify-setup --voice no",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--voice", choices=("yes", "no"), help="skip the prompt, set voice on or off")
    p.add_argument("--skip-skill", action="store_true", help="don't install SKILL.md for agents")
    p.add_argument("--no-test", action="store_true", help="don't fire a test notification at the end")
    a = p.parse_args()
    _quiet()

    want_voice = {"yes": True, "no": False}[a.voice] if a.voice else _ask_voice()
    print(f"\nVoice: {'on' if want_voice else 'off'}  ({save_config(voice=want_voice)})")

    if want_voice:
        model, voices = NotificationServer.tts_paths()
        print(f"Voice models -> {default_model_dir()}")
        for path in (Path(model), Path(voices)):
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_file():
                print(f"  {path.name} already there, skipping")
                continue
            if path.name not in MODEL_FILES:
                print(f"  {path.name} is a custom path - download it yourself")
                continue
            _download(path.name, path)

    if not a.skip_skill:
        src = NotificationServer._resolve_asset("SKILL.md")
        if not src:
            print("SKILL.md missing from the package - reinstall.", file=sys.stderr)
        else:
            print("Agent skill ->")
            for target in _skill_targets():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, target / "SKILL.md")
                print(f"  {target / 'SKILL.md'}")

    # Plain ASCII here on purpose: Windows consoles default to cp1252 and
    # mangle anything fancier.
    print("\nMCP server (optional - the CLI works without it):")
    print("  claude mcp add --scope user notify -- mcp-server-notify")

    if not a.no_test:
        print("\nFiring a test notification...")
        started = time.monotonic()
        speech = NotificationServer()._send_notification(NotificationRequest(
            title="Setup complete",
            message="Voice is on." if want_voice else "Toast-only, no voice.",
            speak="Setup's done. You can hear me, so the voice layer works.",
            voice=want_voice,
            timeout=5,
        ))
        _finish(speech, started)
    print('Done. Try: notify "Hello" "it works"')
    return 0
