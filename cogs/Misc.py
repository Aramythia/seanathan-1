"""
A bunch of Misclaneous commands for testing purposes
"""
import discord
from discord.ext import commands

from discord.ext.commands import BucketType, cooldown, CommandOnCooldown

from Utilities import Checks, AssetCreation, PageSourceMaker

import time

class Misc(commands.Cog):
    def __init__(self,client):
        self.client=client

    #EVENTS
    @commands.Cog.listener() # needed to create event in cog
    async def on_ready(self): # YOU NEED SELF IN COGS
        print('Misc is ready.')

    #COMMANDS
    @commands.command(description='Invite Ayesha to your server!')
    async def invite(self, ctx):
        embed = discord.Embed(title='Click me to invite Ayesha to your server!',
            url = 'https://discord.com/api/oauth2/authorize?client_id=767234703161294858&permissions=70347841&scope=bot',
            color = 0xBEDCF6)
        # embed.set_image()

        await ctx.reply(embed=embed)

    # @commands.command(description='Greet Ayesha!')
    # async def hello(self,ctx):
    #     await ctx.message.channel.send('Hello!')

    # @commands.command(description='Lean.')
    # async def sean(self,ctx):
    #     await ctx.message.channel.send('Sean is short for Seanathan')

    # @commands.command(brief='<statement>', description='Ayesha will echo your statement.')
    # async def echo(self,ctx, *, returnStatement):
    #     await ctx.send(returnStatement)
        
    @commands.command(description='Link to a place to report bugs in AyeshaBot.')
    async def report(self,ctx):
        embed=discord.Embed(title="bug reporter", url="https://github.com/seanathan-discordbot/seanathan/issues", description="If you encounter what you believe to be a bug while using our bot please report it here", color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command(pass_context=True, aliases=['cd'], description='View any cooldowns your character has.')
    async def cooldowns(self, ctx):
        cooldowns = []
        for command in self.client.walk_commands():
            if command.is_on_cooldown(ctx):
                cooldowns.append((f'{command.name}', f'{time.strftime("%M:%S", time.gmtime(command.get_cooldown_retry_after(ctx)))}'))
        embed = discord.Embed(color=0xBEDCF6)
        if not cooldowns:
            await ctx.reply('You have no cooldowns.')
            return
        output = ""
        for cmd in cooldowns:
            output = output + f'`{cmd[0]}`: {cmd[1]}\n'
        embed.add_field(name=f'{ctx.author.display_name}\'s Cooldowns', value=output)
        await ctx.reply(embed=embed)

    @commands.command(description='Hi')
    async def leaderboard(self, ctx):
        board = await AssetCreation.getTopXP(self.client.pg_con)
        embed = discord.Embed(title='AyeshaBot Leaderboards', color=0xBEDCF6)
        
        output = ''
        for entry in board:
            player = await self.client.fetch_user(entry[0])
            output = output + f'**{player.name}#{player.discriminator}\'s** `{entry[1]}`: Level `{entry[2]}`, with `{entry[3]}` xp.\n'

        embed.add_field(name='Most Experienced Players', value=output)

        await ctx.reply(embed=embed)

    @commands.command(description='Hi')
    async def toppve(self, ctx):
        board = await AssetCreation.getTopBosses(self.client.pg_con)
        embed = discord.Embed(title='AyeshaBot Leaderboards', color=0xBEDCF6)
        
        output = ''
        for entry in board:
            player = await self.client.fetch_user(entry[0])
            output = output + f'**{player.name}#{player.discriminator}\'s** `{entry[1]}`: `{entry[2]}` bosses defeated.\n'

        embed.add_field(name='Most Bosses Defeated', value=output)

        await ctx.reply(embed=embed)

    @commands.command(description='Get 2 rubidics daily!')
    @commands.check(Checks.is_player)
    @cooldown(1, 86400, BucketType.user)
    async def daily(self, ctx):
        await AssetCreation.giveRubidics(self.client.pg_con, 2, ctx.author.id)
        await ctx.reply('You received 2 rubidics!')

def setup(client):
    client.add_cog(Misc(client))
