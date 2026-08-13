<a href="https://glama.ai/mcp/servers/@Cactusinhand/mcp_server_notify"> <img width="380" height="200" src="https://glama.ai/mcp/servers/@Cactusinhand/mcp_server_notify/badge" alt="Glama badge for Notify MCP server" /> </a> [![MseeP.ai Security Assessment Badge](https://mseep.net/pr/cactusinhand-mcp-server-notify-badge.png)](https://mseep.ai/app/cactusinhand-mcp-server-notify) 

[![PyPI version](https://badge.fury.io/py/mcp-server-notify.svg)](https://badge.fury.io/py/mcp-server-notify)

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/Cactusinhand/mcp_server_notify)](https://archestra.ai/mcp-catalog/Cactusinhand__mcp_server_notify)


# 📢 MCP Notify Server (qxZap fork)

[English](README.md) | [中文](README.zh.md)

Desktop notifications for AI agents — a toast when a long task finishes, and
optionally a voice that tells you what happened, so you don't have to babysit a
terminal.

> **Fork notes (qxZap).** On top of upstream:
> - Windows toast shows **"MCP Notify"** with a real icon, not "Python".
> - Per-agent title prefix (`agent` field) so you know which agent is calling.
> - Offline voice layer — [Kokoro-82M](https://github.com/thewh1teagle/kokoro-onnx)
>   runs locally, no API keys, no network.
> - **Two ways to use it:** the MCP server, or the `notify` CLI + agent skill
>   with no server at all.

---

## 🚀 Quick start

```bash
pip install mcp-server-notify     # or: uv tool install mcp-server-notify
notify-setup                      # asks one question, installs the skill, test toast
notify "Hello" "it works"
```

`notify-setup` asks whether you want **voice**:

```
Voice is optional. Notifications can also be read out loud by a local
TTS model - fully offline, no API keys, ~330 MB one-time download.
Enable voice? [Y/n]
```

Say no and you get plain desktop notifications, nothing downloaded. Say yes and
it fetches the model once. Your answer is remembered in
`%LOCALAPPDATA%\mcp-notify\config.json` (`~/.config/mcp-notify/config.json` on
Unix) — change your mind any time:

```bash
notify-setup --voice no      # toast only from now on
notify-setup --voice yes     # voice back on (downloads the model if needed)
```

Scripted installs pass `--voice yes|no` to skip the prompt. With no answer and
no terminal to ask, setup leaves voice off rather than downloading 330 MB
unasked.

## 🎛️ Two ways to use this

Same code underneath, so behaviour is identical either way. Run both if you
like — they don't conflict.

| | **MCP server** | **CLI + skill** |
| --- | --- | --- |
| Setup | register with your MCP client | `notify-setup`, nothing to register |
| Runs | background stdio process, always on | only while a notification is being sent |
| The agent calls it via | the `send_notification` tool | a shell command |
| Best for | clients with MCP support | agents without MCP, cron jobs, shell scripts, your own tooling |

### Route A — CLI + skill (no server)

```bash
notify "Build complete" "All 42 tests passed"
notify "Deploy" "prod is live" --agent Sisyphus --speak "Prod is live, we're good."
notify --say "hey, that long one finally finished"    # speak only, no toast
notify --list-voices
```

| Flag | Meaning |
| --- | --- |
| `--agent NAME` | title renders as `[NAME] <title>`, and NAME is spoken |
| `--speak TEXT` | the spoken line, instead of one composed from title+message |
| `--say TEXT` | speak this and skip the toast entirely |
| `--voice NAME` | Kokoro voice for this call (default `af_bella`) |
| `--no-voice` | toast only, stay silent |
| `--no-sound` | skip the notification chime |
| `--timeout SEC` | how long the toast stays up (default 10) |
| `--list-voices` | print every available voice and exit |

`notify-setup` also installs a **skill** — a `SKILL.md` that teaches an agent
*when* to notify and *how* to write a line that sounds spoken rather than
logged. It lands in `~/.claude/skills/notify/` and the opencode skills dir, and
is picked up automatically the next time that client starts. Source:
[`src/mcp_server_notify/assets/SKILL.md`](src/mcp_server_notify/assets/SKILL.md)
(it lives inside the package so it ships in the wheel — a plain `pip install`
carries the skill with it).

### Route B — MCP server

One tool, `send_notification`, taking the fields in the table below.

**Claude Code**

```bash
claude mcp add --scope user notify -- mcp-server-notify
```

**opencode** — `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "notify": {
      "type": "local",
      "command": ["mcp-server-notify"],
      "enabled": true,
      "environment": { "MCP_NOTIFY_DEFAULT_AGENT": "opencode" }
    }
  }
}
```

**Claude Desktop** — `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "notify": {
      "command": "mcp-server-notify",
      "env": { "MCP_NOTIFY_DEFAULT_AGENT": "Claude" }
    }
  }
}
```

On Windows, Claude Desktop may not see your user `PATH`; if the server fails to
start, use the absolute path (`%USERPROFILE%\.local\bin\mcp-server-notify.exe`).

**Cursor** — `~/.cursor/mcp.json`, same shape as Claude Desktop.

**VSCode + Copilot** — `settings.json`:

```json
"mcp": {
  "servers": {
    "notify": { "command": "mcp-server-notify" }
  }
}
```

Then add something like *"send me a notification when the task is finished"* to
your prompt — or make it a rule so you don't retype it. In VSCode agent mode,
type `#` and pick `#send_notification`.

## 📋 Request fields

Used by both routes — the CLI flags map one-to-one onto these.

| Field | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | str | *required* | Toast title. Prefixed with `[agent]` when `agent` is set. |
| `message` | str | *required* | Toast body. Read on screen, not aloud (unless composed into the spoken line). |
| `agent` | str? | `None` | Which agent is calling. Prefixes the title, spoken aloud. |
| `speak` | str? | `None` | Your own spoken line. Wins over the auto-composed one. |
| `voice` | bool | `true` | Speak this notification at all. |
| `play_sound` | bool | `true` | Play the bundled chime. |
| `timeout` | int | `60` (CLI: `10`) | Toast lifetime in seconds. |

```json
{
  "title": "Build complete",
  "message": "All 42 tests passed.",
  "agent": "Sisyphus",
  "speak": "Hey, I'm done — that was fast."
}
```

Renders as `[Sisyphus] Build complete` and says *"Hey, I'm done — that was fast."*

## 🔧 Environment variables

| Variable | Default | Effect |
| --- | --- | --- |
| `MCP_NOTIFY_DEFAULT_AGENT` | unset | Agent prefix for calls that don't pass one. Per-call `agent` wins. |
| `MCP_NOTIFY_VOICE` | your setup answer | `false` / `0` / `no` / `off` silences the whole machine. Overrides the config file; toasts still fire. |
| `MCP_NOTIFY_TTS_VOICE` | `af_bella` | Which Kokoro voice speaks. |
| `MCP_NOTIFY_TTS_MODEL` | `<data dir>/kokoro-v0_19.onnx` | Path to the ONNX model. |
| `MCP_NOTIFY_TTS_VOICES` | `<data dir>/voices.bin` | Path to the voice pack. |

`<data dir>` is `%LOCALAPPDATA%\kokoro` on Windows, `~/.cache/kokoro` elsewhere.
Point the two path vars at an existing download if you already have one.

## 🗣️ How the voice layer behaves

Kokoro-82M runs locally through ONNX runtime (~200 MB VRAM, or CPU). The model
loads once per process and is reused; speech runs on a background thread, so a
notification never waits on audio.

- **Readability filter.** If a message is mostly hex hashes, UUIDs, base64,
  paths, or long digit runs, the spoken line collapses to *"<agent> says:
  there's news, check your screen."* rather than reading a blob out loud. It
  applies to `speak` too, as a backstop.
- **Length cap.** Spoken lines are truncated at 200 characters. Say one or two
  sentences; the detail belongs in the toast.
- **Never fatal.** Voice turned off, no model on disk, no audio device, synth
  error — speech silently no-ops and the toast still goes out. (`notify --say`
  is the exception: with nothing to show, it says voice is off and exits 1.)
- **Speed.** A toast lands in ~0.6s; with voice, ~3s, most of it the spoken
  audio itself. The model loads once per process, so the MCP server pays it on
  the first notification only.
- `notify --list-voices` prints the full set: `af_*` / `am_*` (American female
  and male), `bf_*` / `bm_*` (British), plus blends like `af`.

## 🧑‍💻 Install from source

```bash
git clone https://github.com/qxZap/mcp_server_notify.git
cd mcp_server_notify
uv tool install --editable .    # notify / notify-setup / mcp-server-notify on PATH
notify-setup
```

`--editable` means the commands run the checkout directly — edit a file and the
next run has it, no reinstall.

Run the server by hand to check it, with optional debug logging:

```bash
mcp-server-notify --debug --log-file=path/to/logfile.log
python -m mcp_server_notify        # same thing
```

Tests: `pytest tests/ -q`.

### Platform notes

- **Windows** — nothing extra; `pywin32` is a declared dependency (without it
  Apprise reports `windows:// is disabled` and only the fallback path delivers).
- **macOS** — `brew install terminal-notifier` for the Apprise path; the plyer
  fallback works without it.
- **Linux** — nothing extra.

## 🩹 Troubleshooting

| Symptom | Fix |
| --- | --- |
| Toast appears, nothing spoken | Models aren't downloaded — run `notify-setup`. |
| `notify: command not found` | Install dir isn't on `PATH`. `uv tool install` puts it in `~/.local/bin`; restart the shell. |
| Toast source shows a raw id instead of "MCP Notify" | Windows caches toast identity — sign out and back in once. |
| Nothing appears at all (Windows) | Focus Assist / Do Not Disturb, or notifications disabled for the app in Windows Settings. |
| Server crashes on startup with `'Server' object has no attribute 'list_tools'` | An `mcp` SDK 2.x got installed. This project pins `mcp<2`; reinstall in a clean env. |
| Speech cut off mid-sentence | The process died early. The CLI waits for playback; a wrapper of your own may not. |

## 🐳 Running with Docker

Currently not available due to environment compatibility issues.
If Docker containers need to trigger host notifications regardless of whether the host OS is Windows, macOS, or Linux, the solution becomes much more complex, and direct use of native notifications is usually not feasible.

Main issues:
1. OS-specific notification systems
Each operating system (Windows, macOS, Linux) has its unique notification mechanism.

2. Docker isolation
The isolation of Docker containers limits their ability to access host operating system resources directly.

3. Dependency management
Need to handle different notification libraries and dependencies for each operating system.

## 🧾 License

MIT

## 💻 Contributions

Issues and pull requests are welcome!
