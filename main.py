import random
import re
from astrbot.api.all import *
from astrbot.api.event.filter import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.1")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @event_message_type(EventMessageType.ALL)
    async def on_group_msg(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        
        # 1. 严格拦截以 "//" 开头的正式游戏指令
        if not msg.startswith("//"):
            return
            
        raw_cmd = msg[2:].strip()
        sender_name = event.get_sender_name()
        
        if not raw_cmd:
            return

        # =================================================================
        # 模式 A：匹配多面骰公式 (如: // 1d100, // 2d6)
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
            
            # 系统指令每一行前加上 //，完美兼容大模型的唤醒词前缀过滤
            llm_injection = (
                f"\n//\n"
                f"// 【系统绝对指令（KP请执行）】:\n"
                f"// 调查员 @{sender_name} 进行了纯骰子投掷：【{raw_cmd}】。\n"
                f"// 骰娘摇出的真实点数总和为：【 {total} 】 (细节: [ {rolls_detail} ]{mod_str})。\n"
                f"// 请KP立即在回复最前端明确公示这个投掷结果并严格使用它：\n"
                f"// 【🎲 KP 掷骰公告】\n"
                f"// 调查员：@{sender_name}\n"
                f"// 投掷动作：{raw_cmd}\n"
                f"// 最终点数：{total}\n"
                f"// ====================\n"
                f"// 请根据此数字无缝推进后续的剧情描写。"
            )
            
            event.message_obj.message_str += llm_injection
            return

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (如: // 力量, // 侦查检定)
        # =================================================================
        skill_target = re.sub(r'(检定|掷骰|骰一下)$', '', raw_cmd).strip()
        if skill_target:
            dice_point = random.randint(1, 100)
            
            yield event.plain_result(f"🎲 @{sender_name} 正在申请【{skill_target}】检定... (1d100 结果已密报给 KP)")
            
            # 系统指令每一行前加上 // 锚定符，直接对齐 AI 要求的唤醒规则
            llm_injection = (
                f"\n//\n"
                f"// 【系统绝对指令（KP请执行）】:\n"
                f"// 调查员 @{sender_name} 正在申请进行【{skill_target}】属性检定。\n"
                f"// 后台实体骰娘已为他摇出了 1d100 结果：【 {dice_point} 】。\n"
                f"// 请KP立即查阅知识库中 @{sender_name} 的【{skill_target}】数值，按 COC 7th 标准在回复最前端公示：\n"
                f"// 【🎲 KP 检定裁决】\n"
                f"// 调查员：@{sender_name}\n"
                f"// 检定科目：【{skill_target}】\n"
                f"// 命运骰点：1d100 = [ {dice_point} ]\n"
                f"// 裁决等级：[由KP比对知识库后得出]\n"
                f"// ====================\n"
                f"// 请直接以此为开篇，并无缝续写后续剧情发展，推进游戏流程。"
            )
            
            event.message_obj.message_str += llm_injection
