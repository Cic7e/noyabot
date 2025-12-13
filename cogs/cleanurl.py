import json
import math
import os
import re
from collections import Counter
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

import discord
from discord.ext import commands

from utils.url_manager import AllowlistManager

URL_CHANNEL_ID = int(os.getenv("URL_LOG_CHANNEL_ID"))

def load_rules() -> dict:
    rules_path = "data/rules.json"
    try:
        with open(rules_path, "r") as f:
            data = json.load(f)
            print(f"Loaded {len(data.get('GENERAL', []))} general and {len(data) - 1} specific domain rules.")
            return data
    except FileNotFoundError:
        print(f"WARNING: {rules_path} not found. URL cleaner will have no rules.")
        return {"GENERAL": []}

def calculate_entropy(text: str) -> float:
    if not text:
        return 0.0
    entropy = 0
    length = len(text)
    counts = Counter(text)
    for count in counts.values():
        p_x = count / length
        entropy += - p_x * math.log2(p_x)
    return entropy

class FeedbackView(discord.ui.View):
    def __init__(self, cog, url_data: list):
        super().__init__(timeout=600)
        self.cog = cog
        self.url_data = url_data

    @discord.ui.button(label="This isn't correct", style=discord.ButtonStyle.red)
    async def button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        button.label = "Thanks!"
        button.disabled = True
        await interaction.response.edit_message(view=self)
        for item in self.url_data:
            await self.cog._log_cleaning(title="User Feedback Received", color=discord.Color.red(),
                                         original_url=item["original"], cleaned_url=item["cleaned"],
                                         triggered_by=interaction.user)

class CleanerCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.db_manager = AllowlistManager()
        self.rules = load_rules()

    def cog_unload(self):
        self.db_manager.close()

    def _filter_allowlist(self, url: str) -> str | None:
        parsed_url = urlparse(url)
        allowed_params = self.db_manager.get_params(parsed_url.netloc)
        if allowed_params is None:
            return None
        allowed_params = set(allowed_params)
        query_params = parse_qs(parsed_url.query)
        final_params = {key: value for key, value in query_params.items() if key.lower() in allowed_params}
        new_query = urlencode(final_params, doseq=True)
        url_parts = list(parsed_url)
        url_parts[4] = new_query
        return urlunparse(url_parts)

    def _filter_fallback(self, url: str):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        params_to_remove = {p.lower() for p in self.rules.get("GENERAL", [])}
        domain_parts = parsed_url.netloc.lower().split('.')
        for i in range(len(domain_parts)):
            current_domain = ".".join(domain_parts[i:])
            if current_domain in self.rules:
                params_to_remove.update({p.lower() for p in self.rules[current_domain]})
        filtered_params = { key: value for key, value in query_params.items() if key.lower() not in params_to_remove}
        final_params = {}
        for key, value_list in filtered_params.items():
            value_str = value_list[0]
            if len(value_str) >= 20:
                entropy = calculate_entropy(value_str)
                if entropy >= 4:
                    continue
            final_params[key] = value_list
        new_query = urlencode(final_params, doseq=True)
        url_parts = list(parsed_url)
        url_parts[4] = new_query
        return urlunparse(url_parts)

    async def _log_cleaning(self, *, title: str, color: discord.Color, original_url: str, cleaned_url: str,
                            triggered_by: discord.User = None):
        parsed = urlparse(cleaned_url)
        domain = parsed.netloc
        params = parse_qs(parsed.query)
        param_str = json.dumps(params, indent=2) if params else "None"
        channel = self.bot.get_channel(URL_CHANNEL_ID)
        embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
        embed.add_field(name="Original URL", value=f"<{original_url}>", inline=False)
        embed.add_field(name="Cleaned URL", value=f"<{cleaned_url}>", inline=False)
        embed.add_field(name="Domain", value=f"```\n{domain}\n```", inline=False)
        embed.add_field(name="Current Parameters", value=f"```json\n{param_str}```", inline=False)
        if triggered_by:
            embed.set_footer(text=f"Feedback from: {triggered_by.name}", icon_url=triggered_by.display_avatar.url)
        await channel.send(embed=embed)

    @commands.message_command(name="Clean URLs", integration_types={discord.IntegrationType.guild_install,
                                                                    discord.IntegrationType.user_install})
    async def clean_urls(self, ctx: discord.ApplicationContext, message: discord.Message):
        ephemeral = True if ctx.guild else False
        await ctx.defer(ephemeral=ephemeral)
        url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        found_urls = url_pattern.findall(message.content)
        if not found_urls:
            await ctx.followup.send("No URLs were found in this message.")
            return
        processed_data = []
        for url in found_urls:
            cleaned_url = self._filter_allowlist(url)
            if cleaned_url is None:
                cleaned_url = self._filter_fallback(url)
                await self._log_cleaning(title="Fallback Filter Used",
                                         color=discord.Color.yellow(), original_url=url, cleaned_url=cleaned_url)
            processed_data.append({"original": url, "cleaned": cleaned_url})
        cleaned_links = [item["cleaned"] for item in processed_data]
        final_urls = "\n\n".join(f"<{link}>" for link in cleaned_links)
        view = FeedbackView(cog=self, url_data=processed_data)
        await ctx.followup.send(f"{final_urls}\n-# This is in beta :)", view=view)

    @commands.slash_command(name="urledit", description="Manage the URL allowlist.",
                            default_permissions=discord.Permissions(administrator=True),
                            guild_ids=[911994369605775431])
    @discord.option("action", description="The action to perform.", choices=["view", "append", "remove"])
    @discord.option("domain", description="The domain to manage")
    @discord.option("param", description="The parameter to add/remove", default=None)
    async def urledit(self, ctx, action: str, domain: str, param: str = None):
        if not await self.bot.is_owner(ctx.author):
            return await ctx.respond("You do not have permission to use this command.", ephemeral=True)
        domain = domain.lower()
        param = param.lower() if param else None

        if action == "view":
            params = self.db_manager.get_params(domain)
            if not params:
                return await ctx.respond(f"Domain `{domain}` not found in the allowlist.", ephemeral=True)
            return await ctx.respond(f"Allowed parameters for `{domain}`:\n```\n{', '.join(params)}\n```", ephemeral=True)

        elif action == "append" and param:
            was_present, new_params = self.db_manager.append_param(domain, param)
            if was_present:
                return await ctx.respond(f"Parameter `{param}` already exists for `{domain}`.", ephemeral=True)
            new_params_str = ",".join(sorted(list(new_params)))
            return await ctx.respond(f"Appended `{param}`. New params for `{domain}`:\n```\n{new_params_str}\n```",
                                     ephemeral=True)

        elif action == "remove" and param:
            status, remaining_params = self.db_manager.remove_param(domain, param)
            match status:
                case "domain_not_found":
                    return await ctx.respond(f"Domain `{domain}` not found in the allowlist.", ephemeral=True)
                case "param_not_found":
                    return await ctx.respond(f"Parameter `{param}` does not exist for `{domain}`.", ephemeral=True)
                case "domain_removed":
                    return await ctx.respond(f"🗑️ Removed `{param}`. No parameters left, so `{domain}` was removed from the allowlist.", ephemeral=True)
                case "param_removed":
                    new_params_str = ",".join(sorted(list(remaining_params)))
                    return await ctx.respond(f"Removed `{param}`. New params for `{domain}`:\n```\n{new_params_str}\n```", ephemeral=True)
        else:
            return await ctx.respond(f"The `param` option is required for the `{action}` action.", ephemeral=True)

def setup(bot: discord.Bot):
    bot.add_cog(CleanerCog(bot))