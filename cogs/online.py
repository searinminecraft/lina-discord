from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks

import constants
import logging
from typing import TYPE_CHECKING, Any
from utils.formatting import bigip, flagconverter
from utils.paginator import ButtonPaginator

if TYPE_CHECKING:
    from bot import Lina

log = logging.getLogger("lina.cogs.online")


class FriendsListPaginator(ButtonPaginator):

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def format_page(self, page: Any):
        embed = discord.Embed(
            title = f"{self.user}'s Friends",
            description="\n".join(
                [f"* {x}" for x in page]
                ),
            color=constants.ACCENT_COLOR
        )
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages}, Total: {len(self.pages)}")
        return embed


class Online(commands.Cog):

    def __init__(self, bot: Lina):
        self.bot: Lina = bot
        self.addons_dict = {}
        self.cachedSTKUsers = {}

    async def addUsersToCache(self, users: list):

        if len(users) == 1:
            return await self.addUserToCache(users[0][0], users[0][1])

        async with self.bot.pool.acquire() as conn:

            pre = await conn.prepare("INSERT INTO lina_discord_stkusers (id, username) VALUES ($1, $2) ON CONFLICT DO NOTHING")

            for user in users:
                if user[0] not in self.cachedSTKUsers:
                    log.debug("Adding %s (%d) to cache...",
                              user[1], user[0])
                    self.cachedSTKUsers[user[0]] = user[1]

            await pre.executemany(users)

    def idToUsername(self, userid: int):
        """
        Converts a given ID to a usernaFalse
        Returns the ID if it's not found in the cache.
        """

        try:
            return self.cachedSTKUsers[userid]
        except IndexError:
            return userid

    async def usernameToId(self, username: str):
        """
        Converts a username to an ID.

        Raises IndexError if player isn't found in the database.
        """

        sql_esc = str.maketrans({
            "%": "\\%",
            "_": "\\_",
            "\\": "\\\\"
        })

        data = await self.bot.pool.fetchrow(
                "SELECT * FROM lina_discord_stkusers "
                "WHERE username ILIKE $1 "
                "GROUP BY id FETCH FIRST 1 ROW ONLY",
                username.translate(sql_esc) + '%')
        
        if not data:
            raise IndexError(f"Could not find user {username} in database.")

        return (data["id"], data["username"])

    async def addUserToCache(self, userid: int, username: str):
        log.debug("Adding %s (%d) to cache...",
                  username, userid)

        if userid not in self.cachedSTKUsers:
            self.cachedSTKUsers[userid] = username
        await self.bot.pool.execute(
                "INSERT INTO lina_discord_stkusers (id, username) VALUES ($1, $2) "
                "ON CONFLICT DO NOTHING",
                userid, username)

    async def populateCache(self):
        log.info("Populating player cache...")

        data = await self.bot.pool.fetch("SELECT * FROM lina_discord_stkusers")

        for _ in data:
            log.debug("Adding %s (%d) to cache...",
                      _["username"], _["id"])

            self.cachedSTKUsers[_["id"]] = _["username"]

        log.info("Finished populating player cache.")


    @tasks.loop(hours=2)
    async def syncAddons(self):
        addondata = await self.bot.stkGetReq("/downloads/xml/online_assets.xml")

        addons = []
        for a in addondata.findall("track"):
            addons.append((
                a.attrib["id"],
                a.attrib["name"],
                a.attrib["file"],
                int(a.attrib["date"]),
                a.attrib["uploader"],
                a.attrib["designer"],
                a.attrib["description"],
                a.get("image", ""),
                int(a.attrib["format"]),
                int(a.attrib["revision"]),
                int(a.attrib["status"]),
                int(a.attrib["size"]),
                float(a.attrib["rating"])
            ))

            self.addons_dict[a.attrib["id"]] = {
                "id": a.attrib["id"],
                "name":  a.attrib["name"],
                "file": a.attrib["file"],
                "date": int(a.attrib["date"]),
                "uploader": a.attrib["uploader"],
                "designer": a.attrib["designer"],
                "description": a.attrib["description"],
                "image": a.get("image", ""),
                "format": int(a.attrib["format"]),
                "revision": int(a.attrib["revision"]),
                "status": int(a.attrib["status"]),
                "size": int(a.attrib["size"]),
                "rating": float(a.attrib["rating"])
            }

        async with self.bot.pool.acquire() as con:
            pre = await con.prepare(
                """
                INSERT INTO lina_discord_addons
                    (id, name, file, date, uploader, designer, description,
                    image, format, revision, status, size, rating)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (id) DO UPDATE SET
                    id = $1,
                    name = $2,
                    file = $3,
                    date = $4,
                    uploader = $5,
                    designer = $6,
                    description = $7,
                    image = $8,
                    format = $9,
                    revision = $10,
                    status = $11,
                    size = $12,
                    rating = $13
                ;
                """
            )

            await pre.executemany(addons)

    def convertAddonIdToName(self, _id: str):

        _id = _id.removeprefix('addon_')

        match _id:
            case 'abyss': return 'Abyss'
            case 'alien_signal': return 'Alien Signal'
            case 'ancient_colosseum_labrynth': return 'Ancient Colosseum Labrynth'
            case 'arena_candela_city': return 'Candela City'
            case 'battleisland': return 'Battle Island'
            case 'black_forest': return 'Black Forest'
            case 'candela_city': return 'Candela City'
            case 'cave': return 'Cave X'
            case 'cocoa_temple': return 'Cocoa Temple'
            case 'cornfield_crossing': return 'Cornfield Crossing'
            case 'endcutscene': return 'What the fuck?'
            case 'featunlock': return 'lina is the best!!'
            case 'fortmagma': return 'Fort Magma'
            case 'gplose': return 'You lost? Too bad.'
            case 'gpwin': return 'Huh?'
            case 'gran_paradiso_island': return 'Gran Paradiso Island'
            case 'hacienda': return 'Hacienda'
            case 'hole_drop': return 'Hole Drop'
            case 'icy_soccer_field': return 'Icy Soccer Field'
            case 'introcutscene': return 'Intro Cutscene'
            case 'introcutscene2': return 'Intro Cutscene (Part 2)'
            case 'lasdunasarena': return 'Las Dunas Arena'
            case 'lighthouse': return 'Around the Lighthouse'
            case 'mines': return 'Old Mine'
            case 'minigolf': return 'Minigolf'
            case 'oasis': return 'Oasis'
            case 'olivermath': return 'Oliver\'s Math Class'
            case 'overworld': return 'Overworld'
            case 'pumpkin_park': return 'Pumpkin Park'
            case 'ravenbridge_mansion': return 'Ravenbridge Mansion'
            case 'sandtrack': return 'Shifting Sands'
            case 'scotland': return 'Nessie\'s Pond'
            case 'snowmountain': return 'Northern Resort'
            case 'snowtuxpeak': return 'Snow Peak'
            case 'soccer_field': return 'Soccer Field'
            case 'stadium': return 'The Stadium'
            case 'stk_enterprise': return 'STK Enterprise'
            case 'temple': return 'Temple'
            case 'tutorial': return 'Tutorial'
            case 'volcano_island': return 'Volcan Island'
            case 'xr591': return 'XR591'
            case 'zengarden': return 'Zen Garden'
            case _: pass

        try:
            return self.addons_dict[_id]['name']
        except KeyError:
            if _id == '':
                return 'None'
            else:
                return f'Unknown track (ID: `{_id}`)'

    async def cog_load(self):
        self.bot.loop.create_task(self.populateCache())
        self.syncAddons.start()

    def cog_unload(self):
        self.syncAddons.cancel()

    @app_commands.command(
        name="online",
        description="See currently online users."
    )
    async def online(self, interaction: discord.Interaction):
        serverlist = self.bot.playertrack.serverlist

        embed = discord.Embed(
            title = "Public Online",
            color = self.bot.accent_color
        )

        for i in range(len(serverlist[0])):
            serverInfo = serverlist[0][i][0]
            # Some servers (such as Frankfurt servers) have
            # newlines on their names, and it looks ugly on embed
            # and can potentially break the layout. So strip them out.
            serverName = serverInfo.attrib["name"] \
                .replace("\r", "") \
                .replace("\n", "")
            serverCountry = flagconverter(serverInfo.attrib["country_code"])
            currentTrack = self.convertAddonIdToName(serverInfo.attrib["current_track"])
            currentPlayers = int(serverInfo.attrib["current_players"])
            password = int(serverInfo.attrib["password"]) == 1
            ip = bigip(serverInfo.attrib["ip"])
            port = int(serverInfo.attrib["port"])

            players = serverlist[0][i][1]

            log.debug(f"Server {serverName} players: {len(players)}")

            if len(players) == 0:
                continue

            embed.add_field(
                name=f"{serverCountry} {serverName} ({ip}): {len(players)} player{'s' if len(players) > 1 else ''} - {currentTrack}:",
                value="\n".join(
                    [f"{flagconverter(x.attrib['country-code'])} {x.attrib['username']}" for x in players]
                ),
                inline=False
            )
        if len(embed.fields) == 0:
            await interaction.response.send_message(embed=discord.Embed(
                description="Nobody is currently playing.",
                color=self.bot.accent_color
            ))
        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top-players", description="Get top 10 ranked players.")
    async def topplayers(self, interaction: discord.Interaction):

        data = await self.bot.stkPostReq("/api/v2/user/top-players",
                                         f"userid={self.bot.stk_userid}&" \
                                         f"token={self.bot.stk_token}")

        await interaction.response.send_message(embed=discord.Embed(
            title="Top 10 ranked players",
            description="\n".join([
                f"{x + 1}. {data[0][x].attrib['username']} — {round(float(data[0][x].attrib['scores']), ndigits=2)} (Max: {round(float(data[0][x].attrib['max-scores']), ndigits=2)})" for x in range(len(data[0]))
            ]),
            color=self.bot.accent_color
        ))

    @app_commands.command(name="usersearch", description="Search for a user in STK.")
    @app_commands.describe(query="The search query.")
    async def usersearch(self, interaction: discord.Interaction, query: str):
        data = await self.bot.stkPostReq(
            "/api/v2/user/user-search",
            f"userid={self.bot.stk_userid}&"
            f"token={self.bot.stk_token}&"
            f"search-string={query}"
        )

        if len(data[0]) == 0:
            await interaction.response.send_message(embed=discord.Embed(
                title=f"Search results for \"{query}\"",
                description="No results :(",
                color=self.bot.accent_color
            ))
        else:
            await self.addUsersToCache([ (int(x.attrib['id']), x.attrib['user_name']) for x in data[0] ])
            await interaction.response.send_message(embed=discord.Embed(
                title=f"Search results for \"{query}\"",
                description="\n".join([
                    f"* {x.attrib['user_name']} ({x.attrib['id']})" for x in data[0]
                ]),
                color=self.bot.accent_color
            ))

    @app_commands.command(name="friendslist", description="Get a user's friends list.")
    @app_commands.describe(user="The user ID or name of target user.")
    async def friendslist(self, interaction: discord.Interaction, user: str):

        try:
            user = int(user)
        except ValueError:
            pass

        if isinstance(user, int):
            username = self.idToUsername(user)
            data = await self.bot.stkPostReq(
                "/api/v2/user/get-friends-list",
                f"userid={self.bot.stk_userid}&"
                f"token={self.bot.stk_token}&"
                f"visitingid={user}"
            )
        else:
            try:
                userid, username = await self.usernameToId(user)
            except IndexError:
                return await interaction.response.send_message(embed=discord.Embed(
                    title="Error",
                    description=f"I couldn't find user {user} in the database. If possible, try specifying their User ID instead.",
                    color=self.bot.accent_color
                ))

            data = await self.bot.stkPostReq(
                "/api/v2/user/get-friends-list",
                f"userid={self.bot.stk_userid}&"
                f"token={self.bot.stk_token}&"
                f"visitingid={userid}"
            )

        res = []

        for x in range(len(data[0])):
            res.append("{name} ({_id})".format(
                name=data[0][x][0].attrib["user_name"],
                _id=data[0][x][0].attrib["id"])
            )

        await self.addUsersToCache([(
            int(data[0][x][0].attrib["id"]),
            data[0][x][0].attrib["user_name"])
            for x in range(len(data[0]))])

        if len(res) == 0:
            return await interaction.response.send_message(embed=discord.Embed(
                title="Error",
                description=f"User {username} has no friends :(",
                color=self.bot.accent_color
            ))

        page = FriendsListPaginator(username, res, author_id=interaction.user.id, per_page=25)
        await page.start(interaction)
    
    @app_commands.command(name="rank", description="Get a user's ranking")
    @app_commands.describe(user="The user's ID or name")
    async def stk_rank(self, interaction: discord.Interaction, user: str):

        try:
            user = int(user)
        except ValueError:
            pass

        if isinstance(user, int):
            username = self.idToUsername(user)
            data = self.bot.stkPostReq(
                    "/api/v2/user/get-ranking",
                    f"userid={self.bot.stk_userid}&"
                    f"token={self.bot.stk_token}&"
                    f"id={user}"
            )
        else:
            try:
                userid, username = await self.usernameToId(user)
            except IndexError:
                return await interaction.response.send_message(embed=discord.Embed(
                    title="Error",
                    description=f"I couldn't find user {user} in the database. If possible, try specifying their User ID instead.",
                    color=self.bot.accent_color
                ))

            data = await self.bot.stkPostReq(
                "/api/v2/user/get-ranking",
                f"userid={self.bot.stk_userid}&"
                f"token={self.bot.stk_token}&"
                f"id={userid}"
            )


        if int(data.attrib["rank"]) <= 0:
            return await interaction.response.send_message(embed=discord.Embed(
                description=f"{username} has no ranking yet.",
                color=self.bot.accent_color
            ))
        else:
            return await interaction.response.send_message(embed=discord.Embed(
                title=f"{username}'s Ranking Info",
                description=(
                    f"**Rank**: {data.attrib['rank']}\n"
                    f"**Score**: {round(float(data.attrib['scores']), ndigits=2)}\n"
                    f"**Highest Score**: {round(float(data.attrib['max-scores']), ndigits=2)}\n"
                    f"**Raw Score**: {round(float(data.attrib['raw-scores']), ndigits=2)}\n"
                    f"**Number of Races**: {data.attrib['num-races-done']}\n"
                    f"**Deviation**: {round(float(data.attrib['rating-deviation']), ndigits=2)}\n"
                    f"**Disconnects**: (placeholder)"
                    ),
                color=self.bot.accent_color
                ))

async def setup(bot: Lina):
    await bot.add_cog(Online(bot))
