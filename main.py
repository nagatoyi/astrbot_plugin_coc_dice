import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.2.0")
class TRPGLLMDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @command("roll")
    async def do_roll(self, event: AstrMessageEvent, args: str = ""):
        sender_name = event.get_sender_name()
        raw_cmd = args.strip()

        if not raw_cmd:
            yield event.plain_result(f"❌ @{sender_name} 请输入具体投掷内容。")
            return

        kp_instruction = ""
        display_action = ""

        # =================================================================
        # 模式 A：匹配标准多面骰公式
        # =================================================================
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([\+\-])\s*(\d+))?$', raw_cmd)
        if dice_match:
            num = int(dice_match.group(1))
            sides = int(dice_match.group(2))
            modifier_sign = dice_match.group(3)
            modifier_val = int(dice_match.group(4)) if dice_match.group(4) else 0
            
            rolls = [random.randint(1, sides) for _ in range(num)]
            total = sum(rolls)
            if modifier_sign == '+': total += modifier_val
            elif modifier_sign == '-': total -= modifier_val
                
            display_action = f"🎲 @{sender_name} 掷出了 {raw_cmd}... (点数已同步给 KP)"
            
            kp_instruction = (
                f"【系统提示：调查员 @{sender_name} 进行了纯骰子投掷【{raw_cmd}】。"
                f"后台真实骰娘计算出的最终总和为【 {total} 】。"
                f"请你作为 KP，必须严格且仅以下面这种格式作为你回复的最前端："
                f"本次{sender_name}:{raw_cmd}的结果是{total}\n"
                f"随后请在此行下方换行，并根据该数字客观续写后续剧本内容。】"
            )

        # =================================================================
        # 模式 B：智能匹配属性/技能检定
        # =================================================================
        else:
            skill_match = re.match(r'^([\u4e00-\u9fa5]{2,4})(检定|掷骰|骰一下)?(?:\s+(.*))?$', raw_cmd)
            if skill_match:
                skill_target = skill_match.group(1) 
                action_desc = skill_match.group(3) if skill_match.group(3) else "" 
                dice_point = random.randint(1, 100)
                
                display_action = f"🎲 @{sender_name} 正在申请 【{skill_target}】 检定... (1d100 结果已密报给 KP)"
                
                kp_instruction = (
                    f"【系统提示：调查员 @{sender_name} 正在申请进行【{skill_target}】属性对撞检定。动作描述: {action_desc}。"
                    f"后台实体骰娘摇出的 1d100 命运数字为【 {dice_point} 】。"
                    f"请你作为 KP，必须严格且仅以下面这种格式作为你回复的最前端："
                    f"本次{sender_name}:{skill_target}检定的结果是{dice_point}\n"
                    f"请紧接着去你的知识库里比对该调查员的属性，并在下方换行判定其成功等级（大成功/成功/失败等），然后推进游戏剧情。】"
                )

        if kp_instruction:
            # 1. 立即把骰娘的结果先发出来
            yield event.plain_result(display_action)
            
            # 2. 核心突破：直接调用 AstrBot 的底层 LLM 接口来获取 AI KP 的回复
            # 这样可以绕过事件流拦截，强行让 AI 推进剧情
            try:
                # 尝试从 context 获取当前群聊/私聊的底层 llm 处理器
                provider = self.context.get_llm_provider() if hasattr(self.context, "get_llm_provider") else None
                if provider:
                    # 将玩家的原本陈述与后台强指令组合
                    prompt = f"玩家动作: {raw_cmd}\n\n{kp_instruction}"
                    
                    # 让大模型产生回复 (注意：此方法会带上之前的上下文历史)
                    # 如果需要纯文本回复，可以直接使用 text_chat 等底层方法
                    response = await provider.text_chat(prompt, session_id=event.session_id)
                    
                    if response and response.completion:
                        yield event.plain_result(response.completion)
                        return
            except Exception as e:
                # 捕获异常，防止底层方法名在不同版本有微调时崩溃
                pass

            # 方案二（备用）：如果上面的底层调用失败，使用全新的原生纯文本模拟注入
            # 修改当前 message 并在下一轮激活（部分版本适用）
            event.message_obj.message_str = raw_cmd + "\n" + kp_instruction
            if hasattr(event, "set_unhandled_for_agent"):
                event.set_unhandled_for_agent(True)
