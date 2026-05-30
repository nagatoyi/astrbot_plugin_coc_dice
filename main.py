import random
import re
from astrbot.api.all import *
from astrbot.api.event.filter import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.3")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 使用 regex 过滤器，强行拦截以 // 或 . 或 🎲 开头的所有消息，确保插件比 Agent 优先触发
    @filter.regex(r"^(//|\.|\🎲)\s*(.*)$")
    async def on_dice_command(self, event: AstrMessageEvent, match: re.Match):
        # 提取去掉前缀后的核心指令内容
        raw_cmd = match.group(2).strip()
        sender_name = event.get_sender_name()
        
        if not raw_cmd:
            return

        # =================================================================
        # 模式 A：匹配多面骰公式 (如: 1d100, 2d6, .r 1d20)
        # =================================================================
        # 允许命令中包含小写 r 或格式化字符
        dice_cmd = re.sub(r'^r\s*', '', raw_cmd).strip() # 去除可能存在的 .r 中的 r
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
            
            # 强行注入给大模型的上下文
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
            
            # 安全做法：同时修改 message_str 并尝试更新 message_obj
            event.message_obj.message_str = raw_cmd + llm_injection
            return

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (支持: 侦查检定 检查蜡烛 / 力量检定)
        # =================================================================
        # 改用更聪明的正则：捕获句子开头的 2-4 个字作为技能名称（如 侦查、理智、心理学）
        # 匹配诸如 "侦查检定..."、"心理学骰一下..." 或直接 "力量..."
        skill_match = re.match(r'^([\u4e00-\u9fa5]{2,4})(检定|掷骰|骰一下)?(?:\s+(.*))?$', raw_cmd)
        
        if skill_match:
            skill_target = skill_match.group(1) # 提取出 "侦查"
            action_desc = skill_match.group(3) if skill_match.group(3) else "" # 提取出 "检查蜡烛和蜡堆"
            
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
            
            # 将带有提示词的完整文本交给接下来的 Agent 流程
            event.message_obj.message_str = raw_cmd + llm_injection
            return
