import random

import discord
from discord.ext import commands

class RandCog(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.slash_command(name="random", description="Randomly pick a word from a list",
                            integration_types={discord.IntegrationType.guild_install,
                                               discord.IntegrationType.user_install})
    @commands.cooldown(3, 5, commands.BucketType.member)
    @discord.option("choices", description="Separate the choices by a comma, period, or semicolon")
    @discord.option("mode", description="Should I shuffle the list, or choose a random value?",
                    choices=[discord.OptionChoice(name="Shuffle", value="shuffle"),
                             discord.OptionChoice(name="Pick One", value="pick")])
    async def rand(self, ctx, choices: str, mode: str):
        separators = [",", ".", ";"]
        for sep in separators:
            choices = choices.replace(sep, ",")
        items = [item.strip() for item in choices.split(",") if item.strip()]
        if mode == "shuffle":
            random.shuffle(items)
            await ctx.respond(", ".join(items), allowed_mentions=discord.AllowedMentions.none())
        else:
            pick = random.choice(items)
            await ctx.respond(pick, allowed_mentions=discord.AllowedMentions.none())

def setup(bot: discord.Bot):
    bot.add_cog(RandCog(bot))