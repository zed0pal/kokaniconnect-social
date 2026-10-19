#!/usr/bin/env python3
"""Turn a slide spec into a 9:16 Reel (MP4) with original background music.

Usage: python3 scripts/make_reel.py specs/<id>.json [--secs 4] [--mood warm] [--out media/<id>-reel.mp4]

Renders each slide at 1080x1920 in the brand theme, crossfades them, adds a
music bed from scripts/music.py, and encodes to Instagram's Reels spec
(H.264 yuv420p 30fps, AAC 48 kHz stereo 128k, moov atom at the front).
Also writes a cover image <id>-reel-cover.jpg (first slide).
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import design  # noqa: E402
import music  # noqa: E402

FADE = 0.6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--secs", type=float, default=4.0, help="seconds per slide")
    ap.add_argument("--mood", default="warm", choices=music.MOODS)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out")
    a = ap.parse_args()

    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    sid = spec["id"]
    out = Path(a.out) if a.out else ROOT / "media" / f"{sid}-reel.mp4"
    design.H = 1920  # 9:16 canvas; layout re-centres automatically
    design.SAFE_BOTTOM = 380  # Reels caption/UI overlay zone

    with tempfile.TemporaryDirectory() as tmp:
        frames = []
        for i, s in enumerate(spec["slides"], 1):
            p = Path(tmp) / f"s{i}.png"
            design.render_slide(s, 1, 1).save(p)  # total=1 → no 'Swipe' hint
            frames.append(p)
        n = len(frames)
        dur = n * a.secs - (n - 1) * FADE
        wav = Path(tmp) / "music.wav"
        music.save(str(wav), music.compose(dur, a.mood, a.seed))

        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for f in frames:
            cmd += ["-loop", "1", "-t", f"{a.secs}", "-framerate", "30", "-i", str(f)]
        cmd += ["-i", str(wav)]
        chain, last = [], "[0:v]"
        for k in range(1, n):
            lbl = f"[v{k}]"
            chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={FADE}:offset={k * (a.secs - FADE):.3f}{lbl}")
            last = lbl
        chain.append(f"{last}format=yuv420p[vout]")
        cmd += [
            "-filter_complex", ";".join(chain),
            "-map", "[vout]", "-map", f"{n}:a",
            "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "20",
            "-r", "30", "-g", "60", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-t", f"{dur:.3f}", "-movflags", "+faststart", str(out),
        ]
        subprocess.run(cmd, check=True)

        cover = out.with_name(out.stem + "-cover.jpg")
        from PIL import Image
        Image.open(frames[0]).convert("RGB").save(cover, "JPEG", quality=92)
    print(out)
    print(cover)


if __name__ == "__main__":
    main()
