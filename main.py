import random
import re
from astrbot.api.all import *
from astrbot.api.event.filter import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.2")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @event_message_type(EventMessageType.ALL)
    async def on_group_msg(self, event: AstrMessageEvent):
        # 兼容性修复：不管框架有没有切掉前缀 "//"，我们都把前缀剥离干净统一处理
        msg = event.message_str.strip()
        if msg.startswith("//"):
            raw_cmd = msg[2:].strip()
        else:
            raw_cmd = msg # 即使 // 被框架吃掉了，剩余的纯指令也交给我们处理
            
        sender_name = event.get_sender_name()
        if not raw_cmd:
            return

        # =================================================================
        # 模式 A：匹配多面骰公式 (如: 1d100, 2d6)
        # =================================================================
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([\+\-])\s*(\d+))?$', raw_cmd)
        if dice_match:
            num = int(dice_match.group(1))
            sides = int(dice_match.group(2))
            modifier_sign = dice_match.group(3)
            modifier_val = int(dice_match.group(4)) if dice_match.group(4) else 0
            
            if num > 20 or sides > 1000:
                yield event.plain_result(f"❌ @{sender_name} 骰子数量过多或面数过大，法则崩溃了。")
                return
                
            rolls = [random.randint(1, sides) for _ in range(num)]
            total = sum(rolls)
            if modifier_sign == '+':
                total += modifier_val
            elif modifier_sign == '-':
                total -= modifier_val
                
            rolls_detail = " + ".join(map(str, rolls))
            mod_str = f" {modifier_sign} {modifier_val}" if modifier_sign else ""
            
            yield event.plain_result(f"🎲 @{sender_name} 掷出了 {raw_cmd}... (点数已同步给 KP)")
            
            # 每一行头部带上强唤醒标签 //
            llm_injection = (
                f"\n//\n"
                f"// 【系统绝对指令（KP请执行）】:\n"
                f"// 调查员 @{sender_name} 进行了纯骰子投掷：【{raw_cmd}】。\n"
                f"// 后台真实骰娘计算出的最终总和为：【 {total} 】。\n"
                f"// 你作为 KP 必须严格且仅以该格式作为你回复的最前端（严禁自己脑补点数）：\n"
                f"// 本次{sender_name}:{raw_cmd}的结果是{total}\n"
                f"// ====================\n"
                f"// 随后请在此行下方换行，并根据该数字客观续写后续剧本内容。"
            )
            event.message_obj.message_str += llm_injection
            return

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (如: 力量, 侦查检定)
        # =================================================================
        # 只要不是纯丢骰，并且长度在 1-8 个字内（防止把长句子闲聊误判成属性）
        skill_target = re.sub(r'(检定|掷骰|骰一下)$', '', raw_cmd).strip()
        if skill_target and len(skill_target) <= 8 and not skill_target.replace(" ","").isdigit():
            dice_point = random.randint(1, 100)
            
            yield event.plain_result(f"🎲 @{sender_name} 正在申请【{skill_target}】检定... (1d100 结果已密报给 KP)")
            
            llm_injection = (
                f"\n//\n"
                f"// 【系统绝对指令（KP请执行）】:\n"
                f"// 调查员 @{sender_name} 正在申请进行【{skill_target}】属性对撞检定。\n"
                f"// 后台实体骰娘摇出的 1d100 命运数字为：【 {dice_point} 】。\n"
                f"// 你作为 KP 必须严格且仅以该格式作为你回复的最前端（直接使用这个数字，严禁自己脑补）：\n"
                f"// 本次{sender_name}:{skill_target}检定的结果是{dice_point}\n"
                f"// ====================\n"
                f"// 请紧接着去你的知识库里比对该调查员的属性，并在下方换行判定其成功等级（大成功/成功/失败等），然后推进游戏剧情。"
            )
            event.message_obj.message_str += llm_injection
