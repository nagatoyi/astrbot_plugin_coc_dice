import random
import re
from astrbot.api.all import *
from astrbot.api.event.filter import *

@register("astrbot_plugin_coc_dice", "ishu", "单机双芯无缝交棒骰娘测试版", "1.6.0")
class CocDicePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 依然使用全局事件拦截，避免 @command 的强制断流
    @event_message_type(EventMessageType.ALL)
    async def on_all_messages(self, event):
        try:
            raw_text = event.message_str.strip()
        except AttributeError:
            return

        if not raw_text:
            return
            
        cmd = raw_text
        if cmd.startswith("//"):
            cmd = cmd[2:].strip()
        elif cmd.startswith("/"):
            cmd = cmd[1:].strip()

        sender_name = event.get_sender_name()

        # =================================================================
        # 我们以常规属性/技能检定为例，加入“交棒”逻辑
        # =================================================================
        skill_match = re.search(r'^(.{1,6}?)\s*检定$', cmd)
        if skill_match and "伤害" not in cmd:
            skill_target = skill_match.group(1).strip()
            if not skill_target:
                skill_target = "未知行动"
            
            total = random.randint(1, 100)
            
            comment = "🎉 噔噔噔噔！骰子落地啦！"
            if total <= 5: comment = "✨ 哇哦！大成功！"
            elif total > 95: comment = "💀 噫……大失败？！"
            elif total <= 50: comment = "😎 稳稳当当！点数很漂亮~"
            else: comment = "🤔 唔……看来运气稍微差了一点点！🐾"
            
            reply = (
                f"🎲 命运的齿轮开始转动咯！\n"
                f"✨ @{sender_name} 正在进行 【{skill_target}检定】 ✨\n"
                f"👉 默认投掷：[1d100]\n"
                f"🎯 最终点数：====  {total}  ====\n"
                f"{comment}"
            )
            
            # 1. 骰娘先在群里发出物理计算的活泼结果
            yield event.plain_result(reply)
            
            # 2. 核心交棒区：构造强行投喂给 AI 的密报
            # 注意：每一行都加了 //，防止 AI KP 判定为“场外发言”而闭嘴
            kp_instruction = (
                f"\n//\n"
                f"// [TRPG_ENGINE_NOTICE]\n"
                f"// 系统密报：玩家 @{sender_name} 刚刚进行了【{skill_target}检定】。\n"
                f"// 后台物理骰娘摇出的真实结果点数是：【 {total} 】。\n"
                f"// 你作为 KP 必须无条件信任并接收此数据，立刻在回复的最前端输出：\n"
                f"// 本次{sender_name}:{skill_target}检定的结果是{total}\n"
                f"// 随后换行，结合知识库比对成功等级，立刻生成接下来的剧情描述。"
            )
            
            # 3. 强行篡改底层的消息内容，把密报塞进去
            event.message_obj.message_str = f"// 申请{skill_target}检定" + kp_instruction
            
            # 4. 踹醒大模型，强制告诉框架：“这个事件还没完，请大模型接客！”
            try:
                event.set_unhandled_for_agent(True)
            except Exception:
                pass
                
            return

        # =================================================================
        # 公式兜底盲骰 (如: 1d100, 2d6) 也加入交棒逻辑
        # =================================================================
        dice_match = re.match(r'^(\d+)[dD](\d+)(?:\s*([+-])\s*(\d+))?$', cmd)
        if dice_match:
            num = int(dice_match.group(1))
            sides = int(dice_match.group(2))
            mod_sign = dice_match.group(3)
            mod_val = int(dice_match.group(4)) if dice_match.group(4) else 0
            
            if num > 20 or sides > 1000:
                yield event.plain_result(f"🤯 哇哇哇 @{sender_name}！骰子太多啦！")
                return
            
            rolls = [random.randint(1, sides) for _ in range(num)]
            total = sum(rolls)
            if mod_sign == '+': total += mod_val
            elif mod_sign == '-': total -= mod_val
            
            reply = f"🎲 @{sender_name} 掷出了 【{cmd}】，最终点数：====  {total}  ===="
            yield event.plain_result(reply)
            
            kp_instruction = (
                f"\n//\n"
                f"// [TRPG_ENGINE_NOTICE]\n"
                f"// 系统密报：玩家 @{sender_name} 投掷了【{cmd}】，结果是：【 {total} 】。\n"
                f"// 请 KP 结合该数字，立刻输出剧情。"
            )
            event.message_obj.message_str = f"// 投掷{cmd}" + kp_instruction
            try:
                event.set_unhandled_for_agent(True)
            except Exception:
                pass
            return
