# notes-player

A tiny educational MCP server for **Claude Code**. It exposes one tool, `play_melody`, that lets the assistant play musical notes through your speakers. The whole server is ~120 lines of Python — read [`src/notes_player/server.py`](src/notes_player/server.py) to see how a complete MCP server fits together.

> **Platform:** macOS only. Playback uses the built-in `afplay` command. On Linux/Windows the tool will return an error message instead of crashing.

## Install (one command)

**Prerequisites:**
- [Claude Code](https://docs.claude.com/en/docs/claude-code) — check with `claude --version`
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — check with `uv --version`

Then run:

```bash
claude mcp add notes-player -- uvx --from git+https://github.com/hugary1995/notes-player notes-player
```

(Replace `hugary1995` with the GitHub user/org that owns this fork.)

Verify it's wired up:

```bash
claude mcp list
# notes-player: uvx --from git+... notes-player - ✓ Connected
```

That's it. `uvx` fetches the repo, builds it in a cached environment, and runs it on demand — no manual `pip install`, no virtualenv to manage.

## Try it

Start Claude Code in any directory and ask:

> Play the first line of Twinkle Twinkle Little Star.

Claude will call `play_melody` with the right notes and you'll hear it through the speakers.

Other things to try:
- *"Play an A 440."*
- *"Play a C major scale, ascending then descending, at 180 bpm."*
- *"Play the opening of Beethoven's Fifth."*

## The tool

One tool: **`play_melody(notes, tempo_bpm)`**

| Argument    | Type                              | Description |
|-------------|-----------------------------------|-------------|
| `notes`     | `list[{pitch, beats}]`            | Ordered notes (or rests) to play. |
| `tempo_bpm` | `int` (20–400, default `120`)     | Quarter-notes per minute. |

Each note has:
- `pitch` — scientific notation: `"C4"` (middle C), `"G#5"`, `"Bb3"`, or `"R"` for a rest.
- `beats` — duration relative to a quarter note: `1.0` quarter, `0.5` eighth, `2.0` half.

Claude figures out the right arguments from natural-language requests — you shouldn't need to call it by hand.

## Updating

`uvx` caches by default. To pull a newer commit, force a refresh:

```bash
uvx --reinstall --from git+https://github.com/hugary1995/notes-player notes-player --help
```

## Removing

```bash
claude mcp remove notes-player
```

## Development

If you want to hack on the server itself, clone the repo and use it from the local checkout:

```bash
git clone https://github.com/hugary1995/notes-player
cd notes-player
uv sync                    # creates .venv with mcp installed
uv run notes-player        # launches the server on stdio for manual JSON-RPC poking
```

To point Claude Code at your local copy instead of GitHub:

```bash
claude mcp add notes-player -s project -- uvx --from . notes-player
```

This writes a `.mcp.json` to the current directory that points at the local source — edit the code and re-launch Claude Code to pick up the changes.

## How it works (the short version)

1. The MCP server registers one tool via FastMCP and listens for JSON-RPC over stdio.
2. When Claude calls `play_melody`, the server converts each pitch to a frequency (A4 = 440 Hz, semitones go up by a factor of 2^(1/12)).
3. It synthesizes a sine wave per note with a short fade-in/fade-out (so notes don't click), writes a temporary WAV file, and shells out to `afplay` to play it.
4. The tool returns when playback finishes.

That's the whole thing. Look at [`server.py`](src/notes_player/server.py) — it's short on purpose.
