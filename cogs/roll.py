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

        def roll_callback(match):
            try:
                num_dice_str = match.group(1) or "1"
                num_sides_str = match.group(2)
                num_dice = int(float(num_dice_str))
                num_sides = int(float(num_sides_str))
            except ValueError:
                raise ValueError(f"Invalid number format in '{match.group(0)}'")
            total, rolls = self._roll_dice(num_dice, num_sides)
            if num_dice == 1:
                breakdown_parts.append(str(total))
            else:
                if sort:
                    rolls.sort(reverse=True)
                breakdown_parts.append(f"[{' + '.join(map(str, rolls))} = {total}]")
            return str(total)
        sanitized_for_calc = re.sub(r'([\d.]*)[a-zA-Z]([\d.]+)', roll_callback, dice_string, flags=re.IGNORECASE)
        operators = re.split(r'[\d.]*[a-zA-Z][\d.]+', dice_string, flags=re.IGNORECASE)
        result = []
        for i in range(len(breakdown_parts)):
            result.append(operators[i])
            result.append(breakdown_parts[i])
        result.append(operators[-1])
        full_breakdown = "".join(result)
        return sanitized_for_calc, full_breakdown

    def _safe_eval(self, expression: str):
        expression = expression.replace('^', '**')
        tree = ast.parse(expression, mode='eval')
        for node in ast.walk(tree):
            if type(node) not in ALLOWED_NODES:
                raise ValueError(f"Invalid expression: Disallowed node {type(node).__name__}")

        def _eval_node(node):
            if isinstance(node, ast.Constant):
                if not isinstance(node.value, (int, float)):
                    raise ValueError("Only numeric constants are allowed.")
                return node.value
            elif isinstance(node, ast.BinOp):
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                return ALLOWED_OPERATORS[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = _eval_node(node.operand)
                return ALLOWED_OPERATORS[type(node.op)](operand)
            elif isinstance(node, ast.Expression):
                return _eval_node(node.body)
            raise TypeError(node)
        return _eval_node(tree)

    @commands.slash_command(name="roll", description="Roll some dice!",
                            integration_types={discord.IntegrationType.guild_install,
                                               discord.IntegrationType.user_install})
    @commands.cooldown(3, 5, commands.BucketType.member)
    @discord.option("dice", description="A number of sides or dice notation (e.g., 20, 1d20, 2d6+5)", default="1d20")
    @discord.option("sort", description="Display as-is or sort by descending?", default=False)
    @discord.option("whisper", description="Should the result be visible only to you?", default=False)
    async def roll(self, ctx, dice: str, sort: bool, whisper: bool):
        await ctx.defer(ephemeral=whisper)
        user_input = dice.replace(' ', '').lower()
        if len(user_input) > 1000:
            await ctx.followup.send("Your roll expression is too long! Please keep it under 1000 characters.",
                                    ephemeral=True)
            return
        if user_input.isdigit():
            user_input = f"1d{user_input}"
        try:
            sanitized_string, breakdown_string = self._parse_and_roll(user_input, sort)
            if not VALID_MATH_PATTERN.fullmatch(sanitized_string):
                invalid_chars = "".join(sorted(list(set(re.sub(VALID_MATH_PATTERN, "", sanitized_string)))))
                raise ValueError(f"Unsupported characters: {invalid_chars}")
            sanitized_string = re.sub(r'(?<=\d|\))\(', '*(', sanitized_string)
            total = self._safe_eval(sanitized_string)
            final_response = f"{ctx.author.mention} rolled **{total}!**"
            if breakdown_string != str(total):
                formatted_breakdown = re.sub(r'([+\-*/^()])', r' \1 ', breakdown_string)
                formatted_breakdown = re.sub(r'\s+', ' ', formatted_breakdown).strip()
                detailed_response = f"{ctx.author.mention} rolled **{total}!** `{formatted_breakdown}`"
                if len(detailed_response) <= 1950:
                    final_response = detailed_response
                else:
                    final_response = f"{ctx.author.mention} rolled **{total}!**"
        except (ValueError, TypeError, SyntaxError, KeyError, ZeroDivisionError) as e:
            await ctx.followup.send(f"Sorry, there was an error with your roll: `{e}`")
            return
        await ctx.followup.send(final_response, allowed_mentions=discord.AllowedMentions.none())

def setup(bot: discord.Bot):
    bot.add_cog(RollCog(bot))