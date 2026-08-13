---
name: notify
description: Desktop notifications with a local voice. Pop a system toast and optionally speak it out loud through offline Kokoro TTS, so the user knows a long task finished without watching the terminal. Use when a task completes, when you need attention on something, or when the user asks to be told rather than shown.
---

# Notify

A toast on the user's desktop, optionally read aloud. Runs fully offline — no
API keys, no network, no server process.

## These are shell commands

Invoke everything below through your bash/shell tool. There is no MCP tool
named `notify` unless the user also installed the MCP server (both can coexist;
they share the same code). If your harness says "unknown tool", you tried to
call it as a tool — run it in the shell instead.

## Commands

```
notify "<title>" "<message>"                 # toast + spoken line
notify "<title>" "<message>" --agent <name>  # title renders as [name] <title>
notify "<title>" "<message>" --speak "<line>"# your own spoken line
notify "<title>" "<message>" --no-voice      # silent toast
notify --say "<line>"                        # speak only, no toast
notify --list-voices
notify-setup                                 # one-time: models + skill install
```

Useful flags: `--voice <name>` (per-call voice), `--no-sound` (skip the chime),
`--timeout <sec>` (toast lifetime, default 10).

## When to fire one

Notify when the user has plausibly looked away: a build, test run, deploy, or
long agent task just finished; you hit a question you can't answer alone; or
something failed and waiting silently wastes their time.

Do **not** notify for every step of a task you're actively working through with
them — they're already looking at the screen. One notification per finished
piece of work, not a play-by-play.

## Writing the spoken line

`--speak` is where the difference between a status page and a colleague lives.
Without it the server composes `"<agent> says: <title>. <message>"`, which is
fine but robotic. With it, say what you'd actually say out loud:

```
notify "Tests green" "35 passed in 2.5s" --agent Sisyphus \
  --speak "All thirty five tests pass. That cache bug is gone."
```

Rules that matter for speech:

- Spell numbers and versions the way they're said: "thirty five", "version two
  point one", not "35" or "v2.1" where it'd be misread.
- No URLs, file paths, hashes, or code — they sound like noise. Put those in
  the toast `message`, which is read, not spoken.
- Keep it under ~200 characters. Longer lines get truncated with an `…`.
- One or two sentences. It's a hallway remark, not a summary.

The server runs a readability filter as a backstop: if a line is mostly hex,
UUIDs, base64, paths, or long digit runs, it speaks `"<agent> says: there's
news, check your screen."` instead of vocalizing the blob.

## Agent identity

`--agent <name>` prefixes the toast title (`[Sisyphus] Build complete`) and is
spoken aloud, so the user can tell which agent is talking when several run at
once. Set `MCP_NOTIFY_DEFAULT_AGENT=<name>` to apply it to every call without
passing the flag.

## Voices

Default is `af_bella`. `notify --list-voices` prints the full set — American
and British, male and female (`af_*`, `am_*`, `bf_*`, `bm_*`). Pick per call
with `--voice`, or globally with `MCP_NOTIFY_TTS_VOICE`.

Set `MCP_NOTIFY_VOICE=false` to make the whole machine silent (toasts still
fire). A per-call `--no-voice` silences one notification; there is no flag to
force voice back on once the env disabled it, by design — if the user turned
speech off, an agent shouldn't override that.

## Install (one-time per machine)

```
pip install mcp-server-notify     # or: uv tool install mcp-server-notify
notify-setup
```

`notify-setup` downloads the Kokoro model (~330 MB, once), copies this
`SKILL.md` into `~/.claude/skills/notify/` and the opencode skills dir, and
fires a test notification so you know it works. Re-run it any time to refresh
the skill file.

To also expose this as an MCP tool, `notify-setup` prints the one-line
`claude mcp add` command at the end. The MCP tool takes the same fields
(`title`, `message`, `agent`, `speak`, `voice`, `play_sound`, `timeout`).

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Toast appears, nothing is spoken | Models not downloaded — run `notify-setup`. Speech never blocks or fails the toast. |
| `notify` command not found | The install dir isn't on PATH; `python -m mcp_server_notify.cli` won't work either — reinstall with `pip install` or `uv tool install`. |
| Toast source says a raw id, not "MCP Notify" | Windows caches toast identity; sign out and back in once. |
| Speech is cut off mid-sentence | Something killed the process early — the CLI waits for playback, a wrapper script may not. |
| Nothing at all on Windows | Focus Assist / Do Not Disturb is on, or notifications are off for this app in Windows Settings. |
