from __future__ import annotations

import discord
from discord.ext import commands

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import Lina


class Stub(commands.Cog):

    def __init__(self, bot: Lina):
        self.bot: Lina = bot

    def noticeEmbed(self, name: str):
        return discord.Embed(
            description=(
                "Please use slash command `{}` to execute this command.".format(name)  # noqa
            ),
            color=self.bot.accent_color
        )

    @commands.command(name="trackuser", aliases=["stk-trackuser-dm"])
    async def stub_trackuser(self, ctx: commands.Context):

        return await ctx.reply(
                embed=self.noticeEmbed("trackuser"), mention_author=False
        )


async def setup(bot: Lina):
    await bot.add_cog(Stub(bot))
