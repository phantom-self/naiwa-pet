# 奶蛙桌宠 · naiwa-pet

> Windows 桌宠：**20 个动作 + 换装 + 悬浮账本气泡**，给 [DeepSeek Harness](https://github.com/) 的
> `dsh-pet` 用。**下载即用**，素材已经打包在里面。

![气泡](docs/screenshot.png)

---

## 30 秒装好

1. 右上角 **Code → Download ZIP**
2. 解压，**双击 `一键安装.bat`**
3. 重启 `dsh-pet`（关掉再打开）

奶蛙会出现在桌面右下角。想用账本气泡，双击 `bubble\启动气泡.bat`。

> 安装脚本会**自动备份**你的 `main-config.jsonc`，出问题能还原。

---

## 里面有什么

| 东西 | 说明 |
|---|---|
| **20 个动作** | 大笑 / 换装 / 小动作 / 闹腾 / 躺平，共 5 类 |
| **换装** | 粉色 / 蓝色 / 薄荷 / 礼帽 / 墨镜 |
| **待机** | 站着斜眼瞟，占 60%，不吵 |
| **账本气泡** | 显示本次花费 / token / 累计，30 秒刷新，零联网 |
| **制作流水线** | `build/`：视频 → 透明 webm，AI 抠图（rembg） |

---

## 素材说明（请读一下）

动作素材是从**网络公开视频**用 AI 抠图做出来的，**不是我们原创的角色**。

- 我们**不主张**任何角色形象的权利
- **禁止商用**
- 仅供学习交流；若权利人认为有问题，联系我们会立刻删除

详见 [`docs/风险声明.md`](docs/风险声明.md)。

---

## 自己加动作

```bash
pip install -r build/requirements.txt

# 视频 → 透明 webm（自动 AI 抠图 + 统一画布）
python build/rembg_build.py --video 你的视频.mp4 --start 0 --end 6 --name 新动作 --out ./out

# 做换装（粉色/蓝色/薄荷/礼帽/墨镜）
python build/costumes.py --frames ./work/新动作_rgba --out ./out
```

然后把生成的 `.webm` 丢进
`%USERPROFILE%\.dsh\dsh-pet\pet\naiwa-animation\`，
并在 `pet-pack\naiwa-config.json` 里把名字加进对应分类。

---

## 坑（都踩过）

| 坑 | 解法 |
|---|---|
| VP9 带 alpha 变黑 | `-pix_fmt yuva420p -auto-alt-ref 0` **+** `-metadata:s:v:0 alpha_mode=1` |
| 千万别从 GIF 转 | GIF 没有透明通道了，必须从 RGBA 的 PNG 序列编码 |
| 白底 + 白肚子抠不干净 | **别自己写阈值**，直接上 `rembg`（U2Net） |
| 白色底座/台子去不掉 | 同上，AI 分割会把它当背景 |
| 边缘一圈白晕 | 抠图后做「反混合」`F=(C-(1-a)·白)/a` |
| 动作切换时跳一下 | 所有动作必须**同一画布、同一地面线、同一水平中心** |
| 分类权重报错 | `sum(categories.weight) === 100 - idle - turn - move` |

---

## 许可

- 代码：MIT（见 `LICENSE`）
- 动作素材：来自网络，**不在 MIT 范围内**，禁止商用
- 宠物机制参考 `dsh-pet`（MIT），致谢
