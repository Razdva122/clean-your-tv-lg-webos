#!/usr/bin/env python3
"""Prepare offline theme media; never upscale an undersized photograph.

Requires the same pinned imageio-ffmpeg package as desktop CYTV.
Writes a new media directory and a wallpaperVideo fragment for theme.json.
The author must record the original photograph's source/rights in CREDITS.txt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def prepare(source, destination, motion=False):
    import imageio_ffmpeg
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file() or source.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Choose a JPG/PNG original up to 64 MiB')
    with source.open('rb') as stream:
        signature = stream.read(8)
    if not (signature.startswith(b'\xff\xd8') or signature == b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Expected a JPG/PNG original')
    if destination.exists():
        raise ValueError('Choose a new output directory; existing media is preserved')
    frames = imageio_ffmpeg.read_frames(str(source))
    try:
        width, height = next(frames)['size']
    finally:
        frames.close()
    master_w, master_h = (4032, 2268) if motion else (3840, 2160)
    if width < master_w or height < master_h or width * height > 160_000_000:
        raise ValueError(f'Original crop must contain at least {master_w}×{master_h} real pixels')
    # A 16:9 crop must fit before downsampling; neither axis may be enlarged.
    unit = min(width // 16, height // 9)
    if unit * 16 < master_w or unit * 9 < master_h:
        raise ValueError('Original 16:9 crop is too small for native 4K')
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    def run(args):
        subprocess.run([ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-y', *args],
                       check=True, stdin=subprocess.DEVNULL, timeout=600)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.wallpaper-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        master = stage / 'master.png'
        run(['-i', str(source), '-vf', f'crop={unit*16}:{unit*9},scale={master_w}:{master_h}:flags=lanczos', '-frames:v', '1', '-threads', '2', str(master)])
        # A periodic orbit returns to the same position and velocity at the loop.
        # The movement is editorial camera motion, not observed nebula motion.
        duration, fps = (20, 24) if motion else (2, 25)
        crop = f"crop=3840:2160:x='96+80*sin(2*PI*n/{duration*fps})':y='54+40*cos(2*PI*n/{duration*fps})'" if motion else 'null'
        variants = []
        for quality, w, h, rate, limit in [('4k',3840,2160,'4M',12*1024*1024), ('1080p',1920,1080,'1200k',4*1024*1024)]:
            output = stage / f'wallpaper-{quality}.mp4'
            print(f'Encoding {quality}: {duration}s, {fps} fps', flush=True)
            run(['-loop','1','-framerate',str(fps),'-i',str(master),'-vf',f'{crop},scale={w}:{h}:flags=lanczos',
                 '-t',str(duration),'-an','-c:v','libx264','-preset','medium','-crf','19','-maxrate',rate,'-bufsize',rate,
                 '-pix_fmt','yuv420p','-profile:v','high','-level:v','5.1' if w==3840 else '4.1',
                 '-g',str(fps*2),'-threads','2','-movflags','+faststart',str(output)])
            if output.stat().st_size > limit:
                raise ValueError(f'{quality} exceeds theme media budget')
            variants.append(dict(quality=quality,path=output.name))
        poster = stage / 'wallpaper.jpg'
        for q in (2, 3, 4, 5, 7, 10):
            run(['-i',str(stage/'wallpaper-4k.mp4'),'-frames:v','1','-q:v',str(q),str(poster)])
            if poster.stat().st_size <= 2*1024*1024:
                break
        else:
            raise ValueError('Poster exceeds theme budget')
        result = dict(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceSize=[width,height],
                      cropSize=[unit*16,unit*9],motion='periodic-camera-orbit' if motion else 'still',duration=duration,fps=fps,
                      wallpaperVideo=dict(variants=variants))
        (stage/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
        master.unlink()
        # Same-filesystem rename: a failed encode never exposes partial output.
        stage.rename(destination)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('--motion', action='store_true', help='20-second subtle seamless camera orbit')
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.destination, args.motion), indent=2))
