import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "纯净活泼的专属投掷骰娘插件", "1.3.0")
class CocDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 唯一的指令触发词：roll
    @command("roll")
    async def do_roll(self, event: MessageEvent, *args):
        raw_cmd = " ".join(args).strip()
        sender_name = event.get_sender_name()
        
        if not raw_cmd:
            yield event.plain_result(f"✨ 哎呀 @{sender_name}，你忘记告诉我投什么骰子啦！快告诉我你要扔多大的骰子（比如 /roll 1d100）吧~ 🎲")
            return

        # 仅保留纯正的多面骰匹配逻辑 (如: 1d100, 2d6+1, 1d4)
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([+-])\s*(\d+))?$', raw_cmd)
        
        if dice_match:
            num = int(dice_match.group(1))
            sides = int(dice_match.group(2))
            modifier_sign = dice_match.group(3)
            modifier_val = int(dice_match.group(4)) if dice_match.group(4) else 0
            
            # 骰子数量与面数限制
            if num > 20 or sides > 1000:
                yield event.plain_result(f"🤯 哇哇哇 @{sender_name}！骰子数量太多或者面数太大啦！人家的手都要捧不下啦，稍微少一点好不好嘛~ 💦")
                return
                
            rolls = [random.randint(1, sides) for _ in range(num)]
            total = sum(rolls)
            if modifier_sign == '+':
                total += modifier_val
            elif modifier_sign == '-':
                total -= modifier_val
                
            rolls_detail = " + ".join(map(str, rolls))
            mod_str = f" {modifier_sign} {modifier_val}" if modifier_sign else ""
            
            # 活泼的吐槽逻辑
            comment = "🎉 噔噔噔噔！骰子落地啦！"
            if sides == 100 and num == 1:
                # 针对百面骰的专属吐槽
                if total <= 5:
                    comment = "✨ 哇哦！这简直是大成功！你今天是受幸运女神眷顾了吗？快去买彩票呀！🎉"
                elif total > 95:
                    comment = "💀 噫……大、大失败？！这个数字看得让人倒吸一口凉气，请务必保护好自己！😱"
                elif total <= 50:
                    comment = "😎 稳稳当当！点数很漂亮，看起来一切都在你的掌握之中呢~"
                else:
                    comment = "🤔 唔……看来运气稍微差了一点点，不过没关系，下一次一定会更好的！🐾"
            
            # 最终的活泼输出格式
            reply = (
                f"🎲 命运的齿轮开始转动咯！\n"
                f"✨ @{sender_name} 掷出了 【{raw_cmd}】 ✨\n"
                f"👉 扔出细节：[{rolls_detail}]{mod_str}\n"
                f"🎯 最终点数：====  {total}  ====\n"
                f"{comment}"
            )
            yield event.plain_result(reply)

        else:
            # 输入格式不正确时的卖萌提示
            yield event.plain_result(f"歪头 🤔 @{sender_name}，你扔出的公式好像不太对劲哦？要是标准的 NdM 格式（比如 1d100 或 2d6+3）我才能看得懂呀！快重新试一次吧！🐾")
