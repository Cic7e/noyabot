import os
import traceback

import discord
from discord.ext import commands

LOG_CHANNEL_ID = int(os.getenv("ERROR_LOG_CHANNEL_ID"))

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx: discord.ApplicationContext, error: discord.DiscordException):
        error = getattr(error, "original", error)

        async def send_error_message(message, ephemeral=True):
            if ctx.response.is_done():
                await ctx.followup.send(message, ephemeral=ephemeral)
            else:
                await ctx.respond(message, ephemeral=ephemeral)

        if isinstance(error, discord.HTTPException) and error.code == 50035:
            await send_error_message("Output is greater than 2000 characters! Try again")
            return
        if isinstance(error, commands.CommandOnCooldown):
            await send_error_message(f"You're on cooldown for the next {error.retry_after:.2f} seconds!")
            return
        elif isinstance(error, commands.BotMissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await send_error_message(f"I need the following permissions: `{missing_perms}`")
        else:
            tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
            traceback_text = "".join(tb_lines)
            embed = discord.Embed(
                title="Command Error",
                description="An unhandled exception occurred.",
                color=discord.Color.red()
            )
            embed.add_field(name="Command", value=f"`/{ctx.command.name}`", inline=False)
            embed.add_field(name="Author", value=f"{ctx.author.mention} (`{ctx.author.id}`)", inline=False)
            if ctx.guild:
                embed.add_field(name="Location", value=f"**Server:** {ctx.guild.name} (`{ctx.guild.id}`)\n"
                                                       f"**Channel:** {ctx.channel.mention} (`{ctx.channel.id}`)",
                                inline=False)
            else:
                embed.add_field(name="Location", value="Direct Message", inline=False)
            truncated_traceback = traceback_text[-1000:]
            embed.add_field(name="Traceback", value=f"```py\n{truncated_traceback}\n```", inline=False)
            log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(embed=embed)
            else:
                print(f"Error: Log channel with ID {LOG_CHANNEL_ID} not found.")
            await send_error_message("I messed up :( I let Cic7e know")

def setup(bot: discord.Bot):
    bot.add_cog(ErrorHandlerCog(bot))