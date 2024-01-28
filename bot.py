from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import tasks, commands

import logging
import xml.etree.ElementTree as et
from aiohttp import ClientSession
import asyncpg
from typing import TYPE_CHECKING, Optional

import constants

log = logging.getLogger("lina.main")

if TYPE_CHECKING:
    from cogs import PlayerTrack
    from cogs import Online

extensions = (
    "cogs.online",
    "cogs.playertrack",
    "cogs.core",
    "cogs.misc"
)


class STKRequestError(Exception):
    """Raised when an error occurs upon performing a request to STK servers."""
    pass


class Lina(commands.Bot):
    """
    Class representing lina herself.
    """

    pool: asyncpg.Pool

    def __init__(self):

        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)

        super().__init__(intents=intents,
                         activity=discord.Game(name="SuperTuxKart"),
                         allowed_mentions=allowed_mentions,
                         command_prefix=constants.PREFIX)

        self.accent_color = constants.ACCENT_COLOR
        self.stk_userid: int = None
        self.stk_token: str = None

    async def stkPostReq(self, target, args):
        """Helper function to send a POST request to STK servers."""
        assert self.session is not None
        log.info(
            "Sending %s to %s",
        args.replace(str(self.stk_token), "[REDACTED]").replace(constants.STK_PASSWORD, "[REDACTED]"),
            str(self.session._base_url) + target
        )
        async with self.session.post(
            target, data=args,
            headers={
                **self.session.headers,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        ) as r:
            r.raise_for_status()

            data = et.fromstring(await r.text())

            if data.attrib["success"] == "no":
                raise STKRequestError(data.attrib["info"])
            else:
                return data

    async def stkGetReq(self, target):
        """Helper function to send a GET request to STK servers."""
        assert self.session is not None
        async with self.session.get(target) as r:
            r.raise_for_status()
            return et.fromstring(await r.text())

    async def authSTK(self):
        """Authenticate to STK"""
        log.info(f"Trying to authenticate STK account {constants.STK_USERNAME}")
        try:
            loginPayload = await self.stkPostReq(
                "/api/v2/user/connect",
                f"username={constants.STK_USERNAME}&"
                f"password={constants.STK_PASSWORD}&"
                "save-session=true"
            )
        except Exception:
            log.exception("Unable to authenticate due to error. The bot will now shut down.")
            return await self.close()

        if loginPayload.attrib["success"] == "no":
            log.critical(f"Unable to login! {loginPayload.attrib['info']}")
            log.critical("The bot will now shut down.")
            return await self.close()

        self.stk_userid = loginPayload.attrib["userid"]
        self.stk_token = loginPayload.attrib["token"]

        log.info(f"STK user {loginPayload.attrib['username']} logged in successfully.")

    @tasks.loop(minutes=1)
    async def stkPoll(self):
        try:
            await self.stkPostReq(
                "/api/v2/user/poll",
                f"userid={self.stk_userid}&"
                f"token={self.stk_token}"
            )
        except STKRequestError as e:
            if str(e) in "Session not valid. Please sign in.":
                log.error("Session invalidated. Reauthenticating...")
                await self.authSTK()
            else:
                log.error("Poll request failed: %s", e)
        except Exception:
            log.exception("Poll request failed due to exception:")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.author.send("You can't use this command in private messages.")

        if isinstance(error, commands.CommandInvokeError):
            error: commands.CommandInvokeError
            original = error.original

            if isinstance(original, STKRequestError):
                return await ctx.send(embed=discord.Embed(
                    title="Sorry, an STK related error occurred.",
                    description=str(original),
                    color=self.accent_color
                ))

            return await ctx.send(embed=discord.Embed(
                title="Sorry, this shouldn't have happened. Guru Meditation.",
                description=f"```\n{str(original)}\n```",
                color=self.accent_color
            ))

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandInvokeError):
            error: app_commands.CommandInvokeError
            original = error.original

            if isinstance(original, STKRequestError):
                return await interaction.response.send_message(embed=discord.Embed(
                    title="Sorry, an STK related error occurred.",
                    description=str(original),
                    color=self.accent_color
                ), ephemeral=True)

            return await interaction.response.send_message(embed=discord.Embed(
                title="Sorry, this shouldn't have happened. Guru Meditation.",
                description=f"```\n{str(original)}\n```",
                color=self.accent_color
            ), ephemeral=True)

    async def setup_hook(self):
        self.tree.error(self.on_app_command_error)

        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        self.session = ClientSession(
            "https://online.supertuxkart.net",
            headers={
                "User-Agent": "DiscordBot (linaSTK 1.0)"
            }
        )

        await self.authSTK()

        for extension in extensions:
            try:
                await self.load_extension(extension)
            except Exception:
                log.exception(f"Unable to load extension {extension}.")

    async def close(self):
        """Shut down lina"""

        log.info("lina is shutting down...")
        if hasattr(self, 'session'):
            try:
                await self.stkPostReq("/api/v2/user/client-quit",
                                      f"userid={self.stk_userid}&"
                                      f"token={self.stk_token}")
            finally:
                await self.session.close()

        await super().close()

    async def start(self):
        """Bring lina to life"""
        log.info("Starting bot...")
        await super().start(constants.TOKEN, reconnect=True)

    @property
    def playertrack(self) -> Optional[PlayerTrack]:
        """Represents the PlayerTrack cog"""
        return self.get_cog("PlayerTrack")

    @property
    def online(self) -> Optional[Online]:
        """Represents the Online cog"""
        return self.get_cog("Online")

    async def on_ready(self):
        log.info(f"Bot {self.user} ({self.user.id}) is ready!")
        self.stkPoll.start()
