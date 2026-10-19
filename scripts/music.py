#!/usr/bin/env python3
"""Compose a short, soft, original instrumental bed (no samples, no third-party
audio) so Reels carry zero copyright risk.

Usage: python3 scripts/music.py OUT.wav SECONDS [--mood warm|uplifting] [--seed N]

Warm pad chords + a gentle plucked arpeggio in a pentatonic scale, light reverb,
fade in/out. 48 kHz stereo 16-bit WAV (Instagram's maximum sample rate).
"""
import argparse
import wave
import numpy as np

SR = 48000
MOODS = {
    # key root (Hz), chord progression as semitone offsets from root, tempo
    "warm": dict(root=146.83, prog=[[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]], bpm=76),
    "uplifting": dict(root=164.81, prog=[[0, 4, 7], [-5, -1, 2], [-3, 0, 4], [-7, -3, 0]], bpm=88),
}
PENTA = [0, 2, 4, 7, 9, 12, 14, 16]


def hz(root, semis):
    return root * 2 ** (semis / 12)


def env(n, a, r):
    e = np.ones(n)
    a, r = int(a * SR), int(r * SR)
    e[:a] = np.linspace(0, 1, a)
    e[-r:] *= np.linspace(1, 0, r)
    return e


def pad(freqs, dur):
    t = np.arange(int(dur * SR)) / SR
    s = sum(np.sin(2 * np.pi * f * d * t) for f in freqs for d in (0.997, 1.0, 1.003))
    s += 0.3 * sum(np.sin(2 * np.pi * f / 2 * t) for f in freqs[:1])  # soft bass
    return s / (len(freqs) * 3) * env(len(t), 0.8, 0.9)


def pluck(f, dur):
    t = np.arange(int(dur * SR)) / SR
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return tone * np.exp(-t * 3.2) * env(len(t), 0.005, 0.05)


def reverb(x, secs=1.4, mix=0.28, rng=None):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 4.0)
    ir /= np.abs(ir).sum() / 8
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return (1 - mix) * x + mix * wet


def compose(seconds, mood="warm", seed=7):
    m, rng = MOODS[mood], np.random.default_rng(seed)
    beat = 60 / m["bpm"]
    bar = 4 * beat
    total = int((seconds + 2) * SR)
    mix = np.zeros(total)
    tpos, i = 0.0, 0
    while tpos < seconds + 1:
        chord = m["prog"][i % len(m["prog"])]
        seg = pad([hz(m["root"], c) for c in chord], bar + 0.9)
        s = int(tpos * SR)
        mix[s : s + len(seg)] += 0.55 * seg[: max(0, total - s)]
        # arpeggio: eighth notes, notes drawn from pentatonic above the chord root
        for k in range(8):
            if rng.random() < 0.25 and k % 2:  # leave some space
                continue
            note = chord[0] + 12 + PENTA[(k * 2 + i + rng.integers(0, 3)) % len(PENTA)]
            p = pluck(hz(m["root"], note), 1.6)
            ps = int((tpos + k * beat / 2) * SR)
            mix[ps : ps + len(p)] += 0.22 * p[: max(0, total - ps)]
        tpos += bar
        i += 1
    mix = mix[: int(seconds * SR)]
    # gentle low-pass (one-pole) to keep it soft behind the visuals
    a, y, out = 0.18, 0.0, np.empty_like(mix)
    for j, v in enumerate(mix):
        y += a * (v - y)
        out[j] = y
    out = reverb(out, rng=rng)
    out *= env(len(out), 1.0, 2.0)
    out /= np.abs(out).max() + 1e-9
    out *= 10 ** (-6 / 20)  # peak −6 dBFS: present but gentle
    left = out
    right = np.roll(out, int(0.012 * SR))  # subtle stereo width
    return np.stack([left, right], axis=1)


def save(path, stereo):
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("seconds", type=float)
    ap.add_argument("--mood", default="warm", choices=MOODS)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    save(a.out, compose(a.seconds, a.mood, a.seed))
    print(a.out)
