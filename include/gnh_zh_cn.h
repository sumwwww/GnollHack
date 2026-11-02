/*
 * include/gnh_zh_cn.h
 * GnollHack 简体中文汉化核心头文件 (C99 Core Engine)
 * 适配目标: Modern Windows Port (.NET 10 MAUI / WinUI 3 - gnollhackwin.dll)
 */

#ifndef GNH_ZH_CN_H
#define GNH_ZH_CN_H

#ifdef __cplusplus
extern "C" {
#endif

#define GNH_ZH_CN_ENABLED 1

/*
 * UTF-8 缓冲区扩容说明：
 * 原版 NetHack/GnollHack 中 BUFSZ 通常为 256 字节，QBUFSZ 为 128 字节。
 * 在 UTF-8 编码下，每个简体中文字符占 3 字节，拼接长传奇词缀物品名与状态消息时
 * 极易触发缓冲区截断甚至栈溢出。建议在 include/global.h 中引入此宏將 BUFSZ 提升至 1024。
 */
#ifndef GNH_UTF8_BUFSZ
#define GNH_UTF8_BUFSZ 1024
#endif

#ifndef GNH_UTF8_QBUFSZ
#define GNH_UTF8_QBUFSZ 512
#endif

/* 词条映射结构体 */
typedef struct gnh_zh_kv {
    const char *en;
    const char *zh;
} gnh_zh_kv_t;

/* 核心翻译查询函数（精确匹配 + 前缀/后缀词缀合成） */
const char *gnh_zh_translate(const char *en_str);
const char *gnh_zh_translate_object(const char *en_obj_name);
const char *gnh_zh_translate_spell(const char *en_spell_name);
const char *gnh_zh_translate_artifact(const char *en_art_name);
const char *gnh_zh_translate_monster_or_role(const char *en_name);

/*
 * 中文语法适配函数（替代 src/objnam.c 与 src/pline.c 中的英文屈折变化）：
 * 1. zh_cn_an(str): 取消英文 "a " / "an " 冠词，直接返回中文名词或补足量词
 * 2. zh_cn_makeplural(str): 禁用英文词尾 +s/+es/+ies 复数变形，直接返回原中文名
 * 3. zh_cn_s_suffix(str): 将英文所有格 "'s" / "'" 替换为中文 "的"
 * 4. zh_cn_vtense(subj, verb): 禁用英文第三人称单数动词变形
 * 5. zh_cn_resolve_wish(input): 支持玩家输入中文或英文进行许愿(Wishing)与百科查询
 */
char *zh_cn_an(const char *str, char *buf);
char *zh_cn_makeplural(const char *str, char *buf);
char *zh_cn_s_suffix(const char *str, char *buf);
const char *zh_cn_vtense(const char *subj, const char *verb);
const char *zh_cn_resolve_wish_to_english(const char *user_input);

#define GNH_TR(s)          gnh_zh_translate(s)
#define GNH_TR_OBJ(s)      gnh_zh_translate_object(s)
#define GNH_TR_SPELL(s)    gnh_zh_translate_spell(s)
#define GNH_TR_ART(s)      gnh_zh_translate_artifact(s)
#define GNH_TR_MON(s)      gnh_zh_translate_monster_or_role(s)

#ifdef __cplusplus
}
#endif

#endif /* GNH_ZH_CN_H */
