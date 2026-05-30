import random
import re
from astrbot.api.all import *
from astrbot.api.event.filter import *  # 显式导入全局拦截器以防丢失

@register("astrbot_plugin_coc_dice", "ishu", "无关键词智能检定骰娘", "1.5.0")
class CocDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 使用全局事件拦截，截获群里每一条消息进行正则检索
    @event_message_type(EventMessageType.ALL)
    async def on_all_messages(self, event):
        # 不使用类型提示，彻底杜绝 MessageEvent not defined 的版本报错
        try:
            raw_text = event.message_str.strip()
        except AttributeError:
            return

        if not raw_text:
            return
            
        # 兼容处理：如果玩家习惯性打了 // 或 / 前缀，自动剥离干净
        cmd = raw_text
        if cmd.startswith("//"):
            cmd = cmd[2:].strip()
        elif cmd.startswith("/"):
            cmd = cmd[1:].strip()

        sender_name = event.get_sender_name()

        # =================================================================
        # 场景一：伤害检定 (自动匹配武器骰)
        # 触发范例："手枪伤害检定", "伤害检定 匕首", "步枪 伤害检定"
        # =================================================================
        if "伤害" in cmd and "检定" in cmd:
            # 内置的 CoC 7th 标准武器伤害面板
            WEAPONS = {
                "手枪": "1d10",
                "左轮": "1d10",
                "散弹枪": "4d6",
                "霰弹枪": "4d6",
                "步枪": "2d6+4",
                "冲锋枪": "2d6",
                "撬棍": "1d6", 
                "棍": "1d6",
                "棒": "1d6",
                "匕首": "1d4",
                "小刀": "1d4",
                "徒手": "1d3",
                "拳头": "1d3",
                "斗殴": "1d3",
                "剑": "1d8",
                "斧": "1d8",
            }
            
            formula = "1d6" # 默认兜底伤害
            weapon_name = "未知武器"

            # 遍历字典，只要发言中包含了该武器名，就自动锁定对应公式
            for w, dmg in WEAPONS.items():
                if w in cmd:
                    formula = dmg
                    weapon_name = w
                    break
            
            # 解析对应武器的骰子公式并计算
            f_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([+-])\s*(\d+))?$', formula)
            if f_match:
                num = int(f_match.group(1))
                sides = int(f_match.group(2))
                mod_sign = f_match.group(3)
                mod_val = int(f_match.group(4)) if f_match.group(4) else 0
                
                rolls = [random.randint(1, sides) for _ in range(num)]
                total = sum(rolls)
                if mod_sign == '+':
                    total += mod_val
                elif mod_sign == '-':
                    total -= mod_val
                
                rolls_detail = " + ".join(map(str, rolls))
                mod_str = f" {mod_sign} {mod_val}" if mod_sign else ""
                
                reply = (
                    f"⚔️ 战斗爆发咯！\n"
                    f"💥 @{sender_name} 进行了 【{weapon_name}】 伤害检定\n"
                    f"👉 武器面板：[{formula}]\n"
                    f"🎲 伤害明细：[{rolls_detail}]{mod_str}\n"
                    f"🩸 最终伤害：====  {total}  ====\n"
                    f"祈祷这一下能把怪物打趴下吧！🔥"
                )
                yield event.plain_result(reply)
            return

        # =================================================================
        # 场景二：常规属性/技能检定 (默认 1d100)
        # 触发范例："力量检定", "侦查检定", "理智检定"
        # =================================================================
        skill_match = re.search(r'^(.{1,6}?)\s*检定$', cmd)
        if skill_match and "伤害" not in cmd:
            skill_target = skill_match.group(1).strip()
            if not skill_target:
                skill_target = "未知行动"
            
            total = random.randint(1, 100)
            
            # 活泼可爱的检定吐槽
            comment = "🎉 噔噔噔噔！骰子落地啦！"
            if total <= 5:
                comment = "✨ 哇哦！大成功！你今天是受幸运女神眷顾了吗？快去买彩票呀！🎉"
            elif total > 95:
                comment = "💀 噫……大、大失败？！看得让人倒吸一口凉气，务必保护好自己！😱"
            elif total <= 50:
                comment = "😎 稳稳当当！点数很漂亮，看起来一切都在掌握之中呢~"
            else:
                comment = "🤔 唔……运气稍微差了一点点，不过没关系，下次一定行！🐾"
            
            reply = (
                f"🎲 命运的齿轮开始转动咯！\n"
                f"✨ @{sender_name} 正在进行 【{skill_target}检定】 ✨\n"
                f"👉 默认投掷：[1d100]\n"
                f"🎯 最终点数：====  {total}  ====\n"
                f"{comment}"
            )
            yield event.plain_result(reply)
            return

        # =================================================================
        # 场景三：作为兜底，直接输入公式依然可以盲骰 (如: 1d100, 2d6+1)
        # =================================================================
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([+-])\s*(\d+))?$', cmd)
        if dice_match:
            num = int(dice_match.group(1))
            sides = int(dice_match.group(2))
            mod_sign = dice_match.group(3)
            mod_val = int(dice_match.group(4)) if dice_match.group(4) else 0
            
            if num > 20 or sides > 1000:
                yield event.plain_result(f"🤯 哇哇哇 @{sender_name}！骰子太多或者面数太大啦！手要捧不下啦~ 💦")
                return
            
            rolls = [random.randint(1, sides) for _ in range(num)]
            total = sum(rolls)
            if mod_sign == '+':
                total += mod_val
            elif mod_sign == '-':
                total -= mod_val
            
            rolls_detail = " + ".join(map(str, rolls))
            mod_str = f" {mod_sign} {mod_val}" if mod_sign else ""
            
            reply = (
                f"🎲 命运的齿轮开始转动咯！\n"
                f"✨ @{sender_name} 掷出了 【{cmd}】 ✨\n"
                f"👉 扔出细节：[{rolls_detail}]{mod_str}\n"
                f"🎯 最终点数：====  {total}  ====\n"
            )
            yield event.plain_result(reply)
            return
