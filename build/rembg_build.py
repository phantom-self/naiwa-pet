# -*- coding: utf-8 -*-
"""用 rembg（U2Net）把视频做成透明动作 webm —— 推荐用这个，比阈值抠图干净得多

为什么用 rembg：
  纯色阈值抠图碰到「白色台子」「白底 + 白肚子」就会翻车；U2Net 是 AI 分割，
  会把台子/背景一起当背景，边缘也不会泛白。

用法：
  pip install -r requirements.txt
  python rembg_build.py --video in.mp4 --start 0.5 --end 6 --name idle --out ./out

第一次运行会自动下载 u2net.onnx（约 168MB）到 ~/.u2net/
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

from PIL import Image

from rembg import remove, new_session

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"


def alpha_of(path, sess, infer_w=640):
    """AI 抠图：小图推理 → mask 放大回原尺寸 → 贴回原图"""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    small = im.resize((infer_w, max(2, int(h * infer_w / w))), Image.LANCZOS)
    cut = remove(small, session=sess)
    mask = cut.split()[-1].resize((w, h), Image.LANCZOS)
    rgba = im.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--start", type=float, required=True)
    ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", default="./out")
    ap.add_argument("--work", default="./work")
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=28)
    ap.add_argument("--model", default="u2net")
    args = ap.parse_args()

    raw = os.path.join(args.work, args.name + "_raw")
    if os.path.isdir(raw):
        shutil.rmtree(raw)
    os.makedirs(raw, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    subprocess.run([FFMPEG, "-y", "-loglevel", "error",
                    "-ss", str(args.start), "-to", str(args.end), "-i", args.video,
                    "-vf", f"fps={args.fps}", os.path.join(raw, "f%04d.png")], check=True)

    files = sorted(glob.glob(os.path.join(raw, "f*.png")))
    if not files:
        sys.exit("没抽到帧")

    sess = new_session(args.model)

    # 1) 先量全局包围盒 —— 所有动作同一画布，切换才不会跳
    boxes = []
    for p in files[::6]:
        bb = alpha_of(p, sess).split()[-1].getbbox()
        if bb:
            boxes.append(bb)
    cw = max(b[2] - b[0] for b in boxes)
    ch = max(b[3] - b[1] for b in boxes)

    s = args.height / ch
    ow, oh = int(cw * s) // 2 * 2, args.height

    # 2) 逐帧抠图 → 统一画布（底部对齐 + 水平居中）
    frames_dir = os.path.join(args.work, args.name + "_rgba")
    if os.path.isdir(frames_dir):
        shutil.rmtree(frames_dir)
    os.makedirs(frames_dir)
    for i, p in enumerate(files):
        rgba = alpha_of(p, sess)
        bb = rgba.split()[-1].getbbox() or (0, 0, rgba.width, rgba.height)
        crop = rgba.crop(bb)
        crop = crop.resize((max(2, int(crop.width * s)), max(2, int(crop.height * s))), Image.LANCZOS)
        canvas = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
        canvas.paste(crop, ((ow - crop.width) // 2, oh - crop.height - 4), crop)
        canvas.save(os.path.join(frames_dir, f"f{i:04d}.png"))

    # 3) VP9 + alpha 编码
    webm = os.path.join(args.out, args.name + ".webm")
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(args.fps),
                    "-i", os.path.join(frames_dir, "f%04d.png"),
                    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                    "-auto-alt-ref", "0", "-b:v", "0", "-crf", str(args.crf),
                    "-cpu-used", "2", "-row-mt", "1", "-an",
                    "-metadata:s:v:0", "alpha_mode=1", webm], check=True)

    print(f"{args.name}: {ow}x{oh} {len(files)}帧 {os.path.getsize(webm)//1024}KB")


if __name__ == "__main__":
    main()
