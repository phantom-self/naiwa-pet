#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频 → 透明 webm（dsh-pet 可用）

思路：
  1. ffmpeg 抽帧
  2. 逐帧抠掉纯色背景：不能靠全局阈值（角色肚子可能也是白的），
     要从画面边界做「连通域填充」，只把和边界连通的背景去掉
  3. 全片统一裁剪框（保证动作对齐）
  4. 编码 VP9 + alpha

用法：
  python vid2webm.py --video in.mp4 --start 0.5 --end 6 --name 站立呼吸 --out ./out
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter

try:
    from scipy import ndimage
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def bg_mask(cand: np.ndarray) -> np.ndarray:
    """与边界连通的「背景候选」像素"""
    if HAVE_SCIPY:
        lab, n = ndimage.label(cand)
        if n == 0:
            return np.zeros_like(cand)
        border = np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])
        ids = np.unique(border[border > 0])
        return np.isin(lab, ids)

    # 没有 scipy：降采样 + 迭代膨胀
    h, w = cand.shape
    sc = 4
    cs = cand[::sc, ::sc].copy()
    bg = np.zeros_like(cs)
    bg[0, :] = cs[0, :]; bg[-1, :] = cs[-1, :]
    bg[:, 0] = cs[:, 0]; bg[:, -1] = cs[:, -1]
    for _ in range(800):
        prev = bg.copy()
        bg[1:, :] |= bg[:-1, :]; bg[:-1, :] |= bg[1:, :]
        bg[:, 1:] |= bg[:, :-1]; bg[:, :-1] |= bg[:, 1:]
        bg &= cs
        if np.array_equal(bg, prev):
            break
    up = np.array(Image.fromarray((bg * 255).astype(np.uint8)).resize((w, h), Image.NEAREST)) > 127
    for _ in range(5):
        up[1:, :] |= up[:-1, :]; up[:-1, :] |= up[1:, :]
        up[:, 1:] |= up[:, :-1]; up[:, :-1] |= up[:, 1:]
        up &= cand
    return up


def alpha_of(path: str):
    """抠出一帧的 alpha 和前景 bbox"""
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32) / 255.0
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)

    # 背景候选：几乎无彩色 + 够亮（可调，深色背景请改这两行）
    cand = (sat < 0.17) & (mx > 0.70)
    bg = bg_mask(cand)

    alpha = np.where(bg, 0, 255).astype(np.uint8)

    # 脚下浅色投影：底部区域里「很亮且几乎无彩色」的像素再清一次
    h = alpha.shape[0]
    pale = (mx > 0.78) & (sat < 0.40)
    pale[: int(h * 0.68), :] = False
    alpha[pale] = 0

    al = Image.fromarray(alpha, "L").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.6))
    rgba = im.convert("RGBA")
    rgba.putalpha(al)
    return rgba, rgba.split()[-1].getbbox()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--name", required=True, help="输出名（= dsh-pet 里的动画名）")
    ap.add_argument("--out", default="./out")
    ap.add_argument("--height", type=int, default=640)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=24)
    ap.add_argument("--work", default="./work")
    args = ap.parse_args()

    raw = os.path.join(args.work, args.name + "_raw")
    if os.path.isdir(raw):
        shutil.rmtree(raw)
    os.makedirs(raw, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-ss", str(args.start), "-to", str(args.end), "-i", args.video,
                    "-vf", f"fps={args.fps}", os.path.join(raw, "f%04d.png")], check=True)

    files = sorted(os.listdir(raw))
    frames, boxes = [], []
    for f in files:
        rgba, bb = alpha_of(os.path.join(raw, f))
        frames.append(rgba)
        if bb:
            boxes.append(bb)
    if not boxes:
        print("没有抠出前景，检查背景颜色 / 阈值", file=sys.stderr)
        return 1

    x0 = min(b[0] for b in boxes); y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes); y1 = max(b[3] for b in boxes)
    pad = 14
    x0 = max(0, x0 - pad); y0 = max(0, y0 - pad)
    x1 = min(frames[0].width, x1 + pad); y1 = min(frames[0].height, y1 + pad)

    s = args.height / (y1 - y0)
    ow = int((x1 - x0) * s) // 2 * 2
    oh = args.height

    rgba_dir = os.path.join(args.work, args.name + "_rgba")
    if os.path.isdir(rgba_dir):
        shutil.rmtree(rgba_dir)
    os.makedirs(rgba_dir, exist_ok=True)
    for i, fr in enumerate(frames):
        fr.crop((x0, y0, x1, y1)).resize((ow, oh), Image.LANCZOS).save(
            os.path.join(rgba_dir, f"f{i:04d}.png"))

    webm = os.path.join(args.out, args.name + ".webm")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(args.fps),
                    "-i", os.path.join(rgba_dir, "f%04d.png"),
                    "-vf", "unsharp=5:5:0.5:5:5:0.0",
                    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                    "-auto-alt-ref", "0", "-b:v", "0", "-crf", str(args.crf),
                    "-cpu-used", "2", "-row-mt", "1",
                    "-an", "-metadata:s:v:0", "alpha_mode=1", webm], check=True)

    print(f"{args.name}: {ow}x{oh} {len(frames)}帧 {os.path.getsize(webm)//1024}KB -> {webm}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
