"""MCP server that plays musical notes through the system speakers (macOS afplay)."""

import math
import os
import struct
import subprocess
import tempfile
import wave
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP("notes-player")

SEMITONES_FROM_A = {
    "C": -9, "C#": -8, "Db": -8,
    "D": -7, "D#": -6, "Eb": -6,
    "E": -5,
    "F": -4, "F#": -3, "Gb": -3,
    "G": -2, "G#": -1, "Ab": -1,
    "A": 0, "A#": 1, "Bb": 1,
    "B": 2,
}


def pitch_to_freq(pitch: str) -> float | None:
    """Convert scientific pitch notation (e.g. 'C4', 'G#5', 'Bb3') to Hz. Returns None for 'R' (rest)."""
    p = pitch.strip()
    if p.upper() == "R":
        return None
    if not p or not p[-1].isdigit():
        raise ValueError(f"invalid pitch {pitch!r}: must end with octave digit (e.g. 'C4')")
    octave = int(p[-1])
    name = p[:-1]
    name = name[0].upper() + name[1:] if len(name) > 1 else name.upper()
    if name not in SEMITONES_FROM_A:
        raise ValueError(f"invalid note name {name!r} in pitch {pitch!r}; expected C, C#/Db, D, ... B")
    semitones_from_a4 = SEMITONES_FROM_A[name] + (octave - 4) * 12
    return 440.0 * (2 ** (semitones_from_a4 / 12))


class Note(BaseModel):
    pitch: str = Field(
        description=(
            "Scientific pitch notation: letter + optional accidental (# or b) + octave digit. "
            "Examples: 'C4' (middle C), 'G#5', 'Bb3', 'A4' (440 Hz). Use 'R' for a rest."
        )
    )
    beats: float = Field(
        default=1.0,
        gt=0,
        description="Duration in beats. 1.0 = quarter, 0.5 = eighth, 2.0 = half, 4.0 = whole.",
    )


@mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
)
def play_melody(
    notes: Annotated[list[Note], Field(description="Ordered notes (or rests) to play.")],
    tempo_bpm: Annotated[
        int, Field(ge=20, le=400, description="Tempo in beats per minute (quarter-note = 1 beat).")
    ] = 120,
) -> str:
    """Play a melody (or single note) through the speakers.

    Synthesizes each note as a sine wave with a short attack/release envelope,
    writes a temporary WAV, and plays it synchronously via macOS `afplay`. Returns
    when playback finishes. To play a single note, pass a one-element list.
    """
    if not notes:
        return "no notes to play"

    sr = 44100
    beat_seconds = 60.0 / tempo_bpm
    gap_samples = int(sr * 0.02)
    silence = b"\x00\x00" * gap_samples
    frames = bytearray()

    for note in notes:
        freq = pitch_to_freq(note.pitch)
        n = int(sr * note.beats * beat_seconds)
        if freq is None:
            frames.extend(b"\x00\x00" * n)
        else:
            attack = min(2000, n // 4) or 1
            release = min(2000, n // 4) or 1
            for i in range(n):
                if i < attack:
                    env = i / attack
                elif i > n - release:
                    env = max(0.0, (n - i) / release)
                else:
                    env = 1.0
                s = 0.4 * env * math.sin(2 * math.pi * freq * i / sr)
                frames.extend(struct.pack("<h", int(s * 32767)))
        frames.extend(silence)

    fd, path = tempfile.mkstemp(suffix=".wav", prefix="notes_player_")
    os.close(fd)
    try:
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(bytes(frames))
        result = subprocess.run(["afplay", path], capture_output=True, text=True)
        if result.returncode != 0:
            return f"afplay failed (exit {result.returncode}): {result.stderr.strip()}"
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

    total_beats = sum(n.beats for n in notes)
    return f"played {len(notes)} note(s), {total_beats:g} beats at {tempo_bpm} bpm"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
