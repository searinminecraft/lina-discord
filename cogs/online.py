from __future__ import annotations

import discord
from discord import app_commands, ui
from discord.ext import commands, menus, tasks
import logging
import xml.etree.ElementTree as et
from typing import TYPE_CHECKING
from utils import bigip, flagconverter

if TYPE_CHECKING:
    from bot import Lina

log = logging.getLogger("lina.cogs.online")


class EmbedPageSource(menus.ListPageSource):

    async def format_page(self, menu, items):
        embed = discord.Embed(description="\n".join(
            items
        ))
        embed.set_footer(text=f"Page {menu.current_page+1}/{self.get_max_pages()} ({len(self.entries)} items)")
        # you can format the embed however you'd like
        return embed

class Online(commands.Cog):

    def __init__(self, bot: Lina):
        self.bot: Lina = bot
        self.addons_dict = {}

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

    def cog_load(self):
        self.syncAddons.start()

    def cog_unload(self):
        self.syncAddons.cancel()

    @app_commands.command(
        name="online",
        description="See currently online users."
    )
    async def online(self, interaction: discord.Interaction):
        serverlist = self.bot.playertrack.serverlist

        result = ""

        fields = []

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
                f"userid={self.bot.stk_userid}&" \
                f"token={self.bot.stk_token}&" \
                f"search-string={query}"
            )
            

        if len(data[0]) == 0:
            await interaction.response.send_message(embed=discord.Embed(
                title=f"Search results for \"{query}\"",
                description="No results :(",
                color=self.bot.accent_color
            ))
        else:
            await interaction.response.send_message(embed=discord.Embed(
                title=f"Search results for \"{query}\"",
                description="\n".join([
                    f"* {x.attrib['user_name']} ({x.attrib['id']})" for x in data[0]
                ]),
                color=self.bot.accent_color
            ))

    @commands.hybrid_command(name="friendslist", description="Get a user's friends list.")
    @app_commands.describe(userid="The user ID of target user. To know their user ID, you can search them using /usersearch.")
    async def friendslist(self, ctx: commands.Context, userid: int):
        data = await self.bot.stkPostReq(
            "/api/v2/user/get-friends-list",
                f"userid={self.bot.stk_userid}&" \
                f"token={self.bot.stk_token}&" \
                f"visitingid={userid}"
            )

        res = []

        for x in range(len(data[0])):
            res.append("{name} ({_id})".format(
                name=data[0][x][0].attrib["user_name"], 
                _id=data[0][x][0].attrib["id"])
            )

        page = menus.MenuPages(EmbedPageSource(res, per_page=50))
        await page.start(ctx)
        
async def setup(bot: Lina):
    await bot.add_cog(Online(bot))
