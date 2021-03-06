import collections
import time

import asyncpg
import discord
from discord.ext import commands

from utilities import imaging
from utilities import utils


class Owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="usage", hidden=True)
    async def usage(self, ctx, display: str = None):
        """
        Show total command usage per guild.

        `display`: Can be "pie/piechart" or "bar/barchart", produces an image of their repective charts.
        """

        if not self.bot.usage:
            return await ctx.send("No usage of commands yet.")

        total_usage = {}
        for guild_usage in self.bot.usage.values():
            for command, usage in guild_usage.items():
                if command not in total_usage:
                    total_usage[command] = usage
                else:
                    total_usage[command] += usage
        total_usage = collections.OrderedDict(sorted(total_usage.items(), key=lambda kv: kv[1], reverse=True))

        if display is None:

            embeds = []

            embed = discord.Embed(
                colour=discord.Color.gold(),
                title=f"Total usage",
                description=f"```py\n"
            )
            embed.set_thumbnail(url=self.bot.user.avatar_url_as(format="png", size=1024))
            for command, usage in total_usage.items():
                embed.description += f"{command} : {usage}\n"
            embed.description += "```"
            embeds.append(embed)

            for guild_id, guild_usage in self.bot.usage.items():

                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    continue

                usage = collections.OrderedDict(sorted(guild_usage.items(), key=lambda kv: kv[1], reverse=True))

                embed = discord.Embed(
                    colour=discord.Color.gold(),
                    title=f"{guild.name}",
                    description=f"```py\n"
                )
                embed.set_footer(text=f"{guild.id}")
                embed.set_thumbnail(url=guild.icon_url_as(format="png", size=1024))
                for command, command_usage in usage.items():
                    embed.description += f"{command} : {command_usage}\n"
                embed.description += "```"
                embeds.append(embed)

            return await ctx.paginate_embeds(entries=embeds)

        if display in ["pie", "piechart"]:
            start = time.perf_counter()
            pie_chart = imaging.do_pie_chart([v for v in total_usage.values()], [k for k in total_usage.keys()])
            await ctx.send(file=discord.File(filename=f"StatsPie.png", fp=pie_chart))
            end = time.perf_counter()
            return await ctx.send(f"That took {end - start:.3f}sec to complete")

        if display in ["bar", "barchart"]:
            start = time.perf_counter()
            bar_chart = imaging.do_bar_chart("Command usage", "Command", "Usage", [v for v in total_usage.values()], [k for k in total_usage.keys()])
            await ctx.send(file=discord.File(filename=f"StatsBar.png", fp=bar_chart))
            end = time.perf_counter()
            return await ctx.send(f"That took {end - start:.3f}sec to complete")

    @commands.is_owner()
    @commands.command(name="user_growth", aliases=["ug"], hidden=True)
    async def user_growth(self, ctx, history: int = 24):
        """
        Show user count over the past 24 (by default) hours.

        `history`: The amount of hours to get the history of.
        """

        user_growth = await self.bot.db.fetch("WITH t AS (SELECT * from bot_growth ORDER BY date DESC LIMIT $1) SELECT * FROM t ORDER BY date", history)

        if not user_growth:
            return await ctx.send("No growth data.")

        start = time.perf_counter()
        plot = imaging.do_plot("User growth", "Datetime", "Users", [record["member_count"] for record in user_growth], [record["date"] for record in user_growth])
        await ctx.send(file=discord.File(filename=f"UserGrowth.png", fp=plot))
        end = time.perf_counter()
        return await ctx.send(f"That took {end - start:.3f}sec to complete")

    @commands.is_owner()
    @commands.command(name="guild_growth", aliases=["gg"], hidden=True)
    async def guild_growth(self, ctx, history: int = 24):
        """
        Show guild count over the past 24 (by default) hours.

        `history`: The amount of hours to get the history of.
        """

        guild_growth = await self.bot.db.fetch("WITH t AS (SELECT * from bot_growth ORDER BY date DESC LIMIT $1) SELECT * FROM t ORDER BY date", history)

        if not guild_growth:
            return await ctx.send("No growth data.")

        start = time.perf_counter()
        plot = imaging.do_plot("Guild growth", "Datetime", "Guilds", [record["guild_count"] for record in guild_growth], [record["date"] for record in guild_growth])
        await ctx.send(file=discord.File(filename=f"GuildGrowth.png", fp=plot))
        end = time.perf_counter()
        return await ctx.send(f"That took {end - start:.3f}sec to complete")

    @commands.is_owner()
    @commands.command(name="farms", hidden=True)
    async def farms(self, ctx, guilds_per_page = 20):
        """
        Display how many bots/humans there are in each of the bots guilds.

        `guilds_per_page`: How many guilds to show per page.
        """

        def key(e):
            guild_bots = sum(1 for m in e.members if m.bot)
            guild_total = e.member_count
            return round((guild_bots / guild_total) * 100, 2)

        entries = []

        title = "Guild id           |Total    |Humans   |Bots     |Percent  |Name\n"

        for guild in sorted(self.bot.guilds, key=key, reverse=True):

            bots = sum(1 for m in guild.members if m.bot)
            humans = sum(1 for m in guild.members if not m.bot)
            total = guild.member_count
            percent = f"{round((bots / total) * 100, 2)}%"

            message = f"{guild.id} |{total}{' ' * int(9 - len(str(total)))}|{humans}{' ' * int(9 - len(str(humans)))}|{bots}{' ' * int(9 - len(str(bots)))}|{percent}{' ' * int(9 - len(str(percent)))}|{guild.name}"
            entries.append(message)

        return await ctx.paginate_codeblock(entries=entries, entries_per_page=guilds_per_page, title=title)

    @commands.is_owner()
    @commands.command(name="guilds", hidden=True)
    async def guilds(self, ctx):
        """
        Display information about each guild the bot is in.
        """

        embeds = []

        for guild in self.bot.guilds:
            online, idle, dnd, offline = utils.guild_user_status(guild)
            embed = discord.Embed(
                colour=discord.Color.gold(),
                title=f"{guild.name}'s Stats and Information."
            )
            embed.set_thumbnail(url=guild.icon_url_as(format="png", size=1024))
            embed.set_footer(text=f"ID: {guild.id}")
            embed.add_field(name="__**General information:**__", value=f"**Owner:** {guild.owner}\n"
                                                                       f"**Server created at:** {guild.created_at.__format__('%A %d %B %Y at %H:%M')}\n"
                                                                       f"**Members:** {guild.member_count} |"
                                                                       f"<:online:627627415224713226>{online} |"
                                                                       f"<:away:627627415119724554>{idle} |"
                                                                       f"<:dnd:627627404784828416>{dnd} |"
                                                                       f"<:offline:627627415144890389>{offline}\n"
                                                                       f"**Verification level:** {utils.guild_verification_level(guild)}\n"
                                                                       f"**Content filter level:** {utils.guild_content_filter_level(guild)}\n"
                                                                       f"**2FA:** {utils.guild_mfa_level(guild)}\n"
                                                                       f"**Role Count:** {len(guild.roles)}\n", inline=False)
            embed.add_field(name="__**Channels:**__", value=f"**Text channels:** {len(guild.text_channels)}\n"
                                                            f"**Voice channels:** {len(guild.voice_channels)}\n"
                                                            f"**Voice region:** {utils.guild_region(guild)}\n"
                                                            f"**AFK timeout:** {int(guild.afk_timeout / 60)} minutes\n"
                                                            f"**AFK channel:** {guild.afk_channel}\n", inline=False)
            embeds.append(embed)

        return await ctx.paginate_embeds(entries=embeds)

    @commands.is_owner()
    @commands.command(name="socketstats", aliases=["ss"], hidden=True)
    async def socket_stats(self, ctx):
        """
        Get the total amount of each socket event.
        """

        total = sum(self.bot.socket_stats.values())
        uptime = round(time.time() - self.bot.start_time)
        socket_stats = collections.OrderedDict(sorted(self.bot.socket_stats.items(), key=lambda kv: kv[1], reverse=True))

        message = "\n".join([f"{event}:{' ' * int(28 - len(str(event)))}{count}" for event, count in socket_stats.items()])

        return await ctx.send(f"```\n"
                              f"{total} socket events observed at a rate of {round(total/uptime)}/second\n\n"
                              f"{message}\n"
                              f"```")

    @commands.is_owner()
    @commands.group(name="blacklist", hidden=True, invoke_without_command=True)
    async def blacklist(self, ctx):
        """
        Base command for blacklisting.
        """

        return await ctx.send("Please choose a valid subcommand. See `l-help blacklist` for more information.")

    @commands.is_owner()
    @blacklist.group(name="user", invoke_without_command=True)
    async def blacklist_user(self, ctx):
        """
        Display a list of all blacklisted users.
        """

        blacklisted = []

        blacklist = await self.bot.db.fetch("SELECT * FROM blacklist WHERE type = $1", "user")

        if not blacklist:
            return await ctx.send("No blacklisted users.")

        for entry in blacklist:
            user = self.bot.get_user(entry['id'])
            if not user:
                blacklisted.append(f"User not found - {entry['id']} - Reason: {entry['reason']}")
            else:
                blacklisted.append(f"{user.name} - {user.id} - Reason: {entry['reason']}")

        return await ctx.paginate_codeblock(entries=blacklisted, entries_per_page=10, title=f"Showing {len(blacklisted)} blacklisted users.\n\n")

    @commands.is_owner()
    @blacklist_user.command(name="add")
    async def blacklist_user_add(self, ctx, user: int = None, *, reason=None):
        """
        Add a user to the blacklist.

        `user`: The users id.
        `reason`: Why the user is blacklisted.
        """

        if not reason:
            reason = "No reason"

        if len(reason) > 512:
            return await ctx.caution("The reason can't be more than 512 characters.")

        if not user:
            return await ctx.send("You must specify a user's id.")

        try:
            user = await self.bot.fetch_user(user)
            self.bot.user_blacklist.append(user.id)
            await self.bot.db.execute("INSERT INTO blacklist (id, type, reason) VALUES ($1, $2, $3)", user.id, "user", reason)
            return await ctx.send(f"User: `{user.name} - {user.id}` has been blacklisted with reason `{reason}`")

        except asyncpg.UniqueViolationError:
            return await ctx.send("That user is already blacklisted.")

    @commands.is_owner()
    @blacklist_user.command(name="remove")
    async def blacklist_user_remove(self, ctx, user: int = None):
        """
        Remove a user from the blacklist.

        `user`: The users id.
        """

        if not user:
            return await ctx.send("You must specify a user's id.")

        try:
            user = await self.bot.fetch_user(user)
            self.bot.user_blacklist.remove(user.id)
            await self.bot.db.execute("DELETE FROM blacklist WHERE id = $1", user.id)
            return await ctx.send(f"User: `{user.name} - {user.id}` has been unblacklisted.")
        except ValueError:
            return await ctx.send(f"User: `{user.name} - {user.id}` is not blacklisted.")

    @commands.is_owner()
    @blacklist.group(name="guild", invoke_without_command=True)
    async def blacklist_guild(self, ctx):
        """
        Display a list of all blacklisted guilds.
        """

        blacklisted = []

        blacklist = await self.bot.db.fetch("SELECT * FROM blacklist WHERE type = $1", "guild")

        if not blacklist:
            return await ctx.send("No blacklisted guilds.")

        for entry in blacklist:
            guild = self.bot.get_guild(entry["id"])
            if not guild:
                blacklisted.append(f"Guild not found - {entry['id']} - Reason: {entry['reason']}")
            else:
                blacklisted.append(f"{guild.name} - {guild.id} - Reason: {entry['reason']}")

        return await ctx.paginate_codeblock(entries=blacklisted, entries_per_page=10, title=f"Showing {len(blacklisted)} blacklisted guilds.\n\n")

    @commands.is_owner()
    @blacklist_guild.command(name="add")
    async def blacklist_guild_add(self, ctx, guild: int = None, *, reason=None):
        """
        Add a guild to the blacklist.

        `user`: The guilds id.
        `reason`: Why the guild is blacklisted.
        """

        if not reason:
            reason = "No reason"

        if len(reason) > 512:
            return await ctx.caution("The reason can't be more than 512 characters.")

        if not guild:
            return await ctx.send("You must specify a guild's id.")

        try:

            self.bot.guild_blacklist.append(guild)
            await self.bot.db.execute("INSERT INTO blacklist (id, type, reason) VALUES ($1, $2, $3)", guild, "guild", reason)

            try:
                guild = await self.bot.fetch_guild(guild)
                await guild.leave()
            except discord.Forbidden:
                pass

            return await ctx.send(f"Guild: `{guild}` has been blacklisted with reason `{reason}`")

        except asyncpg.UniqueViolationError:
            return await ctx.send("That guild is already blacklisted.")

    @commands.is_owner()
    @blacklist_guild.command(name="remove")
    async def blacklist_guild_remove(self, ctx, guild: int = None):
        """
        Remove a guild from the blacklist.

        `user`: The guilds id.
        """

        if not guild:
            return await ctx.send("You must specify a guild's id.")

        try:
            self.bot.guild_blacklist.remove(guild)
            await self.bot.db.execute("DELETE FROM blacklist WHERE id = $1", guild)
            return await ctx.send(f"Guild: `{guild}` has been unblacklisted.")
        except ValueError:
            return await ctx.send(f"Guild: `{guild}` is not blacklisted.")


def setup(bot):
    bot.add_cog(Owner(bot))
