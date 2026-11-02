/*
 * src/gnh_zh_cn.c
 * GnollHack C99 核心引擎运行时简体中文翻译与语法重写引擎
 * 解决痛点：
 *   1. 英文不定冠词 a/an 拼接中文乱码
 *   2. 英文复数后缀 -s/-es/-ies 破坏 UTF-8 多字节序列
 *   3. 英文所有格 's 与动词第三人称单数变形
 *   4. 许愿 (Wishing) 与图鉴查询的双语互转支持
 */

#include <stdio.h>
#include <string.h>
#ifdef _MSC_VER
#define GNH_STRCASECMP _stricmp
#else
#include <strings.h>
#define GNH_STRCASECMP strcasecmp
#endif
#include "../include/gnh_zh_cn.h"
#include "../include/artilist_zh_cn.h"

extern const gnh_zh_kv_t gnh_role_zh_table[];
extern const gnh_zh_kv_t gnh_race_zh_table[];
extern const gnh_zh_kv_t gnh_alignment_zh_table[];
extern const gnh_zh_kv_t gnh_difficulty_zh_table[];
extern const gnh_zh_kv_t gnh_skill_tier_zh_table[];
extern const gnh_zh_kv_t gnh_skill_name_zh_table[];
extern const gnh_zh_kv_t gnh_status_zh_table[];
extern const gnh_zh_kv_t gnh_monster_category_zh_table[];
extern const gnh_zh_kv_t gnh_item_slot_zh_table[];
extern const gnh_zh_kv_t gnh_quality_material_zh_table[];
extern const gnh_zh_kv_t gnh_mythic_prefix_zh_table[];
extern const gnh_zh_kv_t gnh_mythic_suffix_zh_table[];
extern const gnh_zh_kv_t gnh_object_base_zh_table[];
extern const gnh_zh_kv_t gnh_spell_zh_table[];

static const char *lookup_in_table(const gnh_zh_kv_t *table, const char *key)
{
    if (!table || !key || !*key)
        return NULL;
    for (size_t i = 0; table[i].en != NULL; ++i) {
        if (GNH_STRCASECMP(table[i].en, key) == 0)
            return table[i].zh;
    }
    return NULL;
}

static const char *reverse_lookup_in_table(const gnh_zh_kv_t *table, const char *zh_key)
{
    if (!table || !zh_key || !*zh_key)
        return NULL;
    for (size_t i = 0; table[i].en != NULL; ++i) {
        if (strcmp(table[i].zh, zh_key) == 0)
            return table[i].en;
    }
    return NULL;
}

/* 判断字符串是否包含非 ASCII (UTF-8 中文) 字节 */
static int is_utf8_cjk(const char *s)
{
    if (!s)
        return 0;
    while (*s) {
        if (((unsigned char)*s) >= 0x80)
            return 1;
        s++;
    }
    return 0;
}

const char *gnh_zh_translate_monster_or_role(const char *en_name)
{
    if (!en_name)
        return "";
    const char *res = lookup_in_table(gnh_monster_category_zh_table, en_name);
    if (res)
        return res;
    res = lookup_in_table(gnh_role_zh_table, en_name);
    if (res)
        return res;
    res = lookup_in_table(gnh_race_zh_table, en_name);
    return res ? res : en_name;
}

const char *gnh_zh_translate_artifact(const char *en_art_name)
{
    const char *res = lookup_in_table(gnh_artifact_zh_table, en_art_name);
    return res ? res : en_art_name;
}

const char *gnh_zh_translate_spell(const char *en_spell_name)
{
    if (!en_spell_name)
        return "";
    const char *res = lookup_in_table(gnh_spell_zh_table, en_spell_name);
    if (res)
        return res;
    /* 若传入的是不含 "Spellbook of " 的纯法术名，自动拼接查询 */
    char tmp[256];
    snprintf(tmp, sizeof(tmp), "Spellbook of %s", en_spell_name);
    res = lookup_in_table(gnh_spell_zh_table, tmp);
    return res ? res : en_spell_name;
}

const char *gnh_zh_translate_object(const char *en_obj_name)
{
    if (!en_obj_name)
        return "";
    const char *res = lookup_in_table(gnh_object_base_zh_table, en_obj_name);
    if (res)
        return res;
    res = lookup_in_table(gnh_spell_zh_table, en_obj_name);
    if (res)
        return res;
    res = lookup_in_table(gnh_artifact_zh_table, en_obj_name);
    return res ? res : en_obj_name;
}

const char *gnh_zh_translate(const char *en_str)
{
    if (!en_str || !*en_str || is_utf8_cjk(en_str))
        return en_str;

    const gnh_zh_kv_t *tables[] = {
        gnh_artifact_zh_table,
        gnh_object_base_zh_table,
        gnh_spell_zh_table,
        gnh_role_zh_table,
        gnh_race_zh_table,
        gnh_alignment_zh_table,
        gnh_difficulty_zh_table,
        gnh_skill_tier_zh_table,
        gnh_skill_name_zh_table,
        gnh_status_zh_table,
        gnh_monster_category_zh_table,
        gnh_item_slot_zh_table,
        gnh_quality_material_zh_table,
        gnh_mythic_prefix_zh_table,
        gnh_mythic_suffix_zh_table,
        NULL
    };

    for (size_t i = 0; tables[i] != NULL; ++i) {
        const char *hit = lookup_in_table(tables[i], en_str);
        if (hit)
            return hit;
    }
    return en_str;
}

/*
 * 中文不定冠词处理：替代 src/objnam.c 中的 an(str)
 * 在中文环境下不再前置 "a " 或 "an "，直接返回翻译后的名词
 */
char *zh_cn_an(const char *str, char *buf)
{
    if (!str || !buf)
        return buf;
    const char *tr = gnh_zh_translate(str);
    snprintf(buf, GNH_UTF8_BUFSZ, "%s", tr);
    return buf;
}

/*
 * 中文复数处理：替代 src/objnam.c 中的 makeplural(str)
 * 防止英文复数规则在中文 UTF-8 字节末尾错误追加 's' 或 'es'
 */
char *zh_cn_makeplural(const char *str, char *buf)
{
    if (!str || !buf)
        return buf;
    const char *tr = gnh_zh_translate(str);
    snprintf(buf, GNH_UTF8_BUFSZ, "%s", tr);
    return buf;
}

/*
 * 中文所有格处理：替代 src/objnam.c 中的 s_suffix(str)
 */
char *zh_cn_s_suffix(const char *str, char *buf)
{
    if (!str || !buf)
        return buf;
    const char *tr = gnh_zh_translate(str);
    snprintf(buf, GNH_UTF8_BUFSZ, "%s的", tr);
    return buf;
}

/*
 * 动词时态旁路：替代 vtense()
 */
const char *zh_cn_vtense(const char *subj, const char *verb)
{
    (void)subj;
    return verb ? gnh_zh_translate(verb) : "";
}

/*
 * 双语许愿解析器：当玩家在许愿提示框中输入简体中文物品/神器名称时，
 * 自动将其还原为底层 C 引擎 readobjnam() 识别的英文标准名。
 */
const char *zh_cn_resolve_wish_to_english(const char *user_input)
{
    if (!user_input || !*user_input)
        return user_input;
    if (!is_utf8_cjk(user_input))
        return user_input;

    const gnh_zh_kv_t *tables[] = {
        gnh_artifact_zh_table,
        gnh_object_base_zh_table,
        gnh_spell_zh_table,
        NULL
    };
    for (size_t i = 0; tables[i] != NULL; ++i) {
        const char *en = reverse_lookup_in_table(tables[i], user_input);
        if (en)
            return en;
    }
    return user_input;
}
