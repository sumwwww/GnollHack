using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
namespace GnollHackX
{
    internal static partial class GnhDisplayLocalization
    {
        private sealed class MessageRule
        {
            private static readonly Regex PrintfToken = new Regex(
                @"%(?:%|(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hljztL])?[diuoxXfFeEgGaAcspn])",
                RegexOptions.CultureInvariant);

            private readonly Regex _pattern;
            private readonly string _translation;

            public string Sentinel { get; }
            public int LiteralLength { get; }
            public int PlaceholderCount { get; }
            public int TypeSpecificity { get; }

            public MessageRule(string pattern, string translation, string sentinel, int literalLength, int placeholderCount, int typeSpecificity)
            {
                _pattern = new Regex(pattern, RegexOptions.IgnoreCase | RegexOptions.CultureInvariant, TimeSpan.FromMilliseconds(100));
                _translation = translation;
                Sentinel = sentinel;
                LiteralLength = literalLength;
                PlaceholderCount = placeholderCount;
                TypeSpecificity = typeSpecificity;
            }

            public bool TryTranslate(string text, out string translated)
            {
                Match match = _pattern.Match(text);
                if (!match.Success)
                {
                    translated = null;
                    return false;
                }

                int capture = 0;
                translated = PrintfToken.Replace(_translation, tokenMatch =>
                {
                    string token = tokenMatch.Value;
                    if (token == "%%")
                        return "%";
                    if (token[token.Length - 1] == 'n')
                        return string.Empty;
                    string groupName = "p" + capture++;
                    Group value = match.Groups[groupName];
                    return value.Success ? value.Value : token;
                });
                return true;
            }
        }

        private static readonly Lazy<Dictionary<string, List<MessageRule>>> MessageIndex =
            new Lazy<Dictionary<string, List<MessageRule>>>(BuildMessageIndex);

        public static string Translate(string text)
        {
            if (text == null) return null;
            if (Words.TryGetValue(text, out var translated)) return translated;
            string messageTranslation = TranslateMessageTemplate(text);
            return GnhZhCnTranslator.Translate(messageTranslation);
        }

        private static Dictionary<string, List<MessageRule>> BuildMessageIndex()
        {
            var index = new Dictionary<string, List<MessageRule>>(StringComparer.OrdinalIgnoreCase);
            foreach (MessageRule rule in Messages)
            {
                if (!index.TryGetValue(rule.Sentinel, out List<MessageRule> rules))
                {
                    rules = new List<MessageRule>();
                    index.Add(rule.Sentinel, rules);
                }
                rules.Add(rule);
            }
            return index;
        }

        private static string TranslateMessageTemplate(string text)
        {
            Dictionary<string, List<MessageRule>> index = MessageIndex.Value;
            if (text.Length < 3 || index.Count == 0)
                return text;

            var checkedRules = new HashSet<MessageRule>();
            var possibleRules = new List<MessageRule>();
            for (int i = 0; i <= text.Length - 3; i++)
            {
                string trigram = text.Substring(i, 3);
                if (!index.TryGetValue(trigram, out List<MessageRule> indexedRules))
                    continue;

                foreach (MessageRule rule in indexedRules)
                {
                    if (checkedRules.Add(rule))
                        possibleRules.Add(rule);
                }
            }

            possibleRules.Sort((left, right) =>
            {
                int literalCompare = right.LiteralLength.CompareTo(left.LiteralLength);
                if (literalCompare != 0) return literalCompare;
                int typeCompare = right.TypeSpecificity.CompareTo(left.TypeSpecificity);
                return typeCompare != 0 ? typeCompare : left.PlaceholderCount.CompareTo(right.PlaceholderCount);
            });
            foreach (MessageRule rule in possibleRules)
            {
                if (rule.TryTranslate(text, out string translated))
                    return translated;
            }
            return text;
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
