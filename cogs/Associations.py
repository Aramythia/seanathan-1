import discord
import asyncio

from discord.ext import commands
from discord.ext.commands import BucketType, cooldown, CommandOnCooldown
from dpymenus import Page, PaginatedMenu

import aiosqlite
from Utilities import Checks, AssetCreation, PageSourceMaker

import random

PATH = 'PATH'

# There will be brotherhoods, guilds, and later colleges for combat, economic, and political gain

class Associations(commands.Cog):

    def __init__(self, client):
        self.client = client

    #EVENTS
    @commands.Cog.listener() # needed to create event in cog
    async def on_ready(self): # YOU NEED SELF IN COGS
        print('Associations is ready.')

    #COMMANDS

    # ----- BROTHERHOODS ----- ASSOCIATIONS THAT BUFF COMBAT AND PVP 
    @commands.group(aliases=['bh'], invoke_without_command=True, case_insensitive=True, description='See your brotherhood')
    @commands.check(Checks.in_brotherhood)
    async def brotherhood(self, ctx):
        info = await AssetCreation.getGuildFromPlayer(ctx.author.id)
        getLeader = commands.UserConverter()
        leader = await getLeader.convert(ctx, str(info['Leader']))
        level, progress = await AssetCreation.getGuildLevel(info['ID'], returnline=True)
        members = await AssetCreation.getGuildMemberCount(info['ID'])
        capacity = await AssetCreation.getGuildCapacity(info['ID'])

        embed = discord.Embed(title=f"{info['Name']}", color=0xBEDCF6)
        embed.set_thumbnail(url=f"{info['Icon']}")
        embed.add_field(name='Leader', value=f"{leader.mention}")
        embed.add_field(name='Members', value=f"{members}/{capacity}")
        embed.add_field(name='Level', value=f"{level}")
        embed.add_field(name='EXP Progress', value=f'{progress}')
        embed.add_field(name=f"This {info['Type']} is {info['Join']} to new members.", value=f"{info['Desc']}", inline=False)
        embed.set_footer(text=f"Guild ID: {info['ID']}")
        await ctx.reply(embed=embed)

    @brotherhood.command(brief='<name>', description='Found a brotherhood. Costs 15,000 gold.')
    @commands.check(Checks.not_in_guild)
    async def create(self, ctx, *, name : str):
        if len(name) > 32:
            await ctx.reply('Name max 32 characters')
            return
        # Make sure they have the money and an open name
        if not await Checks.guild_can_be_created(ctx, name):
            return
        # Otherwise create the guild
        async with aiosqlite.connect(PATH) as conn:
            await conn.execute('INSERT INTO guilds (guild_name, guild_type, leader_id, guild_icon) VALUES (?, ?, ?, ?)', (name, 'Brotherhood', ctx.author.id, 'https://cdn4.iconfinder.com/data/icons/ionicons/512/icon-ios7-contact-512.png'))
            c = await conn.execute('SELECT guild_id FROM guilds WHERE leader_id = ?', (ctx.author.id,))
            guild_id = await c.fetchone()
            await conn.execute('UPDATE players SET guild = ?, gold = gold - 15000, guild_rank = "Leader" WHERE user_id = ?', (guild_id[0], ctx.author.id,))
            await conn.commit()
        await ctx.reply('Brotherhood founded. Do `brotherhood` to see it or `brotherhood help` for more commands!')

    @brotherhood.command(brief='<desc', description='Change your brotherhood\'s description [GUILD LEADER ONLY]')
    # @commands.check(Checks.is_guild_leader) <-- Next check covers leaders too
    @commands.check(Checks.is_guild_officer)
    async def description(self, ctx, *, desc : str):
        if len(desc) > 256:
            await ctx.reply(f'Description max 256 characters. You gave {len(desc)}')
            return
        # Get guild and change description
        async with aiosqlite.connect(PATH) as conn:
            c = await conn.execute('SELECT guild FROM players WHERE user_id = ?', (ctx.author.id,)) 
            guild_id = await c.fetchone()
            await conn.execute('UPDATE guilds SET guild_desc = ? WHERE guild_id = ?', (desc, guild_id[0]))
            await conn.commit()
        await ctx.reply('Description updated!')

    @brotherhood.command(brief='<url>', description='Invite a player to your guild')
    @commands.check(Checks.is_guild_officer)
    @commands.check(Checks.guild_has_vacancy)
    async def invite(self, ctx, player : commands.MemberConverter):
        #Ensure target player has a character and is not in a guild
        if not await Checks.has_char(player):
            await ctx.reply('This person does not have a character.')
            return
        if not await Checks.target_not_in_guild(player):
            await ctx.reply('This player is already in an association.')
            return
        #Otherwise invite the player
        #Load the guild
        guild = await AssetCreation.getGuildFromPlayer(ctx.author.id)
        #Create and send embed invitation
        embed = discord.Embed(color=0xBEDCF6)
        embed.add_field(name=f"Invitation to {guild['Name']}", value=f"{player.mention}, {ctx.author.mention} is inviting you to join their {guild['Type']}.")

        message = await ctx.reply(embed=embed)
        await message.add_reaction('\u2705') #Check
        await message.add_reaction('\u274E') #X

        def check(reaction, user):
            return user == player

        reaction = None
        readReactions = True
        while readReactions: 
            if str(reaction) == '\u2705': #Then exchange stuff
                await message.delete()
                async with aiosqlite.connect(PATH) as conn:
                    await conn.execute('UPDATE Players SET guild = ?, guild_rank = "Member" WHERE user_id = ?', (guild['ID'], player.id))
                    await conn.commit()
                    await ctx.send(f"Welcome to {guild['Name']}, {player.mention}!")
                break
            if str(reaction) == '\u274E':
                await message.delete()
                await ctx.reply('They declined your invitation.')
                break

            try:
                reaction, user = await self.client.wait_for('reaction_add', check=check, timeout=15.0)
                await message.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                readReactions = not readReactions
                await message.delete()
                await ctx.send('They did not respond to your invitation.')

    @brotherhood.command(description='Lock/unlock your guild from letting anyone join without an invite.')
    @commands.check(Checks.is_guild_leader)
    async def lock(self, ctx):
        guild = await AssetCreation.getGuildFromPlayer(ctx.author.id)
        if guild['Join'] == 'open':
            async with aiosqlite.connect(PATH) as conn:
                await conn.execute('UPDATE guilds SET join_status = "closed" WHERE guild_id = ?', (guild['ID'],))
                await conn.commit()
                await ctx.reply('Your guild is now closed to new members. Players can only join your guild via invite.')
        else:
            async with aiosqlite.connect(PATH) as conn:
                await conn.execute('UPDATE guilds SET join_status = "open" WHERE guild_id = ?', (guild['ID'],))
                await conn.commit()
                await ctx.reply('Your guild is now open to members. Anyone may join with the `join` command!')

    @brotherhood.command(brief='<guild id : int>', description='Join the target guild if its open!')
    @commands.check(Checks.not_in_guild)
    async def join(self, ctx, guild_id : int):
        #Make sure that guild exists, is open, and has an open slot
        async with aiosqlite.connect(PATH) as conn:
            c = await conn.execute('SELECT guild_name, join_status FROM guilds WHERE guild_id = ?', (guild_id,))
            try:
                guild_name, join_status = await c.fetchone()
            except TypeError:
                await ctx.reply('That guild does not exist.')
                return
            if join_status != 'open':
                await ctx.reply('This guild is not accepting new members at this time.')
                return
            if not await Checks.target_guild_has_vacancy(guild_id):
                await ctx.reply('This guild has no open spaces at the moment.')
                return
        #Otherwise we can add them to the guild
            await conn.execute('UPDATE Players SET guild = ?, guild_rank = "Member" WHERE user_id = ?', (guild_id, ctx.author.id))
            await conn.commit()
            await ctx.reply(f"Welcome to {guild_name}! Use `brotherhood` or `guild` to see your new association.")

    @brotherhood.command(description='Leave your brotherhood.')
    @commands.check(Checks.in_brotherhood)
    @commands.check(Checks.is_not_guild_leader)
    async def leave(self, ctx):
        async with aiosqlite.connect(PATH) as conn:
            await conn.execute('UPDATE Players SET guild = NULL, guild_rank = NULL WHERE user_id = ?', (ctx.author.id,))
            await conn.commit()
            await ctx.reply('You left your brotherhood.')

    @brotherhood.command(brief='<money : int>', description='Donate to your association, increasing its xp!')
    @commands.check(Checks.in_brotherhood)
    async def contribute(self, ctx, donation : int):
        #Make sure they have the money they're paying and that the guild is <lvl 10
        guild = await AssetCreation.getGuildFromPlayer(ctx.author.id)
        level = await AssetCreation.getGuildLevel(guild['ID'])
        if level >= 10:
            await ctx.reply('Your guild is already at its maximum level')
            return
        async with aiosqlite.connect(PATH) as conn:
            c = await conn.execute('SELECT gold FROM players WHERE user_id = ?', (ctx.author.id,)) 
            account = await c.fetchone()
            if donation > account[0]:
                await ctx.reply('You don\'t have that much money to donate.')
                return
        #Remove money from account and add xp to guild
            await conn.execute('UPDATE players SET gold = gold - ? WHERE user_id = ?', (donation, ctx.author.id))
            await conn.execute('UPDATE guilds SET guild_xp = guild_xp + ? WHERE guild_id = ?', (donation, guild['ID']))
            await conn.commit()
        #Also calculate how much more xp is needed for a level up
            c = await conn.execute('SELECT guild_xp FROM guilds WHERE guild_id = ?', (guild['ID'],))
            xp = await c.fetchone()
            needed = 100000 - (xp[0] % 100000)
            await ctx.reply(f'You contributed `{donation}` gold to your brotherhood. It will become level `{level+1}` at `{needed}` more xp.')

    @brotherhood.command(description='View the other members of your guild.')
    @commands.check(Checks.in_brotherhood)
    async def members(self, ctx):
        # Get the list of members, theoretically sorted by rank
        guild = await AssetCreation.getGuildFromPlayer(ctx.author.id)
        async with aiosqlite.connect(PATH) as conn:
            c = await conn.execute("""SELECT user_id, user_name, guild_rank FROM players WHERE guild = ?
                ORDER BY CASE guild_rank WHEN "Leader" then 1
                WHEN "Officer" THEN 2
                WHEN "Adept" THEN 3
                ELSE 4 END""", (guild['ID'],))
            members = await c.fetchall()
        # Sort them into dpymenus pages
        member_list = []

        async def write(start, members):
            page = Page(title=f"{guild['Name']}: Members")
            iteration = 0

            while start < len(members) and iteration < 10:
                attack, crit = await AssetCreation.getAttack(members[start][0])
                level = await AssetCreation.getLevel(members[start][0])
                player = await self.client.fetch_user(members[start][0])
                page.add_field(name=f'{player.name}: {members[start][1]} [{members[start][2]}]', 
                    value=f'Level `{level}`, with `{attack}` attack and `{crit}` crit.', inline=False)
                start += 1
                iteration += 1

            return page

        for i in range(0, len(members), 10):
            member_list.append(await write(i, members))

        menu = PaginatedMenu(ctx)
        menu.add_pages(member_list)
        await menu.open()

    @brotherhood.command(brief='<player> <Officer/Adept>', description='Promote a member of your guild. Officers have limited administrative powers. Adepts have no powers. [LEADER ONLY]')
    @commands.check(Checks.is_guild_leader)        
    async def promote(self, ctx, player : commands.MemberConverter = None, rank : str = None):
        #Tell players what officers and adepts do if no input is given
        if player is None or rank is None:
            embed = discord.Embed(title='Brotherhood Role Menu', color=0xBEDCF6)
            embed.add_field(name='Guild leaders can promote their members to two other roles: Officer and Adept',
                value='**Officers** share in the administration of the association. They can invite and kick members, and change the guild\'s description.\n**Adepts** are a mark of seniority for members. They have no powers, but are stronger and more loyal than other members.')
            message = await ctx.reply(embed=embed)
            await asyncio.sleep(30)
            await message.delete()
            return
        #Ensure the rank input is valid
        if rank != "Officer" and rank != "Adept":
            await ctx.reply('That is not a valid rank. Please input `Officer` or `Adept`.')
            return
        #Otherwise check if player is in guild -> also not the leader
        if ctx.author == player:
            await ctx.reply('I don\'t think so.')
            return
        if not await Checks.has_char(player):
            await ctx.reply('This person does not have a character.')
            return
        if await Checks.target_not_in_guild(player):
            await ctx.reply('This person is not in your brotherhood.')
            return
        leader_guild = await AssetCreation.getGuildFromPlayer(ctx.author.id)
        target_guild = await AssetCreation.getGuildFromPlayer(player.id)
        if leader_guild['ID'] != target_guild['ID']:
            await ctx.reply('This person is not in your brotherhood.')
            return
        #Then give them their role
        async with aiosqlite.connect(PATH) as conn:
            await conn.execute('UPDATE players SET guild_rank = ? WHERE user_id = ?', (rank, player.id))
            await conn.commit()
            await ctx.reply(f'`{player.name}` is now an `{rank}`.')


        
    



def setup(client):
    client.add_cog(Associations(client))