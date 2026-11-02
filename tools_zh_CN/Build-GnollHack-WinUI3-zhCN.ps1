# tools_zh_CN/Build-GnollHack-WinUI3-zhCN.ps1
# GnollHack 现代 Windows 10/11 版 (.NET 10 MAUI / WinUI 3) 简体中文一键汉化与双阶段编译脚本
# 遵循官方编译架构：Stage 1 (win/win32/vs/GnollHack.sln x64) -> Stage 2 (win/win32/xpl/GnollHackM/GnollHackM.csproj)

param(
    [ValidateSet("Debug", "Release")]
    [string]$Configuration = "Release",
    [switch]$SkipPatch,
    [switch]$RunXamlTranslation
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " GnollHack 简体中文现代版 (WinUI 3 / .NET 10 MAUI) 自动构建管线" -ForegroundColor Cyan
Write-Host " 仓库路径: $RepoRoot" -ForegroundColor Cyan
Write-Host " 构建配置: $Configuration | 目标平台: Windows 10/11 x64" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. 检查 MSBuild 与 .NET 10 SDK
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "未找到 vswhere.exe，请先安装 Visual Studio 2026（含 C++ 桌面开发与 .NET MAUI 工作负载）。"
}
$msbuild = & $vswhere -latest -requires Microsoft.Component.MSBuild -find "MSBuild\**\Bin\MSBuild.exe" | Select-Object -First 1
if (-not $msbuild) {
    throw "未找到 MSBuild.exe，请确认 Visual Studio 安装完整。"
}
Write-Host "[1/5] 已定位 MSBuild: $msbuild" -ForegroundColor Green

# 2. 检查图块集 (tileset) 与 FMOD 音效库 (bank) 目录
$tilesetDir = Join-Path $RepoRoot "win\win32\tileset"
$bankDir    = Join-Path $RepoRoot "win\win32\bank"
if (-not (Test-Path $tilesetDir) -or -not (Test-Path $bankDir)) {
    Write-Warning "未检测到完整外部资源目录 win\win32\tileset 或 win\win32\bank。请确认已按照官方 Wiki 部署 GnollHackTileSet 与 GnollHackSoundSet！"
}

# 3. 执行 Python 简体中文汉化补丁注入
if (-not $SkipPatch) {
    Write-Host "[2/5] 正在注入简体中文分模块词库与 UTF-8 语法旁路补丁..." -ForegroundColor Yellow
    python "$PSScriptRoot\apply_zh_cn_patch.py" --repo "$RepoRoot"
} else {
    Write-Host "[2/5] 已跳过汉化补丁注入 (--SkipPatch)" -ForegroundColor Gray
}

# 4. 第一阶段：编译原生 C99 引擎与游戏数据包 (GnollHack.sln -> gnollhackwin.dll & nhdat)
Write-Host "[3/5] 正在编译阶段 1：原生 C99 核心引擎与 nhdat 数据包 (GnollHack.sln | x64 | $Configuration)..." -ForegroundColor Yellow
& $msbuild "win/win32/vs/GnollHack.sln" /t:Rebuild /p:Configuration=$Configuration /p:Platform=x64 /m

if ($RunXamlTranslation) {
    Write-Host "[4/5] 正在运行 makedefsdroid 将 GnollHackX 汉化 XAML 同步转换至 GnollHackM..." -ForegroundColor Yellow
    & $msbuild "win/win32/vs/makedefsdroid.vcxproj" /t:Build /p:Configuration=$Configuration /p:Platform=x64
} else {
    Write-Host "[4/5] 如需同步 WSL XAML 转换，可附加 -RunXamlTranslation 参数（需开启 WSL SSH）" -ForegroundColor Gray
}

# 5. 第二阶段：编译现代 WinUI 3 (.NET 10 MAUI) 客户端
Write-Host "[5/5] 正在编译阶段 2：现代 Windows WinUI 3 客户端 (GnollHackM.csproj)..." -ForegroundColor Yellow
dotnet build "win/win32/xpl/GnollHackM/GnollHackM.csproj" -c $Configuration -f net10.0-windows10.0.19041.0

Write-Host "================================================================" -ForegroundColor Green
Write-Host " 构建完成！可在 win\win32\xpl\GnollHackM\bin\$Configuration\net10.0-windows10.0.19041.0\win-x64\ 下运行游戏。" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
