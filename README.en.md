# naiwa-pet

A desktop pet pack for **DeepSeek Harness / [`dsh-pet`](https://github.com/)**: smooth **video-keyed** animations, **costumes**, and a **floating cost bubble**.

> **This repository ships NO character assets.**
> The character likeness ("奶蛙 / naiwa") originates from the internet and is derived from
> the copyrighted animated character 「奶龙」. It is **not** owned by this project.
> You must supply your own footage and use it at your own risk. **No commercial use.**
> See [`docs/风险声明.md`](docs/风险声明.md) (Chinese).

## Features

- **20 animations** in 5 weighted categories: laughing / costumes / idle / playful / lying-down
- **Costumes**: pink / blue / mint (hue rotation) · top hat / sunglasses (aligned per-frame to the head)
- **Real footage**: VP9 + alpha `.webm`, 30 fps, keyed from video — not a stretched still image
- **Cost bubble**: Electron + CSS floating bubble, reads local DSH ledger, refreshes every 30 s, fully offline

## Quick start

1. Copy `pet-pack/naiwa-config.json` to `%USERPROFILE%\.dsh\dsh-pet\pet\naiwa-config.json`
   > ⚠️ It **must** live in the `pet\` subfolder. Putting it in the `dsh-pet\` root does nothing.
2. Put your own `.webm` clips in `%USERPROFILE%\.dsh\dsh-pet\pet\naiwa-animation\`
   > ⚠️ Directly in that folder — **no** extra `webm\` level.
3. Add the pet entry to `%USERPROFILE%\.dsh\dsh-pet\main-config.jsonc`:

```json
{
  "name": "naiwa",
  "id": "naiwa",
  "size": 320,
  "balanceEnabled": true,
  "whisperEnabled": false,
  "workStatusEnabled": false,
  "display": "desktop",
  "position": { "corner": "bottom-right", "marginX": 48, "marginY": 36 }
}
```

4. Restart `dsh-pet`.

## Build your own animations

```bash
pip install -r build/requirements.txt

# video -> transparent webm
python build/vid2webm.py --video input.mp4 --start 0.5 --end 6.0 --name idle --out ./out

# costumes from the generated RGBA frames
python build/costumes.py --frames ./work/idle_rgba --out ./out
```

Source footage should have a **flat, light background**. Busy scenes (rooms, streets, space)
produce dirty keyed edges.

## Gotchas we already hit

| Gotcha | Fix |
|---|---|
| VP9 alpha turns black | `-pix_fmt yuva420p -auto-alt-ref 0` **plus** `-metadata:s:v:0 alpha_mode=1` |
| Never convert from GIF | GIF already destroyed the alpha — encode from RGBA PNG sequences |
| White belly on white background | Don't threshold globally; flood from the borders (connected component) |
| Accessories drift off the head | Locate the head per frame via the alpha bbox + centroid of the top quarter |
| Hue rotation stains the belly | Only rotate pixels that actually have chroma (`max-min > 0`) |
| Category weights rejected | `sum(categories.weight) === 100 - idle - turn - move` |

## License

- Code: **MIT** (see `LICENSE`)
- Pet-pack mechanism inspired by `dsh-pet` (MIT) — credit given
- **Character assets are NOT covered by this license**
