const { app, BrowserWindow, Menu, screen } = require('electron')
const path = require('node:path')
const fs = require('node:fs')

// —— 路径：都可以用环境变量覆盖，方便别人在自己机器上跑 ——
const HOME = process.env.USERPROFILE || process.env.HOME
const LEDGER_ROOT = process.env.NAIWA_LEDGER_ROOT ||
  path.join(HOME, '.dsh', 'storages', 'session_projcache', 'sessions')
const PET_CONFIG = process.env.NAIWA_PET_CONFIG ||
  path.join(HOME, '.dsh', 'dsh-pet', 'main-config.jsonc')
const POS_FILE = path.join(__dirname, 'bubble-pos.json')

const SNAPSHOT = process.argv.includes('--snapshot')
let win = null

/** 读 DSH 的会话账本，汇总花费与 token */
function readLedger() {
  let totalCny = 0, totalTok = 0, n = 0
  let lastCny = 0, lastTok = 0, lastAt = 0
  try {
    for (const f of fs.readdirSync(LEDGER_ROOT)) {
      if (!f.endsWith('.json')) continue
      try {
        const p = path.join(LEDGER_ROOT, f)
        const j = JSON.parse(fs.readFileSync(p, 'utf8'))
        const rows = j?.record?.rows
        if (!rows) continue
        const c = rows.whalePetCost?.val?.totals || {}
        const t = rows.tokenUsage?.val?.totals || {}
        const cny = (c.peakCny || 0) + (c.offPeakCny || 0)
        const tok = ((t.uncachedInputTokens || 0) + (t.outputTokens || 0) + (t.cacheReadTokens || 0)) / 1e6
        totalCny += cny; totalTok += tok; n++
        const m = fs.statSync(p).mtimeMs
        if (m > lastAt) { lastAt = m; lastCny = cny; lastTok = tok }
      } catch { /* 坏文件跳过 */ }
    }
  } catch { /* 目录不存在 */ }
  return { lastCny, lastTok, totalCny, totalTok, n }
}

/** 从宠物实例配置里算出宠物头顶附近的位置 */
function petAnchor() {
  let size = 320, mx = 48, my = 36
  try {
    const raw = fs.readFileSync(PET_CONFIG, 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/(^|[^\\:])\/\/.*$/gm, '$1')
    const cfg = JSON.parse(raw)
    const pet = (cfg.pets || []).find(p => p.id === (process.env.NAIWA_PET_ID || 'naiwa'))
    if (pet) {
      size = pet.size || size
      mx = pet.position?.marginX ?? mx
      my = pet.position?.marginY ?? my
    }
  } catch { }
  const wa = screen.getPrimaryDisplay().workArea
  return { petTop: wa.y + wa.height - my - size, petRight: wa.x + wa.width - mx }
}

function loadPos() {
  try { return JSON.parse(fs.readFileSync(POS_FILE, 'utf8')) } catch { return null }
}
function savePos(pos) {
  try { fs.writeFileSync(POS_FILE, JSON.stringify(pos, null, 2), 'utf8') } catch { }
}

function createWindow() {
  const W = 300, H = 150
  const a = petAnchor()
  const saved = loadPos()
  const x = saved ? saved.x : Math.round(a.petRight - W + 60)
  const y = saved ? saved.y : Math.round(a.petTop - H + 26)

  win = new BrowserWindow({
    width: W, height: H, x, y,
    frame: false, transparent: true, resizable: false, movable: true,
    alwaysOnTop: true, skipTaskbar: true, hasShadow: false,
    focusable: !SNAPSHOT, show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  win.setAlwaysOnTop(true, 'screen-saver')
  win.loadFile(path.join(__dirname, 'index.html'))

  win.once('ready-to-show', () => {
    if (!SNAPSHOT) win.showInactive()
    win.webContents.send('ledger', readLedger())
  })

  win.on('moved', () => {
    const [nx, ny] = win.getPosition()
    savePos({ x: nx, y: ny })
  })

  win.webContents.on('context-menu', () => {
    Menu.buildFromTemplate([
      { label: '刷新数据', click: () => win.webContents.send('ledger', readLedger()) },
      { label: '回到宠物头顶', click: () => {
          const a2 = petAnchor()
          win.setPosition(Math.round(a2.petRight - 300 + 60), Math.round(a2.petTop - 150 + 26))
        } },
      { type: 'separator' },
      { label: '退出', click: () => app.quit() },
    ]).popup({ window: win })
  })

  setInterval(() => {
    if (win && !win.isDestroyed()) win.webContents.send('ledger', readLedger())
  }, 30000)

  if (SNAPSHOT) {
    win.webContents.once('did-finish-load', () => {
      setTimeout(async () => {
        const img = await win.webContents.capturePage()
        fs.writeFileSync(path.join(__dirname, '..', 'snapshot.png'), img.toPNG())
        console.log('snapshot saved')
        app.quit()
      }, 900)
    })
  }
}

app.disableHardwareAcceleration()
app.whenReady().then(createWindow)
app.on('window-all-closed', () => app.quit())
