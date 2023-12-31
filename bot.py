import discord
from discord.ext import tasks, commands

import logging
import xml.etree.ElementTree as et
from aiohttp import ClientSession
import asyncio
import asyncpg
from utils import bigip, flagconverter

import constants

log = logging.getLogger("lina.main")
log_ptrack = logging.getLogger("lina.ptrack.triggerDiff")

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
        self.addons_dict = {}
        self.serverlist: et.Element = None
        self.lastserverlist: et.Element = None
        self.onlinePlayers = {}
    
    
    async def stkPostReq(self, target, args):
        """Helper function to send a POST request to STK servers."""
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
        async with self.session.get(target) as r:
            r.raise_for_status()
            return et.fromstring(await r.text())
            
    async def setup_hook(self):
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        self.session = ClientSession(
            "https://online.supertuxkart.net",
            headers={
                "User-Agent": "DiscordBot (linaSTK 1.0)"
            }
        )

        log.info(f"Trying to authenticate STK account {constants.STK_USERNAME}")

        try: 
            loginPayload = await self.stkPostReq(
            "/api/v2/user/connect",
            f"username={constants.STK_USERNAME}&" \
            f"password={constants.STK_PASSWORD}&" \
            "save_session=true"
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

        for extension in extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                log.exception(f"Unable to load extension {extension}.")

    async def close(self):
        """Shut down lina"""

        log.info("lina is shutting down...")
        await super().close()
        if hasattr(self, 'session'):
            await self.session.close()

    async def start(self):
        """Bring lina to life"""
        await super().start(constants.TOKEN, reconnect=True)

    @property
    def playertrack(self):
        return self.get_cog("PlayerTrack")

    async def on_ready(self):
        log.info(f"Bot {self.user} ({self.user.id}) is ready!")
