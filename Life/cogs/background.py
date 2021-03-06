import json
from datetime import datetime

import asyncpg
import discord
from discord.ext import tasks, commands


class Background(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.current_prescence = 0
        self.bot.prescences = []

        self.change_prescence.start()
        self.store_bot_growth.start()
        self.store_usage.start()

    def cog_unload(self):
        self.change_prescence.stop()
        self.store_bot_growth.stop()
        self.store_usage.stop()

    @tasks.loop(hours=1.0)
    async def change_prescence(self):
        self.bot.prescences = [discord.Activity(type=discord.ActivityType.watching,
                                                name=f'{len(self.bot.guilds)} Guilds'),
                               discord.Activity(type=discord.ActivityType.watching,
                                                name=f'{len(self.bot.users)} Users'),
                               discord.Activity(type=discord.ActivityType.playing,
                                                name=f"{self.bot.config.DISCORD_PREFIX}help")
                               ]
        await self.bot.change_presence(activity=self.bot.prescences[self.current_prescence])
        self.current_prescence = (self.current_prescence + 1) % len(self.bot.prescences)

    @change_prescence.before_loop
    async def before_change_prescence(self):
        await self.bot.wait_until_ready()


    @tasks.loop(hours=1.0)
    async def store_bot_growth(self):
        try:
            await self.bot.db.execute(f"INSERT INTO bot_growth VALUES ($1, $2, $3)", datetime.today().strftime('%Y-%m-%d: %H:00'), len(self.bot.users), len(self.bot.guilds))
        except asyncpg.UniqueViolationError:
            pass

    @store_bot_growth.before_loop
    async def before_store_bot_growth(self):
        await self.bot.wait_until_ready()


    @tasks.loop(minutes=30.0)
    async def store_usage(self):

        # Loop through guilds and usages in the bots cache.
        for guild_id, guild_usage in self.bot.usage.items():
            try:
                # Try to add the guild and usage to the database.
                await self.bot.db.execute("INSERT INTO bot_usage VALUES ($1, $2)", guild_id, json.dumps(guild_usage))
            except asyncpg.UniqueViolationError:
                # If the guild was already in the database, fetch it and load it from json to a dict.
                data = await self.bot.db.fetchrow("SELECT * FROM bot_usage WHERE id = $1", guild_id)
                db_usage = json.loads(data["usage"])
                # Loop through the commands and usages of the guild.
                for guild_command_name, guild_command_usage in guild_usage.items():
                    # Over-ride/add an entry to the db dict with this commands usage.
                    db_usage[guild_command_name] = guild_command_usage
                # Update the database with the new usage.
                await self.bot.db.execute("UPDATE bot_usage SET usage = $1 where id = $2", json.dumps(db_usage), guild_id)

    @store_usage.before_loop
    async def before_store_usage(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Background(bot))
