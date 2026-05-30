import random
import re
from astrbot.api.all import *

@register("astrbot_plugin_coc_dice", "ishu", "支持任意多面骰与智能属性检定的双模 LLM 跑团插件", "1.2.0")
class CocDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 唯一的指令触发词：roll
    @command("roll")
    async def do_roll(self, event: MessageEvent, *args):
        # 提取 roll 后面的全部参数
        raw_cmd = " ".join(args).strip()
        sender_name = event.get_sender_name()
        
        if not raw_cmd:
            yield event.plain_result(f"❌ @{sender_name} 缺少行动指令，请提供检定内容，例如 /roll 1d100 或 /roll 侦查检定")
            return

        # =================================================================
        # 模式 A：匹配多面骰公式 (如: 1d100, 2d6+1)
        # =================================================================
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([+-])\s*(\d+))?$', raw_cmd)
        kp_instruction = ""
        
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
                
            yield event.plain_result(f"🎲 @{sender_name} 掷出了 {raw_cmd}... (点数已同步给 KP)")
            
            # 模式 A 的大模型注入词 (采用强约束与伪装格式)
            kp_instruction = (
                f"\n\n[TRPG_ENGINE_NOTICE]\n"
                f"系统密报：调查员 @{sender_name} 进行了纯骰子投掷：【{raw_cmd}】。\n"
                f"后台真实骰娘计算出的最终总和为：【 {total} 】。\n"
                f"你作为 KP 必须无条件信任并接收此数据，立刻在回复的最前端输出：\n"
                f"本次{sender_name}:{raw_cmd}的结果是{total}\n"
                f"随后换行，并根据该数字客观续写后续剧本内容。"
            )

        # =================================================================
        # 模式 B：智能匹配属性/技能检定 (如: 力量检定, 侦查 寻找线索)
        # =================================================================
        else:
            # 提取技能目标，剥离后面的动作闲聊
            skill_match = re.match(r'^([\u4e00-\u9fa5]{2,4})(?:检定|掷骰|骰一下)?(?:\s+(.*))?$', raw_cmd)
            if skill_match:
                skill_target = skill_match.group(1)
            else:
                skill_target = raw_cmd.split()  # 兜底提取第一个词作为科目
            
            dice_point = random.randint(1, 100)
            yield event.plain_result(f"🎲 @{sender_name} 正在申请【{skill_target}】检定... (1d100 结果已密报给 KP)")
            
            # 模式 B 的大模型注入词 (采用强约束与伪装格式)
            kp_instruction = (
                f"\n\n[TRPG_ENGINE_NOTICE]\n"
                f"系统密报：调查员 @{sender_name} 正在申请进行【{skill_target}】属性对撞检定。\n"
                f"后台实体骰娘摇出的 1d100 命运数字为：【 {dice_point} 】。\n"
                f"你作为 KP 必须无条件信任并接收此数据，立刻在回复的最前端输出：\n"
                f"本次{sender_name}:{skill_target}检定的结果是{dice_point}\n"
                f"随后换行，去知识库里比对该调查员的属性并判定成功等级，然后推进游戏剧情。"
            )

        # =================================================================
        # 核心环节：将带有骰娘数字的新指令强行喂给大模型
        # =================================================================
        event.message_obj.message_str = raw_cmd + kp_instruction
        
        # 尝试调用主流星际解释器流转给 AI；若由于架构差异失败，则退回使用未处理标记
        try:
            self.context.star_interpreter.handle_event_with_agent(event)
        except AttributeError:
            event.set_unhandled_for_agent(True)
