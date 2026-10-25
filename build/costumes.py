#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""换装：色相旋转 + 贴图（礼帽 / 墨镜）

输入是一批 RGBA 帧（vid2webm.py 会在 work/<名字>_rgba 里留下），
输出是同目录下的 webm。

用法：
  python costumes.py --frames ./work/站立呼吸_rgba --out ./out --prefix 换装
"""
import argparse
import glob
import os
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def hue_shift(im: Image.Image, deg: float) -> Image.Image:
    """只旋转有彩色像素的色相（描边、白肚子不动）"""
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255.0
    rgb, alpha = a[..., :3], a[..., 3]
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    i = m & (mx == r); h[i] = ((g[i] - b[i]) / d[i]) % 6
    i = m & (mx == g); h[i] = ((b[i] - r[i]) / d[i]) + 2
    i = m & (mx == b); h[i] = ((r[i] - g[i]) / d[i]) + 4
    h = (h / 6.0 + deg / 360.0) % 1.0
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    v = mx
    ii = (h * 6).astype(np.int32)
    f = h * 6 - ii
    p = v * (1 - s); q = v * (1 - f * s); t = v * (1 - (1 - f) * s)
    out = np.zeros_like(rgb)
    for k in range(6):
        sel = (ii % 6 == k)
        if k == 0: out[sel] = np.stack([v, t, p], -1)[sel]
        elif k == 1: out[sel] = np.stack([q, v, p], -1)[sel]
        elif k == 2: out[sel] = np.stack([p, v, t], -1)[sel]
        elif k == 3: out[sel] = np.stack([p, q, v], -1)[sel]
        elif k == 4: out[sel] = np.stack([t, p, v], -1)[sel]
        else: out[sel] = np.stack([v, p, q], -1)[sel]
    res = np.concatenate([out, alpha[..., None]], axis=2)
    return Image.fromarray((np.clip(res, 0, 1) * 255).astype(np.uint8), "RGBA")


def head_anchor(im: Image.Image):
    """用 alpha 的 bbox + 顶部 1/4 带的质心，估出头部中心和头顶"""
    a = im.split()[-1]
    bb = a.getbbox()
    if not bb:
        return im.width // 2, 0, bb
    x0, y0, x1, y1 = bb
    band = a.crop((x0, y0, x1, y0 + max(4, (y1 - y0) // 4)))
    hb = band.getbbox()
    cx = x0 + (hb[0] + hb[2]) // 2 if hb else (x0 + x1) // 2
    return cx, y0, bb


def add_hat(im: Image.Image) -> Image.Image:
    im = im.copy()
    d = ImageDraw.Draw(im)
    cx, top, bb = head_anchor(im)
    hw = max(60, int((bb[2] - bb[0]) * 0.46))
    hh = int(hw * 0.42)
    brim = int(hw * 1.35)
    by = top - int(hh * 0.18)
    d.rounded_rectangle([cx - brim // 2, by + hh - 6, cx + brim // 2, by + hh + 6], radius=6, fill=(34, 40, 52, 255))
    d.rounded_rectangle([cx - hw // 2, by, cx + hw // 2, by + hh], radius=int(hh * 0.3), fill=(44, 52, 68, 255))
    d.rectangle([cx - hw // 2, by + hh - 16, cx + hw // 2, by + hh - 6], fill=(226, 88, 88, 255))
    d.rounded_rectangle([cx - hw // 2 + 8, by + 6, cx - hw // 2 + 20, by + hh - 18], radius=4, fill=(70, 80, 100, 255))
    return im


def add_glasses(im: Image.Image) -> Image.Image:
    im = im.copy()
    d = ImageDraw.Draw(im)
    cx, top, bb = head_anchor(im)
    body_h = bb[3] - bb[1]
    cy = top + int(body_h * 0.175)
    lw = max(42, int((bb[2] - bb[0]) * 0.22))
    lh = max(18, int(body_h * 0.062))
    gap = int(lw * 0.35)
    for sx in (-1, 1):
        x0 = cx + sx * (gap // 2) - lw // 2 + sx * lw // 2
        d.rounded_rectangle([x0, cy, x0 + lw, cy + lh], radius=7, fill=(18, 22, 30, 238), outline=(8, 10, 14, 255), width=3)
        d.line([x0 + 6, cy + 4, x0 + lw - 8, cy + lh - 6], fill=(70, 90, 120, 130), width=2)
    d.line([cx - gap // 2, cy + lh // 2, cx + gap // 2, cy + lh // 2], fill=(8, 10, 14, 255), width=4)
    return im


def encode(frames, out_dir, name, fps=30, crf=26):
    tmp = os.path.join(out_dir, "_" + name)
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp, exist_ok=True)
    for i, im in enumerate(frames):
        im.save(os.path.join(tmp, f"f{i:04d}.png"))
    webm = os.path.join(out_dir, name + ".webm")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(fps),
                    "-i", os.path.join(tmp, "f%04d.png"),
                    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                    "-auto-alt-ref", "0", "-b:v", "0", "-crf", str(crf),
                    "-cpu-used", "2", "-row-mt", "1", "-an",
                    "-metadata:s:v:0", "alpha_mode=1", webm], check=True)
    print(f"{name}: {len(frames)}帧 {os.path.getsize(webm)//1024}KB")
    shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, help="RGBA 帧目录（vid2webm.py 产出）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="换装")
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.frames, "f*.png")))
    if not paths:
        raise SystemExit("没找到帧：" + args.frames)
    frames = [Image.open(p).convert("RGBA") for p in paths]
    os.makedirs(args.out, exist_ok=True)

    for name, deg in [("粉色", -80), ("蓝色", 175), ("薄荷", 95)]:
        encode([hue_shift(f, deg) for f in frames], args.out, f"{args.prefix}-{name}", args.fps)
    encode([add_hat(f) for f in frames], args.out, f"{args.prefix}-礼帽", args.fps)
    encode([add_glasses(f) for f in frames], args.out, f"{args.prefix}-墨镜", args.fps)


if __name__ == "__main__":
    main()
