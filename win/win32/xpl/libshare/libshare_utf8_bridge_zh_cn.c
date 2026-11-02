/*
 * win/win32/xpl/libshare/libshare_utf8_bridge_zh_cn.c
 * GnollHack C99 原生层与 C# (.NET 10 MAUI) P/Invoke 互操作层 UTF-8 简体中文桥接封装
 * 防止 Windows 默认 ANSI 代码页 (CP1252/CP936) 在 Marshal.PtrToStringAnsi 时产生中文乱码
 */

#include <string.h>
#include "../../../../include/gnh_zh_cn.h"

#ifdef _WIN32
#include <windows.h>
#endif

/*
 * 在 libshare 回调向 C# 传递消息行 (putstr / pline / menu item) 前调用此函数，
 * 确保英文词条或动态短语转换为 UTF-8 简体中文字符串。
 */
const char *gnh_bridge_localize_utf8(const char *raw_str)
{
    if (!raw_str || !*raw_str)
        return raw_str;
    return gnh_zh_translate(raw_str);
}
