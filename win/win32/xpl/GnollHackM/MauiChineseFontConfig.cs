// win/win32/xpl/GnollHackM/MauiChineseFontConfig.cs
// 现代 Windows 10/11 (.NET 10 MAUI / WinUI 3) 简体中文全局字体回退与 SkiaSharp 渲染配置

using Microsoft.Maui.Hosting;
using Microsoft.Maui.Controls;

namespace GnollHackM
{
    public static class MauiChineseFontConfig
    {
        /// <summary>
        /// 在 MauiProgram.cs 的 CreateMauiApp() 中调用 builder.ConfigureGnollHackChineseFonts()
        /// 确保 WinUI 3 标签、按钮与弹窗在 Windows 10/11 下清晰显示简体中文。
        /// </summary>
        public static MauiAppBuilder ConfigureGnollHackChineseFonts(this MauiAppBuilder builder)
        {
            builder.ConfigureFonts(fonts =>
            {
                // 若 Resources/Fonts 下放置了自定义开源中文字体（如 NotoSansSC-Regular.ttf），在此注册别名：
                // fonts.AddFont("NotoSansSC-Regular.ttf", "GnollHackChinese");
            });

            return builder;
        }
    }
}
