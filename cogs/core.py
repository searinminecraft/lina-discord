from __future__ import annotations

import discord
from discord.ext import commands
import logging
from typing import TYPE_CHECKING, Optional

log = logging.getLogger("lina.cogs.core")

if TYPE_CHECKING:
    from bot import Lina

class Core(commands.Cog):

    def __init__(self, bot: Lina):
        self.bot: Lina = bot

    async def cog_check(self, ctx: commands.Context) -> bool:

        return await self.bot.is_owner(ctx.author)

    @commands.command(hidden=True)
    async def load(self, ctx: commands.Context, *, mod: str):
        try:
            await ctx.channel.typing()
            await self.bot.load_extension(mod)
        except commands.ExtensionError as e:
            log.exception("%s: Unable to load:", mod, exc_info=e)
            await ctx.reply(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.reply("Loaded.")
    

    @commands.command(hidden=True)
    async def unload(self, ctx: commands.Context, *, mod: str):
        try:
            await ctx.channel.typing()
            await self.bot.unload_extension(mod)
        except commands.ExtensionError as e:
            log.exception("%s: Unable to unload:", mod, exc_info=e)
            await ctx.reply(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.reply("Unloaded.")

    @commands.command(hidden=True)
    async def reload(self, ctx: commands.Context, *, mod: str):
        try:
            await ctx.channel.typing()
            await self.bot.reload_extension(mod)
        except commands.ExtensionError as e:
            log.exception("%s: Unable to reload:", mod, exc_info=e)
            await ctx.reply(f"{e.__class__.__name__}: {e}")
        else:
            await ctx.reply("Reloaded.")

    @commands.group(invoke_without_command=True, hidden=True)
    @commands.is_owner()
    @commands.guild_only()
    async def sync(self, ctx: commands.Context, guild_id: Optional[int], copy: bool = False):

        if guild_id:
            guild = discord.Object(guild_id)
        else:
            guild = ctx.guild


        await ctx.channel.typing()
        if copy:
            self.bot.tree.copy_global_to(guild=guild)

        commands = await self.bot.tree.sync(guild=guild)
        await ctx.reply(f"Successfully synced {len(commands)} commands.")

    @sync.command(name="global")
    @commands.is_owner()
    async def sync_global(self, ctx: commands.Context):

        commands = await self.bot.tree.sync()
        await ctx.reply(f"Successfully synced {len(commands)} commands.")

    @commands.command(hidden=True)
    async def shutdown(self, ctx: commands.Context):
        await ctx.reply("Shutting down :wave:")
        await self.bot.close()

async def setup(bot: Lina):
    await bot.add_cog(Core(bot))
