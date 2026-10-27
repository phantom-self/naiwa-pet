# -*- coding: utf-8 -*-
"""从多个新视频里抠出「真正不同」的动作（rembg）

每个片段：抽帧 → AI 抠图 → 统一画布（底部对齐 + 高度归一）→ 透明 webm
输出到 staging 目录，确认后再装进宠物。
"""
import glob
import os
import shutil
import subprocess
import sys

from PIL import Image

sys.path.insert(0, r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\py")
from rembg import remove, new_session

FF = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\py\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
STAGE = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\stage"
WORK = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\work_more"
OUT_H = 720
OW = 528
FPS, CRF = 30, 28
INFER_W = 640

V3 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid3"
V4 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid4"
V5 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid5"

JOBS = [
    (os.path.join(V5, "BV15fEf6kEj8.mp4"), 0.0, 3.6, "奶蛙-奶蛙舞A"),
    (os.path.join(V5, "BV15fEf6kEj8.mp4"), 3.6, 7.2, "奶蛙-奶蛙舞B"),
    (os.path.join(V5, "BV15fEf6kEj8.mp4"), 7.2, 10.9, "奶蛙-奶蛙舞C"),
    (os.path.join(V5, "BV1uSe16KEfi.mp4"), 12.0, 16.0, "奶蛙-踏步舞A"),
    (os.path.join(V5, "BV1uSe16KEfi.mp4"), 25.0, 29.0, "奶蛙-踏步舞B"),
]

sess = new_session("u2net")


def alpha_of(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    small = im.resize((INFER_W, max(2, int(h * INFER_W / w))), Image.LANCZOS)
    cut = remove(small, session=sess)
    mask = cut.split()[-1].resize((w, h), Image.LANCZOS)
    rgba = im.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def build(video, start, end, name):
    if not os.path.exists(video):
        print("缺失", video, flush=True); return
    raw = os.path.join(WORK, name + "_raw")
    if os.path.isdir(raw):
        shutil.rmtree(raw)
    os.makedirs(raw)
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(start), "-to", str(end),
                    "-i", video, "-vf", f"fps={FPS}", os.path.join(raw, "f%04d.png")],
                   capture_output=True, text=True)
    files = sorted(glob.glob(os.path.join(raw, "f*.png")))
    if not files:
        print("空片段", name, flush=True); return

    # 1) 采样量高度
    hs = []
    for p in files[::8]:
        bb = alpha_of(p).split()[-1].getbbox()
        if bb:
            hs.append(bb[3] - bb[1])
    if not hs:
        print("抠不到主体", name, flush=True); return
    ref_h = sorted(hs)[len(hs) // 2]

    # 2) 逐帧：按高度归一 → 底部对齐、水平居中
    outdir = os.path.join(WORK, name + "_rgba")
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    target_h = int(OUT_H * 0.92)
    for i, p in enumerate(files):
        rgba = alpha_of(p)
        bb = rgba.split()[-1].getbbox()
        if not bb:
            Image.new("RGBA", (OW, OUT_H), (0, 0, 0, 0)).save(os.path.join(outdir, f"f{i:04d}.png"))
            continue
        crop = rgba.crop(bb)
        s = target_h / max(1, (bb[3] - bb[1]))
        crop = crop.resize((max(2, int(crop.width * s)), max(2, int(crop.height * s))), Image.LANCZOS)
        if crop.width > OW:
            crop = crop.resize((OW, int(crop.height * OW / crop.width)), Image.LANCZOS)
        canvas = Image.new("RGBA", (OW, OUT_H), (0, 0, 0, 0))
        canvas.paste(crop, ((OW - crop.width) // 2, OUT_H - crop.height - 4), crop)
        canvas.save(os.path.join(outdir, f"f{i:04d}.png"))

    os.makedirs(STAGE, exist_ok=True)
    webm = os.path.join(STAGE, name + ".webm")
    r = subprocess.run([FF, "-y", "-loglevel", "error", "-framerate", str(FPS),
                        "-i", os.path.join(outdir, "f%04d.png"),
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                        "-auto-alt-ref", "0", "-b:v", "0", "-crf", str(CRF),
                        "-cpu-used", "2", "-row-mt", "1", "-an",
                        "-metadata:s:v:0", "alpha_mode=1", webm],
                       capture_output=True, text=True)
    if r.returncode:
        print("编码失败", name, r.stderr[-150:], flush=True); return
    print(f"  {name}: {len(files)}帧 {os.path.getsize(webm)//1024}KB", flush=True)


if __name__ == "__main__":
    os.makedirs(STAGE, exist_ok=True)
    for v, s, e, n in JOBS:
        print("处理", n, flush=True)
        build(v, s, e, n)
    print("done", flush=True)
