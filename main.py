import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.1.9")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @command("roll")
    async def do_roll(self, event: AstrMessageEvent, args: str = ""):
        sender_name = event.get_sender_name()
        raw_cmd = args.strip()

        if not raw_cmd:
            yield event.plain_result(f"❌ @{sender_name} 请输入具体投掷内容。例如：//roll 1d100 或 //roll 侦查 检查抽屉")
            return

        # 用于存储构造好的 Prompt 注入内容
        llm_injection = ""

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

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (支持: 侦查检定 检查抽屉 / 力量)
        # =================================================================
        else:
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

        # =================================================================
        # 唤醒 AI 核心流转逻辑
        # =================================================================
        if llm_injection:
            # 覆写消息体中的文本，确保大模型接收到带系统注入的 Prompt
            event.message_obj.message_str = raw_cmd + llm_injection

            # 根据 AstrBot 开发规范，通过调用上下文中的星际解释器（star_interpreter）或 llm 服务
            # 显式地将当前修改后的事件重新交由大模型服务去执行推理并输出剧情
            if hasattr(self.context, "star_interpreter"):
                # 方案一：通过星际解释器直接处理
                await self.context.star_interpreter.handle_event_with_agent(event)
            elif hasattr(self.context, "llm_service") or hasattr(self.context, "agent_manager"):
                # 方案二：备用大模型路由网关（兼容不同小版本架构）
                if hasattr(event, "set_unhandled_for_agent"):
                    event.set_unhandled_for_agent(True)
            else:
                # 方案三：通用降级兼容
                pass
