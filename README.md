# linaSTK Discord Edition
This is lina rewritten to work on Discord. It has the same functions as the Revolt version but it's still work in progress and is incomplete.

This bot is currently used for the SuperTuxKart Discord, but you can self host it yourself.

# Features

## General
- [x] Player tracking
- [x] STK Seen
- [x] Top 10 ranked players
- [x] Player searching
- [ ] Friends list (partial)
- [x] Server list
- [ ] PokeMap
- [ ] Addon querying
- [ ] Ranking info of a player
## Internal
- [x] Authentication
- [x] Polling
- [x] Session revalidation

# How to set up

> This assumes you have knowledge on how to create a Discord bot and set up the proper intents and invite it, as well as how to use the Linux command line, and how to create a PostgreSQL database.
> 
> Only Linux is supported. Other platforms will not be supported.
>
> But feel free to contact me for help setting up the bot.

1. Initial set up
```
git clone https://github.com/searinminecraft/lina-discord
cd lina-discord
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a file named `constants.py` in the root of the folder. Then fill in the information.
```py
# Accent color (used for embeds)
# You must use the hexadecimal representation of the color, or it won't work!
# Example: if your color is #fbce3a then put 0xfbce3a
ACCENT_COLOR = 0xfbce3a

# SuperTuxKart credentials
# This is required to make most features work.

# It is not recommended to use your main account for this.
# You can create an account here: https://online.supertuxkart.net/register.php

STK_USERNAME = ""
STK_PASSWORD = ""

# This is where you put your bot's Discord token. In any circumstances, DO NOT share this
# to anyone, not even your best friend that you trust! If you accidentally share it,
# IMMEDIATELY reset it.
TOKEN = ""

# Prefix for the bot.
# While lina mostly uses slash commands, some are hybrid and some only use
# the old prefix-based command system.
PREFIX = '&'

# PostgreSQL connection
POSTGRESQL = "postgresql://user:pass@localhost/db" 

# Max amount of players a user can track.
# If the user goes above this value, they will not be able to add additional
# players to track unless a user removes one to free up space.
MAX_PTRACK = 15
```

3. Run the bot
```
python launch.py
```

# License

## Bot
This bot is licensed under the GNU Affero General Public License, version 3.

Certain portions of the source code are from Rapptz's RoboDanny bot, licensed under the Mozilla Public License, version 2.

<img width="150" height="150" alt="lina" style="float: left; margin: 0 10px 0 0" align="left" src="https://autumn.revolt.chat/attachments/lCZSC6d20lfGWADC3IZqN4yTVvOluP8V42eozbV3hU/linastk_.png">

## The Lina character
Lina is a cute character I came up with during development. All artwork related to her is licensed under the Creative Commons Attribution Share Alike 4.0 International license. You can use her (or maybe even improve her) as long as you comply with the license. *(also treat her with care)*

<br>

#### Made with :heart: by searingmoonlight
