# tools_zh_CN/Auto-Download-Assets-And-Build.ps1
# 全自动克隆 GnollHack 仓库、下载官方图块集与音效包、合并简体中文汉化并编译现代 WinUI 3 独立运行版

param(
    [string]$TargetDir = (Join-Path (Get-Location) "GnollHack_Build_Workspace"),
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release"
)

$ErrorActionPreference = "Stop"
$PatchPackRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " GnollHack 现代 WinUI 3 简体中文版 全自动下载 + 合并 + 编译工具" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $PatchPackRoot "win\win32\vs\GnollHack.sln"))) {
    if (-not (Test-Path $TargetDir)) {
        Write-Host "[1/6] 正在从 GitHub 克隆 hyvanmielenpelit/GnollHack 官方仓库..." -ForegroundColor Yellow
        git clone --depth 1 https://github.com/hyvanmielenpelit/GnollHack.git "$TargetDir"
    }
    Write-Host "[2/6] 正在将简体中文分模块汉化文件合并至仓库目录..." -ForegroundColor Yellow
    foreach ($sub in @("include", "src", "dat", "win", "tools_zh_CN", ".github")) {
        $srcPath = Join-Path $PatchPackRoot $sub
        if (Test-Path $srcPath) {
            New-Item -ItemType Directory -Force -Path (Join-Path $TargetDir $sub) | Out-Null
            Copy-Item -Path "$srcPath\*" -Destination (Join-Path $TargetDir $sub) -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    $RepoRoot = Resolve-Path $TargetDir
} else {
    $RepoRoot = $PatchPackRoot
}

Set-Location $RepoRoot

$tilesetDir = Join-Path $RepoRoot "win\win32\tileset"
$bankDir    = Join-Path $RepoRoot "win\win32\bank"
New-Item -ItemType Directory -Force -Path $tilesetDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bankDir "Desktop") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $bankDir "Mobile") | Out-Null

if (-not (Test-Path (Join-Path $tilesetDir "gnollhack_64x96_transparent_32bits.png"))) {
    Write-Host "[3/6] 正在自动下载 GnollHackTileSet 官方图块资源..." -ForegroundColor Yellow
    try {
        $tileRel = Invoke-RestMethod -Uri "https://api.github.com/repos/hyvanmielenpelit/GnollHackTileSet/releases/latest"
        foreach ($asset in $tileRel.assets) {
            $outFile = Join-Path $tilesetDir $asset.name
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $outFile
            if ($asset.name -match "\.zip$") {
                Expand-Archive -Path $outFile -DestinationPath $tilesetDir -Force
            }
        }
    } catch {
        Write-Warning "自动下载图块集失败，请手动从 https://github.com/hyvanmielenpelit/GnollHackTileSet/releases 下载并放入 win\win32\tileset"
    }
}

if (-not (Test-Path (Join-Path $bankDir "Desktop\Master.bank"))) {
    Write-Host "[4/6] 正在自动下载 GnollHackSoundSet 官方 FMOD 音效包..." -ForegroundColor Yellow
    try {
        $soundRel = Invoke-RestMethod -Uri "https://api.github.com/repos/hyvanmielenpelit/GnollHackSoundSet/releases/latest"
        foreach ($asset in $soundRel.assets) {
            $outFile = Join-Path $bankDir $asset.name
            Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $outFile
            if ($asset.name -match "\.zip$") {
                Expand-Archive -Path $outFile -DestinationPath $bankDir -Force
            } elseif ($asset.name -match "\.bank$") {
                Copy-Item $outFile (Join-Path $bankDir "Desktop") -Force
                Copy-Item $outFile (Join-Path $bankDir "Mobile") -Force
            }
        }
    } catch {
        Write-Warning "自动下载音效库失败，请手动从 https://github.com/hyvanmielenpelit/GnollHackSoundSet/releases 下载并放入 win\win32\bank"
    }
}

Write-Host "[5/6] 正在执行简体中文源码注入与双阶段编译..." -ForegroundColor Yellow
& (Join-Path $RepoRoot "tools_zh_CN\Build-GnollHack-WinUI3-zhCN.ps1") -Configuration $Configuration

Write-Host "[6/6] 正在打包免安装独立运行目录 (Self-Contained WinUI 3)..." -ForegroundColor Yellow
$OutPublish = Join-Path $RepoRoot "GnollHack_WinUI3_zhCN_Playable"
dotnet publish "win/win32/xpl/GnollHackM/GnollHackM.csproj" -c $Configuration -f net10.0-windows10.0.19041.0 -p:WindowsPackageType=None -p:SelfContained=true -o "$OutPublish"

Write-Host "================================================================" -ForegroundColor Green
Write-Host " 全部完成！可直接运行的游戏文件已生成至：" -ForegroundColor Green
Write-Host " $OutPublish" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
