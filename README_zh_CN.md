# GnollHack 简体中文分模块汉化与现代 Windows (WinUI 3) 编译工程包

本工程包按照 [hyvanmielenpelit/GnollHack](https://github.com/hyvanmielenpelit/GnollHack) 官方源码目录结构建立，专门针对 **现代 Windows 10/11 版 (.NET 10 MAUI / WinUI 3)** 进行了分模块精准汉化与底层 UTF-8 / 中文语法适配。

## 一、工程目录结构（与原版游戏目录 1:1 对应）

| 文件夹 / 文件路径 | 对应原版模块 | 汉化内容与工程作用 |
| :--- | :--- | :--- |
| `include/gnh_zh_cn.h` | C99 核心头文件 | 定义 `GNH_TR` 汉化宏、UTF-8 缓冲区扩容（`BUFSZ` 256→1024）、中文冠词/复数/所有格旁路函数与双语许愿接口。 |
| `include/artilist_zh_cn.h` | `include/artilist.h` | 全 **62 件神器** 简体中文精确对照表（38 件可许愿神器、13 件职业任务神器、8 件专属不可许愿神器、3 件祈祷仪式神器）。 |
| `src/gnh_zh_cn.c` | `src/objnam.c` & `pline.c` | C99 运行时中文查找引擎，拦截英文冠词 `a/an`、禁止英文复数 `-s/-es` 破坏中文字符、将 `'s` 转为 `的`，并支持中文/英文双语许愿 (`readobjnam`)。 |
| `src/monst_role_skill_zh_cn.c` | `src/role.c`, `skill.c`, `monst.c` | 全 **13 个职业**、**5 个种族**、**3 大阵营**、**7 个难度等级**、**6 级技能熟练度**、**31 项武器/法术/武术技能**、**6 大属性与状态异常**、以及 **59 类怪物图鉴与首领** 简体中文词库。 |
| `src/objects_zh_cn.c` | `src/objects.c` | 全 **22 个装备槽位**、**品质等级**（精良/精英/天界/太初/炼狱）、**特殊材质**、**46 个神话与传奇前缀/后缀词缀**，以及全部近战/远程武器、龙鳞甲、防具、新旧药水、卷轴、魔杖、戒指、护身符、工具、食物、蘑菇、12 种法术材料、宝石矿石、魔冢艺术品与 10 类新增杂项饰品完整词库。 |
| `src/spells_zh_cn.c` | `src/spell.c` & `objects.c` | 全 **12 大法术学派** 与 **230+ 本魔法书/法术** 完整简体中文词库。 |
| `dat/dungeon_zh_cn.txt` | `dat/dungeon.def` & `*.des` | 厄运地牢、地精矿坑、推箱子迷宫、焦热地狱、元素位面及 GnollHack 新增分支（大型环形高能地牢、魔冢几何位面、地狱牧场奶牛关、泰拉斯奎巢穴、耶诺古魔域、金银宝岛等）简体中文映射（UTF-8 无 BOM）。 |
| `dat/opthelp_zh_cn.txt` | `dat/opthelp` & `defaults.gnh` | 核心游戏机制选项与现代 WinUI 3 客户端图形/音频设置说明（UTF-8 无 BOM）。 |
| `dat/rumors_oracles_zh_cn.txt` | `dat/rumors.*` & `oracles.txt` | 幸运曲奇真实传言与德尔斐神谕先知核心提示汉化（UTF-8 无 BOM）。 |
| `win/win32/xpl/GnollHackX/GnhZhCnUiStrings.cs` | 共享 C# 前端逻辑 | 兼容 `.NET Standard 2.0` 的主界面、角色创建、快捷命令栏、设置页简体中文词典，内置 SkiaSharp `Microsoft YaHei UI` 中文字体回退防乱码逻辑。 |
| `win/win32/xpl/GnollHackX/XamlTranslationDict_zh_CN.json` | `GnollHackX/Pages/*.xaml` | 共享 XAML 界面属性（`Text`/`Title`/`Placeholder`）中文映射表（在 `makedefsdroid` 同步到 `GnollHackM` 前注入）。 |
| `win/win32/xpl/GnollHackM/MauiChineseFontConfig.cs` | `.NET 10 MAUI` 宿主 | Windows 10/11 WinUI 3 客户端中文字体注册扩展。 |
| `win/win32/xpl/libshare/libshare_utf8_bridge_zh_cn.c` | C / C# P/Invoke 桥接层 | 确保原生 `gnollhackwin.dll` 向 C# 传递的 UTF-8 中文字符串不被 ANSI 代码页截断。 |
| `tools_zh_CN/apply_zh_cn_patch.py` | 自动化汉化注入器 | 一键备份原文件、扩容 `BUFSZ`、为 `.vcxproj` 注入 `/utf-8`、批量替换 C/XAML/`dat` 词条，并支持 `--extract-untranslated` 导出剩余动态句子。 |
| `tools_zh_CN/Build-GnollHack-WinUI3-zhCN.ps1` | Windows 一键编译脚本 | 自动调用 MSBuild 编译 `GnollHack.sln` (`x64`) 与 `dotnet build` 编译 `GnollHackM.csproj` (`net10.0-windows10.0.19041.0`)。 |

## 二、在 Windows 10 / 11 上合并汉化并编译运行的步骤

1. **克隆官方仓库与外部资源**：
   - 在 Windows 10/11 上安装 **Visual Studio 2026**（勾选 **使用 C++ 的桌面开发** 与 **.NET MAUI 开发**）及 **.NET 10 SDK**。
   - 克隆官方源码：`git clone https://github.com/hyvanmielenpelit/GnollHack.git`
   - 按照官方 Wiki 将图块集放入 `win\win32\tileset`，将 FMOD 音效库放入 `win\win32\bank`。
2. **覆盖本汉化工程目录**：
   - 从 Google Drive 下载本文件夹，将其中的 `include`、`src`、`dat`、`win`、`tools_zh_CN` 直接复制到本地 `GnollHack` 仓库根目录。
3. **一键注入汉化并编译现代 WinUI 3 版**：
   - 在 PowerShell 中进入仓库根目录，运行：
     ```powershell
     .\tools_zh_CN\Build-GnollHack-WinUI3-zhCN.ps1 -Configuration Release
     ```
   - 如需仅注入汉化补丁而不立即编译，可运行：
     ```powershell
     python .\tools_zh_CN\apply_zh_cn_patch.py --repo .
     ```
   - 如需还原为英文原版，可运行：
     ```powershell
     python .\tools_zh_CN\apply_zh_cn_patch.py --repo . --restore
     ```
