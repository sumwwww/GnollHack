using System;
namespace GnollHackX
{
    internal static partial class GnhDisplayLocalization
    {
        public static string Translate(string text)
        {
            if (text == null) return null;
            return Words.TryGetValue(text, out var translated) ? translated : text;
        }
        public static void TranslateStyled(ref string text, ref byte[] attrs, ref byte[] colors)
        {
            string translated = Translate(text);
            if (translated == text) return;
            attrs = ResizeStyle(attrs, translated.Length);
            colors = ResizeStyle(colors, translated.Length);
            text = translated;
        }
        private static byte[] ResizeStyle(byte[] source, int length)
        {
            if (source == null) return null;
            var result = new byte[length + 1];
            // A dictionary match represents a whole label. Preserve its leading style.
            byte style = source.Length > 1 ? source[0] : (byte)0;
            for (int i = 0; i < length; i++) result[i] = style;
            return result;
        }
    }
}
