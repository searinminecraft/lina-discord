from bot import Lina
import constants

import asyncio
import asyncpg
import contextlib
import discord
import logging
import os
from third_party.stkwrapper import stkserver_wrapper
from logging.handlers import RotatingFileHandler

class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True

@contextlib.contextmanager
def setup_logging():
    log = logging.getLogger()

    try:
        discord.utils.setup_logging()
        # __enter__
        max_bytes = 32 * 1024 * 1024  # 32 MiB
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        log.setLevel(logging.INFO)
        handler = RotatingFileHandler(filename='lina.log', encoding='utf-8', mode='w', maxBytes=max_bytes, backupCount=5)
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)

async def createPool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        constants.POSTGRESQL,
        command_timeout=300,
        min_size=20,
        max_size=20
    )

async def initDatabase(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as con:
        async with con.transaction():

            await con.execute("""
            CREATE TABLE IF NOT EXISTS lina_discord_ptrack(
                id bigint NOT NULL PRIMARY KEY,
                usernames text[]
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS lina_discord_stk_seen(
                username varchar(30) NOT NULL PRIMARY KEY,
                date timestamp without time zone NOT NULL,
                server_name varchar(255) NOT NULL,
                country varchar(2),
                server_country varchar(2)
            )
            """)
            await con.execute("""
            CREATE TABLE IF NOT EXISTS lina_discord_addons(
                id varchar(255) NOT NULL PRIMARY KEY,
                name varchar(255) NOT NULL,
                file text NOT NULL,
                date int NOT NULL,
                uploader varchar(30),
                designer varchar(255),
                description text,
                image text NOT NULL,
                format int NOT NULL,
                revision int NOT NULL,
                status int NOT NULL,
                size int NOT NULL,
                rating float NOT NULL
            )
            """)

async def runBot():
    log = logging.getLogger()
    try:
        pool = await createPool()
        await initDatabase(pool)
    except Exception:
        log.exception("Could not set up PostgreSQL. Will now exit.")
        return

    async with Lina() as lina:
        lina.pool = pool
        lina.stkserver = stkserver_wrapper.STKServer(
                logger=log,
                cwd=os.getcwd() + "/stkserver",
                autostart=False,
                extra_args="--disable-addon-karts --disable-addon-tracks",
                data_path="/usr/share/supertuxkart",
                executable_path="/usr/bin/supertuxkart",
                name="linaSTK Verification Server",
                cfgpath=os.getcwd() + "/stkserver/config.xml"
        )
        await lina.start()

if __name__ == "__main__":
    with setup_logging():
        asyncio.run(runBot())
