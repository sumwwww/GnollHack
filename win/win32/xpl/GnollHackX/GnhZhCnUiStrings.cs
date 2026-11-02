// win/win32/xpl/GnollHackX/GnhZhCnUiStrings.cs
// GnollHack 现代客户端 (.NET MAUI / WinUI 3 与 GnollHackX 共享) 简体中文 UI 词典与 SkiaSharp 中文字体渲染辅助类
// 严格遵循官方开发规范：兼容 .NET Standard 2.0，供 GnollHackX 与 GnollHackM 共同编译使用

using System;
using System.Collections.Generic;
using SkiaSharp;

namespace GnollHackX
{
    public static class GnhZhCnUiStrings
    {
        public static bool EnableSimplifiedChinese { get; set; } = true;

        // Windows 10/11 优先使用微软雅黑 UI (Microsoft YaHei UI) 渲染 SkiaSharp 地图浮字与状态栏
        private static SKTypeface _cachedCjkTypeface;

        public static SKTypeface GetChineseTypeface(SKFontStyleWeight weight = SKFontStyleWeight.Normal)
        {
            if (_cachedCjkTypeface != null)
                return _cachedCjkTypeface;

            string[] preferredFamilies = new string[]
            {
                "Microsoft YaHei UI",
                "Microsoft YaHei",
                "SimHei",
                "DengXian",
                "Noto Sans CJK SC"
            };

            foreach (var family in preferredFamilies)
            {
                var tf = SKTypeface.FromFamilyName(family, weight, SKFontStyleWidth.Normal, SKFontStyleSlant.Upright);
                if (tf != null && tf.FamilyName != null)
                {
                    _cachedCjkTypeface = tf;
                    return _cachedCjkTypeface;
                }
            }

            _cachedCjkTypeface = SKTypeface.Default;
            return _cachedCjkTypeface;
        }

        public static readonly Dictionary<string, string> UiDictionary = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
        {
            // === 主菜单 (MainPage.xaml) ===
            { "Start Game", "开始游戏" },
            { "New Game", "新游戏" },
            { "Continue Game", "继续游戏" },
            { "Load Game", "读取存档" },
            { "Save Game", "保存并退出" },
            { "Settings", "游戏设置" },
            { "Options", "选项设置" },
            { "Top Scores", "高分殿堂" },
            { "High Scores", "排行榜" },
            { "Leaderboards", "全球排行榜" },
            { "GnollHack Account", "GnollHack 账号" },
            { "Gnoll Overseer", "豺狼人督军 AI 助手" },
            { "Guidebook", "冒险指南" },
            { "Wiki", "官方百科 (Wiki)" },
            { "Credits", "制作人员名单" },
            { "About", "关于游戏" },
            { "Exit", "退出游戏" },
            { "Quit", "退出" },
            { "Reset", "重置工具与存档修复" },

            // === 角色创建界面 (Character Creation) ===
            { "Choose Character", "创建角色" },
            { "Select Role", "选择职业 (Role)" },
            { "Select Race", "选择种族 (Race)" },
            { "Select Gender", "选择性别 (Gender)" },
            { "Select Alignment", "选择阵营 (Alignment)" },
            { "Select Difficulty", "选择难度等级 (Difficulty)" },
            { "Select Game Mode", "选择游戏模式 (Mode)" },
            { "Random", "随机选择" },
            { "Male", "男性" },
            { "Female", "女性" },
            { "Lawful", "守序" },
            { "Neutral", "中立" },
            { "Chaotic", "混乱" },
            { "Classic (Permadeath)", "经典模式（永久死亡）" },
            { "Modern (Non-Permadeath)", "现代模式（可复活续玩）" },
            { "Explore Mode", "探索模式（无限生命）" },
            { "Wizard Mode", "巫师调试模式" },

            // === 游戏主界面快捷指令栏 (GamePage.xaml Command Canvas & Action Buttons) ===
            { "Inventory", "物品栏 (i)" },
            { "Spells", "法术菜单 (+)" },
            { "Mix Spells", "调配法术 (Shift+X)" },
            { "Cast Spell", "施放法术 (Shift+Z)" },
            { "Skills", "技能加点 (Shift+S)" },
            { "Abilities", "能力与属性 (Shift+A)" },
            { "Character Details", "角色详情 (})" },
            { "Swap Weapons", "切换武器组 (x)" },
            { "Dual Weapon Mode", "双持模式 (Ctrl+X)" },
            { "Fire", "射击 (f)" },
            { "Throw", "投掷 (t)" },
            { "Apply", "使用/应用 (a)" },
            { "Eat", "食用 (e)" },
            { "Quaff", "饮用 (q)" },
            { "Read", "阅读 (r)" },
            { "Zap", "挥动魔杖 (z)" },
            { "Wear", "穿戴防具 (W)" },
            { "Take Off", "脱下防具 (T)" },
            { "Put On", "佩戴饰品 (P)" },
            { "Remove", "取下饰品 (R)" },
            { "Wield", "装备武器 (w)" },
            { "Drop", "丢弃 (d)" },
            { "Pickup", "拾取 (,)" },
            { "Loot", "翻找箱包 (Alt+L)" },
            { "Search", "搜索周围 (s)" },
            { "Rest", "原地休息 (.)" },
            { "Chat", "交谈 (c)" },
            { "Pay", "付款 (p)" },
            { "Pray", "祈祷 (Alt+P)" },
            { "Offer", "献祭 (Alt+O)" },
            { "Dip", "浸入 (Alt+D)" },
            { "Untrap", "解除陷阱 (Alt+U)" },
            { "Kick", "踢击 (k)" },
            { "Jump", "跳跃 (Alt+J)" },
            { "Ride", "骑乘" },
            { "Far Look", "远观查看 (/)" },
            { "Minimap", "小地图" },
            { "Message History", "消息记录" },

            // === 设置界面 (SettingsPage.xaml) ===
            { "Graphics", "图形与显示" },
            { "Audio", "音频与配音" },
            { "Controls", "操作与快捷键" },
            { "Gameplay", "游戏性设置" },
            { "GPU Acceleration", "GPU 硬件加速 (SKGLView)" },
            { "Windowed Mode", "窗口化模式" },
            { "Fullscreen", "全屏模式" },
            { "Master Volume", "主音量" },
            { "Music Volume", "背景音乐音量" },
            { "Effects Volume", "音效音量" },
            { "Voice Volume", "配音音量" },
            { "Subtitles", "显示语音字幕" },
            { "Metric System", "使用公制单位 (kg / m)" },
            { "Confirm", "确认" },
            { "Cancel", "取消" },
            { "Close", "关闭" },
            { "OK", "确定" },
            { "Yes", "是" },
            { "No", "否" }
        };

        public static string TranslateUi(string text)
        {
            if (!EnableSimplifiedChinese || string.IsNullOrEmpty(text))
                return text;

            if (UiDictionary.TryGetValue(text.Trim(), out string zh))
                return zh;

            return text;
        }
    }
}
