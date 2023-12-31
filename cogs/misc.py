import discord
from discord import app_commands
from discord.ext import commands
import datetime

from bot import Lina
from utils.formatting import humanize_timedelta

class Misc(commands.Cog):
    def __init__(self, bot: Lina):
        self.bot: Lina = bot

    @commands.hybrid_command(name="uptime", description="Know how long I have been up.")
    async def uptime(self, ctx: commands.Context):

        delta = discord.utils.utcnow() - self.bot.uptime
        uptime = self.bot.uptime
        uptime_str = humanize_timedelta(timedelta=delta)

        await ctx.reply(
            "I have been up for **{time}** (since {ts})".format(
                time=uptime_str, ts=discord.utils.format_dt(uptime)
            ), mention_author=False
        )

    @commands.hybrid_command(name="stats", description="General bot stats")
    async def stats(self, ctx: commands.Context):
        await ctx.reply(embed=discord.Embed(
            title="Bot statistics",
            description=(
                "**Bot started:** {ts}\n" \
                "**Players in STK Seen database** {stkseen_count}\n" \
                "**Online Players**: {onlinecount}"
            ).format(
                ts=discord.utils.format_dt(self.bot.uptime),
                stkseen_count=(await self.bot.pool.fetchrow("SELECT COUNT(*) FROM lina_discord_stk_seen"))["count"],
                onlinecount=len(self.bot.playertrack.onlinePlayers)
            ),
            color=self.bot.accent_color
        ), mention_author=False)

async def setup(bot: Lina):
    await bot.add_cog(Misc(bot))
