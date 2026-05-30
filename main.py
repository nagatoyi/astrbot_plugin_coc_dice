import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.0")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @event_message_type()
    async def on_group_msg(self, event: MessageEvent):
        msg = event.message_str.strip()
        
        # 1. 严格拦截以 "//" 开头的正式游戏指令
        if not msg.startswith("//"):
            return
            
        raw_cmd = msg[2:].strip()
        sender_name = event.get_sender_name()
        
        if not raw_cmd:
            return

        # =================================================================
        # 模式 A：匹配多面骰公式 (如: // 1d100, // 2d6, // 1d4+1, // 3d6+2)
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
            
            # 给出即时的肉眼反馈
            yield event.plain_result(f"🎲 @{sender_name} 掷出了 {raw_cmd}... (点数已同步给 KP)")
            
            # 构造投喂给大模型的小纸条（追加到消息末尾）
            llm_injection = (
                f"\n\n【系统绝对指令（KP请执行）】:\n"
                f"当前调查员 @{sender_name} 进行了纯骰子投掷，公式为：【{raw_cmd}】。\n"
                f"后台实体骰娘摇出的真实细节为：[ {rolls_detail} ]{mod_str}，最终计算总和为：【 {total} 】。\n"
                f"请你（作为KP）立即在回复最前端明确公示这个投掷结果：\n"
                f"【🎲 KP 掷骰公告】\n"
                f"调查员：@{sender_name}\n"
                f"投掷动作：{raw_cmd}\n"
                f"最终点数：{total}\n"
                f"====================\n"
                f"然后根据这个数值（如伤害扣除、理智丧失等）继续无缝续写接下来的跑团剧情。"
            )
            
            event.message_obj.message_str += llm_injection
            return

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (如: // 力量检定, // 侦查)
        # =================================================================
        skill_target = re.sub(r'(检定|掷骰|骰一下)$', '', raw_cmd).strip()
        if skill_target:
            dice_point = random.randint(1, 100)
            
            yield event.plain_result(f"🎲 @{sender_name} 正在申请【{skill_target}】检定... (1d100 结果已密报给 KP)")
            
            llm_injection = (
                f"\n\n【系统绝对指令（KP请执行）】:\n"
                f"当前调查员 @{sender_name} 正在申请进行【{skill_target}】属性/技能检定。\n"
                f"后台骰娘已为他摇出了 1d100 百分骰，结果为：【 {dice_point} 】。\n"
                f"请你（作为KP）立即查阅你的[知识库/上下文记忆]中关于 @{sender_name} 的【{skill_target}】属性数值，并按 COC 7th 标准判定成功等级（大成功/成功/困难成功/极难成功/失败/大失败）。\n"
                f"请立即在回复最前端明确公示判定结果：\n"
                f"【🎲 KP 检定裁决】\n"
                f"调查员：@{sender_name}\n"
                f"检定科目：【{skill_target}】（当前属性值：请查阅你的知识库填写）\n"
                f"命运骰点：1d100 = [ {dice_point} ]\n"
                f"裁决等级：[请根据对撞结果填写]\n"
                f"====================\n"
                f"然后无缝续写后续剧情发展，推进游戏流程。"
            )
            
            event.message_obj.message_str += llm_injection
