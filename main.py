import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.8")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 显式注册 roll 命令。当输入 //roll ... 时，背后的文本会传入 args 参数中
    @command("roll")
    async def do_roll(self, event: AstrMessageEvent, args: str = ""):
        sender_name = event.get_sender_name()
        raw_cmd = args.strip()

        if not raw_cmd:
            yield event.plain_result(f"❌ @{sender_name} 请输入具体投掷内容。例如：//roll 1d100 或 //roll 侦查 检查抽屉")
            return

        # =================================================================
        # 模式 A：匹配标准多面骰公式 (如: 1d100, 2d6, 1d20+4)
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
                
            # 1. 打印本地掷骰回显
            yield event.plain_result(f"🎲 @{sender_name} 掷出了 {raw_cmd}... (点数已同步给 KP)")
            
            # 2. 构造注入给大模型的 Prompt
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
            
            # 3. 篡改消息文本，引导接下来的 AI 进行剧情润色
            event.message_obj.message_str = raw_cmd + llm_injection
            
            # 让框架知道这个事件还需要转交给 Agent 决策链（激活 AI 回复）
            if hasattr(event, "set_unhandled_for_agent"):
                event.set_unhandled_for_agent(True)
            return

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (支持: 侦查检定 检查抽屉 / 力量)
        # =================================================================
        # 正则解析：开头2-4个汉字为技能名，中间可选“检定/掷骰”，后面可选随后的行为描述
        skill_match = re.match(r'^([\u4e00-\u9fa5]{2,4})(检定|掷骰|骰一下)?(?:\s+(.*))?$', raw_cmd)
        
        if skill_match:
            skill_target = skill_match.group(1) 
            action_desc = skill_match.group(3) if skill_match.group(3) else "" 
            
            dice_point = random.randint(1, 100)
            display_action = f"【{skill_target}】" + (f"({action_desc})" if action_desc else "")
            
            # 1. 打印本地检定回显
            yield event.plain_result(f"🎲 @{sender_name} 正在申请 {display_action} 检定... (1d100 结果已密报给 KP)")
            
            # 2. 构造注入给大模型的 Prompt
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
            
            # 3. 将 Prompt 覆写进上下文，交棒给 AI
            event.message_obj.message_str = raw_cmd + llm_injection
            
            if hasattr(event, "set_unhandled_for_agent"):
                event.set_unhandled_for_agent(True)
            return

        # 如果既不是公式也不是合法技能名，交还给 Agent 做普通闲聊处理
        if hasattr(event, "set_unhandled_for_agent"):
            event.set_unhandled_for_agent(True)
