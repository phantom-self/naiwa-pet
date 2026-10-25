# 一键安装：奶蛙桌宠（含素材）

> 把 `pet-pack` 里的配置和动画放进 `dsh-pet` 的宠物目录，并把宠物登记进实例配置。

$ErrorActionPreference = "Stop"

$repo   = $PSScriptRoot
$dshPet = Join-Path $env:USERPROFILE ".dsh\dsh-pet"
$petDir = Join-Path $dshPet "pet"
$anim   = Join-Path $petDir "naiwa-animation"
$cfg    = Join-Path $dshPet "main-config.jsonc"

Write-Host "== 奶蛙桌宠安装 ==" -ForegroundColor Cyan
Write-Host "目标目录：$dshPet"

if (-not (Test-Path $dshPet)) {
    Write-Host "找不到 $dshPet —— 你装 dsh-pet 了吗？" -ForegroundColor Red
    exit 1
}

# 1) 备份实例配置
if (Test-Path $cfg) {
    $bak = "$cfg.bak-" + (Get-Date -Format yyyyMMdd-HHmmss)
    Copy-Item $cfg $bak
    Write-Host "已备份：$bak" -ForegroundColor DarkGray
}

# 2) 放种类配置 + 素材
New-Item -ItemType Directory -Force -Path $anim | Out-Null
Copy-Item (Join-Path $repo "pet-pack\naiwa-config.json") (Join-Path $petDir "naiwa-config.json") -Force
Copy-Item (Join-Path $repo "pet-pack\naiwa-animation\*.webm") $anim -Force
Write-Host ("素材已复制：" + (Get-ChildItem $anim -Filter *.webm).Count + " 个")

# 3) 登记宠物
if (Test-Path $cfg) {
    $raw = Get-Content $cfg -Raw -Encoding UTF8
    if ($raw -match '"naiwa"') {
        Write-Host "实例配置里已经有 naiwa，跳过" -ForegroundColor DarkGray
    } else {
        # 在 pets 数组末尾插入一项（简单文本插入，兼容带注释的 jsonc）
        $entry = @'
    {
      "name": "奶蛙",
      "id": "naiwa",
      "size": 320,
      "balanceEnabled": true,
      "whisperEnabled": false,
      "workStatusEnabled": false,
      "display": "desktop",
      "position": { "corner": "bottom-right", "marginX": 48, "marginY": 36 }
    }
'@
        $idx = $raw.LastIndexOf("]")
        if ($idx -lt 0) { Write-Host "配置格式看不懂，请手动加一项" -ForegroundColor Yellow; exit 1 }
        $before = $raw.Substring(0, $idx).TrimEnd()
        $after = $raw.Substring($idx)
        if (-not $before.EndsWith("}")) {
            Write-Host "pets 里已经有内容，但结尾不是 } ，请手动加" -ForegroundColor Yellow
        }
        $new = $before + ",`r`n" + $entry + $after
        [System.IO.File]::WriteAllText($cfg, $new, (New-Object System.Text.UTF8Encoding($false)))
        Write-Host "已把奶蛙加进 main-config.jsonc"
    }
} else {
    Write-Host "没有 main-config.jsonc，请先启动一次 dsh-pet 让它生成" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "装完了。现在重启 dsh-pet（关掉再打开），奶蛙会出现在桌面右下角。" -ForegroundColor Green

# 4) 可选：气泡
$bubble = Join-Path $repo "bubble\启动气泡.bat"
if (Test-Path $bubble) {
    Write-Host "想要账本气泡：双击 bubble\启动气泡.bat" -ForegroundColor Cyan
}
