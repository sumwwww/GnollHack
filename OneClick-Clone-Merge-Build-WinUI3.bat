@echo off
chcp 65001 >nul
title GnollHack 现代 WinUI 3 简体中文版 - 一键克隆/合并汉化/自动编译工具
echo ============================================================================
echo   GnollHack 现代 Windows 10/11 (WinUI 3) 简体中文版 一键合并与编译启动器
echo ============================================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools_zh_CN\Auto-Download-Assets-And-Build.ps1" -Configuration Release
echo.
pause
