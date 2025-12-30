import dateparser
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from utils.remind_manager import ReminderManager

def get_time(time: str, *, now: datetime | None = None) -> int:
    reference = now or datetime.now(timezone.utc)
    normalized = (time or "").strip() or "in 5 minutes"
    settings = {
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": reference,
        "PREFER_DATES_FROM": "future",
        "TIMEZONE": "UTC",
        "TO_TIMEZONE": "UTC"}
    parsed = dateparser.parse(normalized, settings=settings)
    if parsed is None:
        raise ValueError("Invalid time format. Try phrases like `in 5 minutes` or `next Tuesday at 2pm`.")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())

class CancelView(discord.ui.View):
    def __init__(self, db_manager, reminder):
        super().__init__(timeout=600)
        self.db_manager = db_manager
        self.reminder = reminder

    @discord.ui.button(label="Cancel?", style=discord.ButtonStyle.grey)
    async def button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        check = self.db_manager.get_reminder(self.reminder)
        if check is None:
            button.label = "Already sent!"
            button.disabled = True
        else:
            button.label = "Cancelled!"
            button.disabled = True
            self.db_manager.remove_reminder(self.reminder)
        await interaction.response.edit_message(view=self)


class ReminderCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.db_manager = ReminderManager()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()
        self.db_manager.close()

    @tasks.loop(seconds=1.0)
    async def check_reminders(self):
        current_timestamp = int(datetime.now(timezone.utc).timestamp())
        due_reminders = self.db_manager.get_due_reminders(current_timestamp)
        for reminder in due_reminders:
            try:
                channel = self.bot.get_channel(reminder['channel_id'])
                user = self.bot.get_user(reminder['author_id'])
                if user is None:
                    try:
                        user = await self.bot.fetch_user(reminder['author_id'])
                    except discord.NotFound:
                        continue
                message_content = "" if reminder['message'] == "null" else reminder['message']
                if channel and not isinstance(channel, discord.DMChannel):
                    await channel.send(content=f"Hey {user.mention}! {message_content}")
                else:
                    await user.send(content=f"Hey! {message_content}")
            except Exception as e:
                print(f"Failed to send reminder {reminder['id']}: {e}")
            finally:
                self.db_manager.remove_reminder(reminder['id'])

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @commands.slash_command(name="remind", description="Sets a persistent reminder, default is 5 minutes")
    @commands.bot_has_permissions(send_messages=True)
    @discord.option("time", description="When do you want to be reminded? Many formats accepted")
    @discord.option("message", description="The message to be reminded of", default="null")
    async def remind(self, ctx, time: str, message: str):
        now_utc = datetime.now(timezone.utc)
        try:
            timestamp = get_time(time, now=now_utc)
        except ValueError as exc:
            return await ctx.respond(str(exc), ephemeral=True)
        seconds_until = timestamp - int(now_utc.timestamp())
        if seconds_until > 315576000:  # 10 years
            return await ctx.respond("You can't set reminders for more than 10 years!", ephemeral=True)
        if seconds_until <= 0:
            return await ctx.respond("You can't set reminders for the past!", ephemeral=True)
        reminder = self.db_manager.add_reminder(author_id=ctx.author.id, channel_id=ctx.channel.id,
                                                    reminder_timestamp=timestamp, message=message)
        stamp = f"on <t:{timestamp}:F>" if seconds_until > 86400 else f"<t:{timestamp}:R>"
        view = CancelView(self.db_manager, reminder)
        return await ctx.respond(f"Got it! I'll remind you {stamp}", ephemeral=True, view=view)

def setup(bot: discord.Bot):
    bot.add_cog(ReminderCog(bot))