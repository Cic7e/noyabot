import random
from typing import Union

import discord
from discord.ext import commands


class SomeoneCog(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.slash_command(name="someone", description="Selects a random user from the server with optional filters.")
    @discord.option("channel", description="Filter users by text or voice channel.",
                    type=Union[discord.VoiceChannel, discord.TextChannel], default=None)
    @discord.option("role", description="Filter users by role.", type=discord.Role, default=None)
    @discord.option("ping", description="Ping the selected user?", type=bool, default=False)
    @discord.option("text", description="Additional funny text?", type=str, default="")
    async def someone(self, ctx, channel, role, ping, text):
        member_pool = [member for member in ctx.guild.members if not member.bot]
        if role:
            member_pool = [member for member in member_pool if role in member.roles]
        if channel:
            if isinstance(channel, discord.VoiceChannel):
                member_pool = [member for member in member_pool if member.voice and member.voice.channel == channel]
            elif isinstance(channel, discord.TextChannel):
                member_pool = [member for member in member_pool if channel.permissions_for(member).view_channel]
        if not member_pool:
            await ctx.respond("No users found!", ephemeral=True)
            return
        chosen_member = random.choice(member_pool)
        if ping:
            mentions = discord.AllowedMentions.users
        else:
            mentions = discord.AllowedMentions.none()
        print(chosen_member.display_name)
        await ctx.respond(f"{chosen_member.mention} {text}", allowed_mentions=mentions)

def setup(bot: discord.Bot):
    bot.add_cog(SomeoneCog(bot))