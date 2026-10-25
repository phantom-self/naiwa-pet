# 账本气泡

一个 300×150 的悬浮气泡，贴在桌宠头顶，显示：

- **本次会话**花了多少钱（大字）
- 多少 M token · 累计花了多少

30 秒刷新一次，**读本地文件，零联网、零 token**。

## 跑起来

```powershell
# 方式 1：装了全局 electron
npm start

# 方式 2：用 dsh-pet 自带的 electron
$env:ELECTRON_BIN="$env:USERPROFILE\.dsh\electron\electron.exe"
双击 启动气泡.bat
```

> ⚠️ 如果直接跑 `electron .` 报 `Cannot find module 'electron'`，
> 说明环境变量里有 `ELECTRON_RUN_AS_NODE`，**先清掉它**（`.bat` 里已经处理了）。

## 数据从哪来

| 数据 | 来源 |
|---|---|
| 花费 / token | `%USERPROFILE%\.dsh\storages\session_projcache\sessions\*.json` |
| 宠物位置 | `%USERPROFILE%\.dsh\dsh-pet\main-config.jsonc` 里的 `pets[]` |

都可以用环境变量覆盖：

```powershell
$env:NAIWA_LEDGER_ROOT="D:\自定义\sessions"
$env:NAIWA_PET_CONFIG="D:\自定义\main-config.jsonc"
$env:NAIWA_PET_ID="naiwa"
```

## 操作

| 操作 | 效果 |
|---|---|
| **拖动** | 移动位置，自动记住（`bubble-pos.json`） |
| **右键** | 刷新数据 / 回到宠物头顶 / 退出 |
| **双击** | （未绑定） |

## 只看一眼效果

```powershell
npm run snapshot   # 生成 ../snapshot.png
```
