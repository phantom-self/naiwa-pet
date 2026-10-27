# -*- coding: utf-8 -*-
"""用 Real-ESRGAN 把低清片段放大 4 倍，再抠图重做

只处理「角色高度不足」的片段，避免无谓放大。
"""
import glob
import os
import shutil
import subprocess
import sys

from PIL import Image

sys.path.insert(0, r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\py")
from rembg import remove, new_session

ESR = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\esrgan\realesrgan-ncnn-vulkan.exe"
ESR_DIR = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\esrgan"
FF = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\py\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
WORK = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\work_hd"
STAGE = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\stage_hd"
V3 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid3"
V4 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid4"
V5 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid5"
V6 = r"C:\Users\j'x\AppData\Local\Temp\dsh-naiwa\vid6"

OUT_H = 720
OW = 560
FPS, CRF = 30, 26
INFER_W = 800

# 只做低清的（角色高度小的）：奶蛙舞×3、踏步舞×2、摇摆舞×3
JOBS = [
    (os.path.join(V6, "BV1Lu4y1M7EC.mp4"), 0.0, 5.0, "奶蛙-小跳蛙A"),
    (os.path.join(V6, "BV1Lu4y1M7EC.mp4"), 5.0, 10.0, "奶蛙-小跳蛙B"),
    (os.path.join(V6, "BV1Lu4y1M7EC.mp4"), 10.0, 15.0, "奶蛙-小跳蛙C"),
    (os.path.join(V6, "BV1Lu4y1M7EC.mp4"), 15.0, 20.0, "奶蛙-小跳蛙D"),
    (os.path.join(V6, "BV1Lu4y1M7EC.mp4"), 20.0, 25.0, "奶蛙-小跳蛙E"),
    (os.path.join(V6, "BV1Lu4y1M7EC.mp4"), 25.0, 30.0, "奶蛙-小跳蛙F"),
    (os.path.join(V6, "BV1YBWF6SEem.mp4"), 7.5, 11.5, "奶蛙-理发店A"),
    (os.path.join(V6, "BV1YBWF6SEem.mp4"), 44.0, 48.0, "奶蛙-理发店B"),
]

sess = new_session("u2net")


def esrgan_dir(indir, outdir):
    os.makedirs(outdir, exist_ok=True)
    subprocess.run([ESR, "-i", indir, "-o", outdir, "-n", "realesr-animevideov3",
                    "-s", "4", "-f", "png", "-t", "256", "-j", "2:2:2"],
                   cwd=ESR_DIR, capture_output=True, text=True)


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
    raw = os.path.join(WORK, name + "_raw")
    if os.path.isdir(raw):
        shutil.rmtree(raw)
    os.makedirs(raw)
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", str(start), "-to", str(end),
                    "-i", video, "-vf", f"fps={FPS}", os.path.join(raw, "f%04d.png")],
                   capture_output=True, text=True)
    n = len(glob.glob(os.path.join(raw, "*.png")))
    if not n:
        print("空", name, flush=True); return

    big = raw + "_x4"
    if os.path.isdir(big):
        shutil.rmtree(big)
    print(f"  超分 {n} 帧…", flush=True)
    esrgan_dir(raw, big)
    ups = sorted(glob.glob(os.path.join(big, "*.png")))
    if len(ups) < n:
        print(f"  超分只出 {len(ups)}/{n} 帧，用原始帧补齐", flush=True)
        ups = sorted(glob.glob(os.path.join(raw, "*.png")))

    # 量高度（超分后）
    hs = []
    for p in ups[::8]:
        bb = alpha_of(p).split()[-1].getbbox()
        if bb:
            hs.append(bb[3] - bb[1])
    ref = sorted(hs)[len(hs) // 2] if hs else OUT_H

    outdir = os.path.join(WORK, name + "_rgba")
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    target = int(OUT_H * 0.92)
    for i, p in enumerate(ups):
        rgba = alpha_of(p)
        bb = rgba.split()[-1].getbbox()
        if not bb:
            Image.new("RGBA", (OW, OUT_H), (0, 0, 0, 0)).save(os.path.join(outdir, f"f{i:04d}.png"))
            continue
        crop = rgba.crop(bb)
        s = target / max(1, bb[3] - bb[1])
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
        print("  编码失败", r.stderr[-120:], flush=True); return
    print(f"  {name}: {len(ups)}帧 {os.path.getsize(webm)//1024}KB", flush=True)


if __name__ == "__main__":
    os.makedirs(STAGE, exist_ok=True)
    sel = JOBS[int(sys.argv[1]):int(sys.argv[1])+1] if len(sys.argv) > 1 else JOBS
    for v, s, e, n in sel:
        print("处理", n, flush=True)
        build(v, s, e, n)
    print("done", flush=True)
