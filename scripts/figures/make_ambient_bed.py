#!/usr/bin/env python3
"""Generate a soft ambient chord pad for video abstracts (CC0 by construction).

Synthesizes a slow-evolving drone (root + fifth + soft third + octave
shimmer, gentle LFO breathing) and writes a 16-bit stereo WAV. No samples,
no third-party material — the license is simply ours.

  python3 scripts/figures/make_ambient_bed.py --out figures/video/<p>/media/ambient-pad.wav [--dur 16]
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SR = 44100


def pad_chord(dur: float, root_hz: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    # fixed phases — deterministic, no RNG
    voices = [
        (root_hz, 0.40, 0.0),          # root
        (root_hz * 1.5, 0.26, 0.7),    # fifth
        (root_hz * 2.0, 0.16, 1.9),    # octave
        (root_hz * 2.52, 0.07, 2.6),   # ~major sixth shimmer (detuned)
    ]
    out = np.zeros(n)
    for f, amp, ph in voices:
        # slow amplitude breathing per voice
        lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.05 * t + ph)
        out += amp * lfo * np.sin(2 * np.pi * f * t + ph)
    # gentle low-pass feel via a short moving average
    k = 24
    kernel = np.ones(k) / k
    out = np.convolve(out, kernel, mode="same")
    # normalize to -6 dBFS-ish and add slow master swell
    out /= np.max(np.abs(out)) + 1e-9
    swell = 0.6 + 0.4 * np.sin(np.pi * np.clip(t / dur, 0, 1))
    out *= swell * 0.5
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dur", type=float, default=16.0)
    ap.add_argument("--root", type=float, default=110.0, help="A2")
    args = ap.parse_args()

    mono = pad_chord(args.dur, args.root)
    # stereo: slight decorrelation via tiny delay on the right channel
    delay = int(0.011 * SR)
    right = np.concatenate([np.zeros(delay), mono[:-delay]])
    stereo = np.stack([mono, right], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {out} ({args.dur:.0f}s stereo, synthesized — CC0 by construction)")


if __name__ == "__main__":
    main()
