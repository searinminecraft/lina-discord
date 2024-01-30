from __future__ import annotations

import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import logging
import datetime
import time
import xml.etree.ElementTree as et
from typing import TYPE_CHECKING

import constants
from utils.formatting import bigip, flagconverter, humanize_timedelta

if TYPE_CHECKING:
    from bot import Lina

log = logging.getLogger("lina.cogs.playertrack")


class Confirmation(ui.View):
    def __init__(self, initiator: int):
        super().__init__(timeout=15)
        self.value = None
        self.initiator = initiator

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.initiator:

            await interaction.response.send_message("Hey! This interaction isn't owned by you! Now shoo!", ephemeral=True)
            return False
        return True

    @ui.button(label="Nevermind", style=discord.ButtonStyle.blurple)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = False
        self.stop()

    @ui.button(label="Yes!", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = True
        self.stop()


class PlayerTrack(commands.Cog):
    def __init__(self, bot: Lina):
        self.bot: Lina = bot
        self.lastserverlist = None
        self.serverlist = None
        self.onlinePlayers = {}

    async def ptrackNotifyJoin(self, user: int, userdata: dict, serverdata: dict):
        user = self.bot.get_user(user)
        assert user is not None

        await user.send(embed=discord.Embed(
            title=f"STK Player Tracker",
            description=(
                "{country} {username} joined a server.\n" \
                "Server: {serverCountry} {server}"
            ).format(
                country=flagconverter(userdata["country-code"]),
                username=userdata["username"],
                serverCountry=flagconverter(serverdata["country_code"]),
                server=str(serverdata["name"])
                .replace("\r", "")
                .replace("\n", "")
            ),
            color=self.bot.accent_color
        ).set_thumbnail(
            url="https://raw.githubusercontent.com/supertuxkart/stk-code/master/data/supertuxkart_256.png"
        )) 

    async def ptrackNotifyLeft(self, user: int, userdata: dict, serverdata: dict):
        user = self.bot.get_user(user)
        assert user is not None

        await user.send(embed=discord.Embed(
            title="STK Player Tracker",
            description=(
                "{country} {username} left.\n"
                "Server: {serverCountry} {server}"
            ).format(
                country=flagconverter(userdata["country-code"]),
                username=userdata["username"],
                serverCountry=flagconverter(serverdata["country_code"]),
                server=str(serverdata["name"])
                .replace("\r", "")
                .replace("\n", "")
            ),
            color=self.bot.accent_color
        ).set_thumbnail(
            url="https://raw.githubusercontent.com/supertuxkart/stk-code/master/data/supertuxkart_256.png"
        ))

    async def triggerDiff(self, tree: et.Element):

        if not self.lastserverlist:
            self.lastserverlist = tree

        ids_old = set(int(x[0].attrib["id"]) for x in self.lastserverlist[0])
        ids_new = set(int(x[0].attrib["id"]) for x in tree[0])

        srvCreated = ids_new.difference(ids_old)
        srvDeleted = ids_old.difference(ids_new)

        playersToInsert = []
        playersToInsertnocc = []

        for i in range(len(tree[0])):

            _id = int(tree[0][i][0].attrib["id"])

            if _id in srvCreated:

                log.info("New server created: %s (%s) with id %d and address %s:%d" % (
                    tree[0][i][0].attrib['name'],
                    tree[0][i][0].attrib['country_code'],
                    int(tree[0][i][0].attrib['id']),
                    bigip(int(tree[0][i][0].attrib['ip'])),
                    int(tree[0][i][0].attrib['port'])
                    ))

                playersJoined = tree[0][i][1]

                for player in playersJoined:

                    username = player.attrib["username"]
                    country = player.attrib["country-code"]
                    serverInfo = tree[0][i][0]
                    serverName = serverInfo.attrib["name"]
                    serverCountry = serverInfo.attrib['country_code']
                    playersToInsert.append((username, country,
                                        serverName, serverCountry))

                    if username not in self.onlinePlayers:
                        self.onlinePlayers[username] = serverInfo

        for i in range(len(self.lastserverlist[0])):

            _id = int(self.lastserverlist[0][i][0].attrib["id"])

            if _id in srvDeleted:

                log.info("Server deleted: %s (%s) with id %d and address %s:%d" % (
                    self.lastserverlist[0][i][0].attrib['name'],
                    self.lastserverlist[0][i][0].attrib['country_code'],
                    int(self.lastserverlist[0][i][0].attrib['id']),
                    bigip(int(self.lastserverlist[0][i][0].attrib['ip'])),
                    int(self.lastserverlist[0][i][0].attrib['port'])
                ))

                playersLeft = self.lastserverlist[0][i][1]

                for player in playersLeft:
                    username = player.attrib['username']
                    serverInfo = self.lastserverlist[0][i][0]
                    serverName = serverInfo.attrib['name']
                    serverCountry = serverInfo.attrib['country_code']

                    playersToInsertnocc.append((username,
                                                serverName,
                                                serverCountry))

                    if username in self.onlinePlayers:
                        del self.onlinePlayers[username]

        # Some optimization procedure stuff
        pairs = {}
        offset = 0

        for i in range(min(len(tree[0]), len(self.lastserverlist[0]))):
            _id_next = int(tree[0][i][0].attrib['id'])

            try:
                _id_prev = int(self.lastserverlist[0][i + offset][0].attrib['id'])
            except IndexError:
                log.error(
                "Bad index: prevTree[0][%s][0] is out of boundaries, offset %s, i=%s, len(tree[0]) = %s, len(prevTree[0] = %s)" % (
                    i + offset,
                    offset,
                    i,
                    len(tree[0]),
                    len(self.lastserverlist[0])
                ))
                continue

            if _id_next == _id_prev:
                pairs[tree[0][i]] = self.lastserverlist[0][i + offset]
            elif _id_next in srvCreated:
                offset -= 1
            elif len(tree[0]) != len(self.lastserverlist[0]):
                while _id_prev in srvDeleted:
                    _id_prev = int(self.lastserverlist[0][i + offset][0].attrib['id'])
                    if _id_prev in srvDeleted:
                        offset += 1
                    elif _id_prev == _id_next:
                        pairs[tree[0][i]] = self.lastserverlist[0][i + offset]
                        break
                    else:
                        log.error(
                            "Failed to find an offset at _id_next %s" % _id_next)

        for pair in pairs:
            oldServerInfo = pairs[pair][0]
            oldServerPlayers = pairs[pair][1]
            serverInfo = pair[0]
            serverPlayers = pair[1]

            if serverInfo.attrib['id'] != oldServerInfo.attrib['id']:
                log.warn("Server IDs don't match: %s %s" % (
                    serverInfo.attrib['id'],
                    oldServerInfo.attrib['id']
                ))
                continue

            serverCTrack = None
            oldserverCTrack = None
            if "current_track" in serverInfo.attrib:
                serverCTrack = serverInfo.attrib["current_track"]
            if "current_track" in oldServerInfo.attrib:
                oldserverCTrack = oldServerInfo.attrib["current_track"]

            if serverCTrack != oldserverCTrack:
                if not oldserverCTrack:
                    log.info("Stub: Game started at %s %s - %s" % (
                        serverInfo.attrib['name'],
                        serverInfo.attrib['id'],
                        serverCTrack
                    ))
                elif not serverCTrack:
                    log.info(
                        "Stub: Game ended at %s %s" % (
                            serverInfo.attrib['name'],
                            serverInfo.attrib['id']
                        ))
            diff_attrib = set()
            for attrib in ('max_players',
                       'game_mode',
                       'difficulty'):
                if serverInfo.attrib[attrib] != oldServerInfo.attrib[attrib]:
                    diff_attrib.add(attrib)

            if diff_attrib:
                log.info("Stub: Config difference detected at %s: %s"
                    % (serverInfo.attrib['name'], diff_attrib))

            playersNew = set(str(x.attrib['username']) for x in serverPlayers)
            playersOld = set(str(x.attrib['username']) for x in oldServerPlayers)
            playersJoined = playersNew.difference(playersOld)
            playersLeft = playersOld.difference(playersNew)

            for i in range(len(serverPlayers)):
                username = serverPlayers[i].attrib['username']
                userid = int(serverPlayers[i].attrib['user-id'])
                userCountryCode = serverPlayers[i].attrib['country-code'].lower() if 'country-code' in serverPlayers[i].attrib else ''

                if username in playersJoined:
                    if 'country-code' in serverPlayers[i].attrib:

                        serverName = serverInfo.attrib['name']
                        serverCountry = serverInfo.attrib['country_code']

                        playersToInsert.append((
                            username,
                            userCountryCode,
                            serverName,
                            serverCountry
                        )) 

                    await self.bot.online.addUserToCache(userid, username)

                    async with self.bot.pool.acquire() as con:
                        for e in await con.fetch("SELECT * FROM lina_discord_ptrack;"):
                            if username in e["usernames"]:
                                self.bot.loop.create_task(self.ptrackNotifyJoin(
                                    e["id"],
                                    serverPlayers[i].attrib,
                                    serverInfo.attrib
                                ))


                    self.onlinePlayers[username] = serverInfo

            for i in range(len(oldServerPlayers)):
                if i >= len(oldServerPlayers):
                    log.warning(
                    "Impossible happened: iteration %s is over oldServerPlayers length: %s"
                    % (i, len(oldServerPlayers)))
                    continue

                username = oldServerPlayers[i].attrib['username']
                userCountryCode = oldServerPlayers[i].attrib['country-code']

                if username in playersLeft:
                    if 'country-code' in oldServerPlayers[i].attrib:

                        serverName = oldServerInfo.attrib['name']
                        serverCountry = oldServerInfo.attrib['country_code']

                        playersToInsert.append((
                            username,
                            userCountryCode,
                            serverName,
                            serverCountry
                        ))

                    async with self.bot.pool.acquire() as con:
                        for e in await con.fetch("SELECT * FROM lina_discord_ptrack;"):
                            if username in e["usernames"]:
                                self.bot.loop.create_task(self.ptrackNotifyLeft(
                                    e["id"],
                                    oldServerPlayers[i].attrib,
                                    oldServerInfo.attrib
                                ))


                    if username in self.onlinePlayers:
                        del self.onlinePlayers[username]

            if len(oldServerPlayers) != len(serverPlayers):
                log.info(
                f"Stub: Server {serverName} became full or free")

        try:
            if playersToInsertnocc:
                async with self.bot.pool.acquire() as con:
                    sel = await con.prepare("""
INSERT INTO lina_discord_stk_seen (username, date, server_name, server_country)
VALUES ($1, now() at time zone 'utc', $2, lower($3))
ON CONFLICT (username) DO UPDATE SET
date = now() at time zone 'utc', server_name = $2, server_country = lower($3);
""")
                    await sel.executemany(playersToInsertnocc)
            if playersToInsert:
                async with self.bot.pool.acquire() as con:
                    sel = await con.prepare("""
INSERT INTO lina_discord_stk_seen (username, country, date, server_name, server_country)
VALUES ($1, lower($2), now() at time zone 'utc', $3, lower($4))
ON CONFLICT (username) DO UPDATE SET
country = lower($2), date = now() at time zone 'utc',
server_name = $3, server_country = lower($4);
""")
                    await sel.executemany(playersToInsert)


            playersToInsert.clear()
            playersToInsertnocc.clear()
        except Exception as e:
            log.exception(
                f"Unable to save player info to DB: {e.__class__.__name__}: {e}")

        self.lastserverlist = self.serverlist

    @tasks.loop(seconds=5)
    async def fetcherWrapper(self):
        try:    
            self.serverlist = await self.bot.stkGetReq("/api/v2/server/get-all")
        except Exception:
            log.exception("Failed to get server list.")

        try:
            await self.triggerDiff(self.serverlist)
        except Exception:
            log.exception("Error at triggerDiff")

    def cog_load(self):
        self.fetcherWrapper.start()

    def cog_unload(self):
        self.fetcherWrapper.cancel()

    @commands.hybrid_command(name="stk-seen", aliases=["seen"], description="See when user was last online")
    @app_commands.describe(player="Player to check")
    async def stk_seen(self, interaction: commands.Context, player: str):
        sql_esc = str.maketrans({
            "%": "\\%",
            "_": "\\_",
            "\\": "\\\\"
        })

        try: 
            data = await self.bot.pool.fetchrow("""SELECT username, LOWER(country) AS country,
                                            date, server_name, LOWER(server_country) AS server_country FROM lina_discord_stk_seen
                                            WHERE username ILIKE $1 GROUP BY username FETCH FIRST 1 ROW ONLY""",
                                            player.translate(sql_esc) + "%")
        except Exception:
            log.exception("Could not get stk-seen data for query {player}")
            return await interaction.reply(embed=discord.Embed(
                title="Error",
                description="An error has occurred while processing your request. Please try again.",
                color=self.bot.accent_color
            ), mention_author=False)

        if data:
            if data["username"] in self.onlinePlayers:
                return await interaction.reply(embed=discord.Embed(
                    title="{country} {username} is currently online.".format(
                        country=flagconverter(data["country"]),
                        username=data["username"]
                    ),

                    description="Currently in server: {country} {name}".format(
                        country=flagconverter(data["server_country"]),
                        name=str(data["server_name"]).replace("\r", "").replace("\n", "")
                    ),
                    color=self.bot.accent_color
                ), mention_author=False)
            else:
                return await interaction.reply(embed=discord.Embed(
                    title="{country} {username} is offline.".format(
                        country=flagconverter(data["country"]),
                        username=data["username"]
                    ),

                    description="I last saw {flag} {username} online **{time} ago** (since {ts}) in server: {serverflag} {server}".format(
                        flag=flagconverter(data["country"]),
                        username=data["username"],
                        time=humanize_timedelta(timedelta=(discord.utils.utcnow() - data["date"].replace(tzinfo=datetime.timezone.utc))),
                        ts=discord.utils.format_dt(datetime.datetime.fromtimestamp(data["date"].timestamp() - time.timezone)),
                        serverflag=flagconverter(data["server_country"]),
                        server=str(data["server_name"]).replace("\r","").replace("\n","")
                    ),
                    color=self.bot.accent_color
                ), mention_author=False)
        else:
            return await interaction.reply(embed=discord.Embed(
                title="Unknown player",
                description=f"I have not seen this player before.\nCheck spelling or track them using `/trackuser {player}`",
                color=self.bot.accent_color
            ), mention_author=False)

    @app_commands.command(name="trackuser", description="Track a user.")
    @app_commands.describe(player="The player to track.")
    async def trackuser(self, interaction: discord.Interaction, player: str):
        
        try:
            ptracks = await self.bot.pool.fetchrow("""
            SELECT usernames FROM lina_discord_ptrack
            WHERE id = $1
            """, interaction.user.id)
        except Exception:
            log.exception(f"Could not get ptracks for {interaction.user.id}")
            return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="An error has occurred while processing your request. Please try again.",
                color=self.bot.accent_color
            ), ephemeral=True)

        if ptracks:
            if player in ptracks["usernames"]:
                return await interaction.response.send_message(embed=discord.Embed(
                    description=f"You are already tracking {player}.",
                    color=self.bot.accent_color
                ), ephemeral=True)

            if len(ptracks["usernames"]) >= constants.MAX_PTRACK:
                return await interaction.response.send_message(embed=discord.Embed(
                    title="Maximum amount of tracked players reached",
                    description=(
                        f"You have reached the maximum amount of players you can track ({constants.MAX_PTRACK}). " \
                        "Please untrack a user before tracking another one."
                    ),
                    color=self.bot.accent_color
                ), ephemeral=True)
        
        try:
            await self.bot.pool.execute("""
            INSERT INTO lina_discord_ptrack
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET
            usernames = array_append(lina_discord_ptrack.usernames, $3)
            """, interaction.user.id, {player}, player)

            await interaction.response.send_message(embed=discord.Embed(
                title=f"Tracking {player} privately.",
                description=(
                    "Okay, I will send a direct message to you every time the user joins/leaves a server. " \
                    f"To stop me from tracking {player}, execute `/untrackuser {player}`."
                ),
                color=self.bot.accent_color
            ), ephemeral=True)
        except Exception:
            log.exception(f"Could not add player {player} for {interaction.user.id}")
            await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="An error has occurred while processing your request. Please try again.",
                color=self.bot.accent_color
            ), ephemeral=True)


    @app_commands.command(name="untrackuser", description="No longer track a user")
    @app_commands.describe(player="The player you're tracking to not track anymore")
    async def untrackuser(self, interaction: discord.Interaction, player: str):

        try:
            data = await self.bot.pool.fetchrow("""
            SELECT usernames FROM lina_discord_ptrack
            WHERE id = $1
            """, interaction.user.id)
        except Exception:
            log.exception(f"Could not get ptracks of user {interaction.user.id}")
            return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="An error has occurred while processing your request. Please try again.",
                color=self.bot.accent_color
            ), ephemeral=True)

        if not data:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="No data from you is in the database yet.",
                color=self.bot.accent_color
            ), ephemeral=True)

        if player in data["usernames"]:
            try:
                await self.bot.pool.execute("""
                UPDATE lina_discord_ptrack
                SET usernames = array_remove(lina_discord_ptrack.usernames, $1)
                WHERE id = $2
                """, player, interaction.user.id)
            except Exception:
                log.exception(f"Could not remove player {player} from {interaction.user.id}")
                return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="An error has occurred while processing your request. Please try again.",
                color=self.bot.accent_color
            ), ephemeral=True)
            else:
                return await interaction.response.send_message(embed=discord.Embed(
                title=f"No longer tracking {player}",
                description=f"You are no longer tracking {player}.",
                color=self.bot.accent_color
            ), ephemeral=True)
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="You are not currently tracking this player.",
                color=self.bot.accent_color
            ), ephemeral=True)

    @app_commands.command(name="usertracks", description="See list of players you're tracking.")
    async def usertracks(self, interaction: discord.Interaction):

        try:
            data = await self.bot.pool.fetchrow("""
            SELECT usernames FROM lina_discord_ptrack
            WHERE id = $1
            """, interaction.user.id)
        except Exception:
            log.exception(f"Could not get ptracks of user {interaction.user.id}")
            return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description="An error has occurred while processing your request. Please try again.",
                color=self.bot.accent_color
            ), ephemeral=True)

        noPlayersEmbed = discord.Embed(
            title="You aren't tracking any players yet.",
            description="To start tracking players, execute `/trackuser username`",
            color=self.bot.accent_color
        )
        if not data:
            return await interaction.response.send_message(embed=noPlayersEmbed, ephemeral=True)
        else:
            if len(data["usernames"]) == 0:
                return await interaction.response.send_message(embed=noPlayersEmbed, ephemeral=True)
            else:
                return await interaction.response.send_message(embed=discord.Embed(
                    title=f"Players you're currently tracking",
                    description="\n".join([
                        f"* {x}" for x in data["usernames"]
                    ]),
                    color=self.bot.accent_color
                ).set_footer(text=f"Total: {len(data['usernames'])}"), ephemeral=True)


    @app_commands.command(name="untrackall", description="Untrack ALL users you're currently tracking.")
    async def untrackall(self, interaction: discord.Interaction):

        view = Confirmation(interaction.user.id)
        await interaction.response.send_message(embed=discord.Embed(
            title="Warning!",
            description=(
                "You're about to untrack ALL users you're currently tracking.\n"\
                "This cannot be undone. Continue?"),
            color=self.bot.accent_color
        ), view=view)

        await view.wait()

        if view.value == True:

            try:
                await self.bot.pool.execute(
                """
                UPDATE lina_discord_ptrack SET usernames = '{}' WHERE id = $1
                """, interaction.user.id)
            except Exception:
                log.exception(f"Could not clear ptracks for user {interaction.user.id}")
                return await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="Error",
                        description="A database error occurred. Please contact the developer.",
                        color=self.bot.accent_color
                    )
                )
            else:
                return await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="Successfully cleared.",
                        description="Your player track list has been cleared.",
                        color=self.bot.accent_color
                    ),
                    view=None
                )
        elif view.value == False:
            return await interaction.delete_original_response()
        else:
            return await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="Error",
                        description="You waited too much...",
                        color=self.bot.accent_color
                    ), view=None
                )

async def setup(bot: Lina):
    await bot.add_cog(PlayerTrack(bot))
