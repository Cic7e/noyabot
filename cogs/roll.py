import ast
import operator as op
import random
import re

import discord
from discord.ext import commands

ALLOWED_OPERATORS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
                     ast.Pow: op.pow, ast.USub: op.neg}
ALLOWED_NODES = [ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, *ALLOWED_OPERATORS.keys()]
VALID_MATH_PATTERN = re.compile(r'^[0-9+\-*/^()\s]+$')

class RollCog(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    def _roll_dice(self, num_dice: int, num_sides: int) -> tuple[int, list[int]]:
        if num_dice > 9999:
            raise ValueError("You can't roll more than 9999 dice at once!")
        if num_sides > 999999999:
            raise ValueError("A die can't have more than 999999999 sides")
        if num_dice < 1 or num_sides < 1:
            return 0, []
        rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
        return sum(rolls), rolls

    def _parse_and_roll(self, dice_string: str, sort: bool) -> tuple[str, str]:
        breakdown_parts = []
        dice_pattern_str = r'(?:[\d.]|\([^)]+\))*[dD](?:[\d.]|\([^)]+\))+'

        def roll_callback(match):
            full_match = match.group(0)
            sep = 'd' if 'd' in full_match else 'D'
            parts = full_match.split(sep, 1)
            raw_dice = parts[0] if parts[0] else "1"
            raw_sides = parts[1]
            if any(x in raw_dice for x in 'dD'):
                dice_resolved, _ = self._parse_and_roll(raw_dice, sort)
            else:
                dice_resolved = raw_dice
            if any(x in raw_sides for x in 'dD'):
                sides_resolved, sides_breakdown = self._parse_and_roll(raw_sides, sort)
            else:
                sides_resolved = raw_sides
                sides_breakdown = raw_sides
            try:
                num_dice = int(self._safe_eval(dice_resolved))
                num_sides = int(self._safe_eval(sides_resolved))
            except (ValueError, SyntaxError, TypeError, IndexError):
                raise ValueError(f"Invalid format in '{full_match}'")
            total, rolls = self._roll_dice(num_dice, num_sides)
            is_complex_sides = (raw_sides != sides_resolved) or not str(raw_sides).isdigit()
            if sort:
                rolls.sort(reverse=True)
            rolls_str = " + ".join(map(str, rolls))
            if is_complex_sides:
                breakdown_parts.append(f"[{sides_breakdown} -> d{num_sides}: {rolls_str}]")
            elif num_dice == 1:
                breakdown_parts.append(str(total))
            else:
                breakdown_parts.append(f"[{rolls_str} = {total}]")
            return str(total)

        sanitized_for_calc = re.sub(dice_pattern_str, roll_callback, dice_string, flags=re.IGNORECASE)
        operators = re.split(dice_pattern_str, dice_string, flags=re.IGNORECASE)
        result_parts = [op + part for op, part in zip(operators, breakdown_parts)]
        full_breakdown = "".join(result_parts) + operators[-1]
        return sanitized_for_calc, full_breakdown

    def _safe_eval(self, expression: str):
        expression = str(expression).replace('^', '**')
        if not expression or not expression.strip():
            return 0
            
        tree = ast.parse(expression, mode='eval')
        for node in ast.walk(tree):
            if type(node) not in ALLOWED_NODES:
                raise ValueError(f"Invalid expression: Disallowed node {type(node).__name__}")

        def _eval_node(node):
            match node:
                case ast.Constant(value=value):
                    if not isinstance(value, (int, float)):
                        raise ValueError("Only numeric constants are allowed.")
                    return value
                case ast.BinOp(left=left, op=op_type, right=right):
                    return ALLOWED_OPERATORS[type(op_type)](_eval_node(left), _eval_node(right))
                case ast.UnaryOp(op=op_type, operand=operand):
                    return ALLOWED_OPERATORS[type(op_type)](_eval_node(operand))
                case ast.Expression(body=body):
                    return _eval_node(body)
                case _:
                    raise TypeError(node)
        return _eval_node(tree)

    @commands.slash_command(name="roll", description="Roll some dice!",
                            integration_types={discord.IntegrationType.guild_install,
                                               discord.IntegrationType.user_install})
    @commands.cooldown(3, 5, commands.BucketType.member)
    @discord.option("dice", description="A number of sides or dice notation (e.g., 20, 1d20, 2d6+5)")
    @discord.option("sort", description="Display as-is or sort by descending?", default=False)
    @discord.option("whisper", description="Should the result be visible only to you?", default=False)
    async def roll(self, ctx, dice: str, sort: bool, whisper: bool):
        await ctx.defer(ephemeral=whisper)
        user_input = dice.replace(' ', '').lower()
        if len(user_input) > 1024:
            await ctx.followup.send("I'm....not rolling this", ephemeral=True)
            return
        try:
            sanitized_string, breakdown_string = self._parse_and_roll(user_input, sort)
            if not VALID_MATH_PATTERN.fullmatch(sanitized_string):
                invalid_chars = "".join(sorted(list(set(re.sub(VALID_MATH_PATTERN, "", sanitized_string)))))
                raise ValueError(f"Unsupported characters: {invalid_chars}")
            sanitized_string = re.sub(r'(?<=\d|\))\(', '*(', sanitized_string)
            total = self._safe_eval(sanitized_string)
            msg_start = f"{ctx.author.mention} rolled `{dice}`"
            if breakdown_string != str(total):
                formatted_breakdown = re.sub(r'([+*/^]|-(?!>))', r' \1 ', breakdown_string)
                formatted_breakdown = re.sub(r'\s+', ' ', formatted_breakdown).strip()
                if len(formatted_breakdown) > 1800:
                     final_response = f"{msg_start} = **{total}!**\n-# (calculations too long to display)"
                else:
                    final_response = f"{msg_start}: `{formatted_breakdown}` = **{total}!**"
            else:
                final_response = f"{msg_start} = **{total}!**"
        except (ValueError, TypeError, SyntaxError, KeyError, ZeroDivisionError) as e:
            if re.search(r'[dD].*\(.*[dD].*\(', user_input):
                 await ctx.followup.send("My abacus just filed a restraining order. "
                                         "Try something like 2d(5+1d5) instead")
                 return
            await ctx.followup.send(f"Sorry, there was an error with your roll: `{e}`")
            return
        await ctx.followup.send(final_response, allowed_mentions=discord.AllowedMentions.none())

def setup(bot: discord.Bot):
    bot.add_cog(RollCog(bot))