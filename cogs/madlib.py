import random
import re

import discord
from discord import default_permissions
from discord.ext import commands

from utils.madlib_manager import MadlibManager


class MadCog(commands.Cog):

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.db_manager = MadlibManager()

    def cog_unload(self):
        self.db_manager.close()

    @commands.slash_command(name="madlib", description="Generate a madlib")
    @commands.cooldown(3, 5, commands.BucketType.member)
    @discord.option("text", description="Your madlib, e.g. '{user}'s [adj] {noun} will [verb]'")
    async def madlib(self, ctx, text: str):
        guild_id = ctx.guild.id if ctx.guild else None
        placeholder_configs = {
            "noun": {"pattern": r"\{noun}|\[noun]", "db_type": "noun"},
            "verb": {"pattern": r"\{verb}|\[verb]", "db_type": "verb"},
            "adjective": {"pattern": r"\{adjective}|\{adj}|\[adjective]|\[adj]", "db_type": "adjective"},
            "user": {"pattern": r"\{user}|\[user]", "db_type": None}}
        processed = text
        for cfg in placeholder_configs.values():
            pattern = cfg["pattern"]
            db_type = cfg["db_type"]
            def replacement(_: re.Match, db_type=db_type):
                if db_type is None:
                    if ctx.guild:
                        member_list = [g.display_name for g in ctx.guild.members]
                        user = random.choice(member_list)
                    else:
                        user = ctx.author.display_name
                    word = user
                else:
                    word = self.db_manager.get_random_word(db_type, guild_id)
                return word
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)
        await ctx.respond(processed)

    @commands.slash_command(name="libedit", description="Edit madlib word database",
                            contexts={discord.InteractionContextType.guild})
    @default_permissions(administrator=True)
    @commands.cooldown(3, 30, commands.BucketType.member)
    @discord.option("action", description="What do you want to do?", choices=["add", "remove"])
    @discord.option("word", description="Word to edit, or URL to add multiple words")
    @discord.option("wordtype", description="Type of word", choices=["noun", "verb", "adjective"])
    async def libedit(self, ctx, action: str, word: str, wordtype: str):
        word = word.strip()
        match action:
            case "add":
                word = word.lower()
                added = self.db_manager.add_word(wordtype, word, ctx.guild.id)
                if added:
                    await ctx.respond(f"Added {word} as {wordtype}!")
                else:
                    await ctx.respond(f"{word} is already stored as {wordtype}", ephemeral=True)
            case "remove":
                word = word.lower()
                removed = self.db_manager.remove_word(wordtype, word, ctx.guild.id)
                if removed:
                    await ctx.respond(f"Removed {word} from {wordtype}")
                else:
                    await ctx.respond(f"{word} was not found as a {wordtype}", ephemeral=True)

def setup(bot: discord.Bot):
    bot.add_cog(MadCog(bot))