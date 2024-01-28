from __future__ import annotations

import discord
from discord.ext import commands
from typing import TYPE_CHECKING
from utils.formatting import humanize_timedelta
import time

if TYPE_CHECKING:
    from bot import Lina


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
                "**Bot started:** {ts}\n"
                "**Players in STK Seen database** {stkseen_count}\n"
                "**Online Players**: {onlinecount}"
            ).format(
                ts=discord.utils.format_dt(self.bot.uptime),
                stkseen_count=(
                    await self.bot.pool.fetchrow("SELECT COUNT(*) FROM lina_discord_stk_seen")
                )["count"],
                onlinecount=len(self.bot.playertrack.onlinePlayers)
            ),
            color=self.bot.accent_color
        ), mention_author=False)

    @commands.hybrid_command(description="Source code")
    async def source(self, ctx: commands.Context):
        return await ctx.send("https://github.com/searinminecraft/lina-discord")

    @commands.hybrid_command(description="About linaSTK")
    async def about(self, ctx: commands.Context):
        return await ctx.reply(embed=discord.Embed(
            title="About linaSTK",
            description=(
                "linaSTK is a free as in freedom and open source "
                "Discord bot that provides SuperTuxKart related "
                "utilities and commands.\n\n"
                "# License\n"
                "Copyright (c) 2023-2024 searingmoonlight\n\n"

                "This program is free software: you can redistribute it and/or modify "
                "it under the terms of the GNU Affero General Public License as published by "
                "the Free Software Foundation, either version 3 of the License, or "
                "(at your option) any later version.\n\n"

                "This program is distributed in the hope that it will be useful, "
                "but WITHOUT ANY WARRANTY; without even the implied warranty of "
                "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
                "GNU Affero General Public License for more details.\n\n"

                "You should have received a copy of the GNU Affero General Public License "
                "along with this program.  If not, see <https://www.gnu.org/licenses/>."
            ),
            color=self.bot.accent_color
        )
            .set_thumbnail(url=self.bot.user.display_avatar.url)
            .set_footer(
                icon_url="https://github.com/searinminecraft.png",
                text="Made with love by searingmoonlight"))

    @commands.command()
    async def ping(self, ctx: commands.Context):

        start = time.perf_counter()
        message = await ctx.reply("Pong!", mention_author=False)
        end = time.perf_counter()

        messageDuration = round((end - start) * 1000)
        heartbeat = round(self.bot.latency * 1000)

        return await message.edit(
            content="Pong! Message: {msg_dur}ms, Heartbeat: {heartbeat_dur}ms".format(
                msg_dur=messageDuration,
                heartbeat_dur=heartbeat
            ))


async def setup(bot: Lina):
    await bot.add_cog(Misc(bot))
