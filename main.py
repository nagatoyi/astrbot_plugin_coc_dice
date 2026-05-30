import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.4")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @event_message_type(EventMessageType.ALL)
    async def on_group_msg(self, event: AstrMessageEvent):
        msg = event.message_str.strip()
        
        # 1. 使用原生正则拦截检查：必须以 // 或 . 或 🎲 开头
        prefix_match = re.match(r"^(//|\.|\🎲)\s*(.*)$", msg)
        if not prefix_match:
            return # 如果没有跑团前缀，直接释放，交由其他插件或 Agent 处理

        # 2. 提取去掉前缀后的核心指令内容
        raw_cmd = prefix_match.group(2).strip()
        sender_name = event.get_sender_name()
        
        if not raw_cmd:
            return

        # =================================================================
        # 模式 A：匹配多面骰公式 (如: 1d100, 2d6)
        # =================================================================
        dice_cmd = re.sub(r'^r\s*', '', raw_cmd).strip() 
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([\+\-])\s*(\d+))?$', dice_cmd)
        
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
                
            yield event.plain_result(f"🎲 @{sender_name} 掷出了 {dice_cmd}... (点数已同步给 KP)")
            
            llm_injection = (
                f"\n//\n"
                f"// 【系统绝对指令（KP请执行）】:\n"
                f"// 调查员 @{sender_name} 进行了纯骰子投掷：【{dice_cmd}】。\n"
                f"// 后台真实骰娘计算出的最终总和为：【 {total} 】。\n"
                f"// 你作为 KP 必须严格且仅以该格式作为你回复的最前端（严禁自己脑补点数）：\n"
                f"// 本次{sender_name}:{dice_cmd}的结果是{total}\n"
                f"// ====================\n"
                f"// 随后请在此行下方换行，并根据该数字客观续写后续剧本内容。"
            )
            
            event.message_obj.message_str = raw_cmd + llm_injection
            return

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (支持: 侦查检定 检查蜡烛)
        # =================================================================
        skill_match = re.match(r'^([\u4e00-\u9fa5]{2,4})(检定|掷骰|骰一下)?(?:\s+(.*))?$', raw_cmd)
        
        if skill_match:
            skill_target = skill_match.group(1) 
            action_desc = skill_match.group(3) if skill_match.group(3) else "" 
            
            dice_point = random.randint(1, 100)
            
            display_action = f"【{skill_target}】" + (f"({action_desc})" if action_desc else "")
            yield event.plain_result(f"🎲 @{sender_name} 正在申请 {display_action} 检定... (1d100 结果已密报给 KP)")
            
            llm_injection = (
                f"\n//\n"
                f"// 【系统绝对指令（KP请执行）】:\n"
                f"// 调查员 @{sender_name} 正在申请进行【{skill_target}】属性对撞检定。动作描述: {action_desc}\n"
                f"// 后台实体骰娘摇出的 1d100 命运数字为：【 {dice_point} 】。\n"
                f"// 你作为 KP 必须严格且仅以该格式作为你回复的最前端（直接使用这个数字，严禁自己脑补）：\n"
                f"// 本次{sender_name}:{skill_target}检定的结果是{dice_point}\n"
                f"// ====================\n"
                f"// 请紧接着去你的知识库里比对该调查员的属性，并在下方换行判定其成功等级（大成功/成功/失败等），然后推进游戏剧情。"
            )
            
            event.message_obj.message_str = raw_cmd + llm_injection
            return
