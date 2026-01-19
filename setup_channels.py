#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord Server Channel Setup Script
Creates all required channels and roles for the tier system
Run this script once after deployment to set up the server structure
"""

import discord
from discord.ext import commands
import asyncio
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Channel and role configuration
ROLES_TO_CREATE = ['Free', 'Standard', 'Instant']

# Only create channels that don't exist yet
CHANNELS_TO_CREATE = {
    '📦 STANDARD FEED': {
        'channels': ['standard-feed'],
        'permissions': {
            'Standard': {'read_messages': True, 'send_messages': False},
            'Instant': {'read_messages': True, 'send_messages': False}
        }
    }
}

# All brand channels (for reference, but won't create if they exist)
# IMPORTANT: Channel names must match BRAND_CHANNEL_MAP in secure_discordbot.py
ALL_BRAND_CHANNELS = [
    # Original brands
    'raf-simons', 'rick-owens', 'maison-margiela', 'jean-paul-gaultier',
    'yohji-yamamoto', 'junya-watanabe', 'undercover', 'vetements',
    'comme-des-garcons', 'martine-rose', 'balenciaga', 'alyx',
    'celine', 'bottega-veneta', 'kiko-kostadinov', 'prada',
    'miu-miu', 'chrome-hearts', 'gosha-rubchinskiy', 'helmut-lang',
    'hysteric-glamour', 'issey-miyake',
    # Missing brands that were in brands.json but not setup_channels.py
    'sacai', 'number-nine', 'soloist', 'doublet', 'thom-browne',
    'lgb', 'dior', 'balmain', 'chanel', '14th-addiction', 'dolce-gabanna',
    # New brands
    'saint-laurent'
]

# Existing channels that should have permissions updated
EXISTING_CHANNELS_TO_UPDATE = {
    '📊 DIGEST': {
        'channels': ['daily-digest'],
        'permissions': {
            'Free': {'read_messages': True, 'send_messages': False},
            'Standard': {'read_messages': True, 'send_messages': False},
            'Instant': {'read_messages': True, 'send_messages': False}
        }
    },
    '🎯 INSTANT ALERTS': {
        'channels': ['auction-alerts', 'ending-soon', 'budget-steals', 'new-listings', 'buy-it-now'],
        'permissions': {
            'Instant': {'read_messages': True, 'send_messages': False}
        }
    },
    '🏷️ BRAND CHANNELS': {
        'channels': ALL_BRAND_CHANNELS,
        'permissions': {
            'Instant': {'read_messages': True, 'send_messages': False}
        }
    }
}

@bot.event
async def on_ready():
    """Bot ready event"""
    logger.info(f'✅ Bot logged in as {bot.user}')
    logger.info(f'📊 Connected to {len(bot.guilds)} guild(s)')
    
    # Get the first guild (assuming single server deployment)
    if bot.guilds:
        guild = bot.guilds[0]
        logger.info(f'🏠 Setting up server: {guild.name}')
        await setup_server_channels(guild)
    else:
        logger.error('❌ No guilds found! Make sure the bot is in a server.')

async def setup_server_channels(guild):
    """Create required channels and roles, update existing ones"""
    try:
        logger.info('🚀 Starting server setup...')
        
        # 1. Create roles
        await create_roles(guild)
        
        # 2. Create only new channels that don't exist
        await create_new_channels(guild)
        
        # 3. Update permissions for existing channels
        await update_existing_channel_permissions(guild)
        
        logger.info('✅ Server setup completed successfully!')
        
    except Exception as e:
        logger.error(f'❌ Server setup failed: {e}')
        raise

async def create_roles(guild):
    """Create required roles"""
    logger.info('👥 Creating roles...')
    
    for role_name in ROLES_TO_CREATE:
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            logger.info(f'✅ Role {role_name} already exists')
            continue
        
        try:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.blue(),
                mentionable=True,
                reason='Tier system role creation'
            )
            logger.info(f'✅ Created role: {role_name}')
        except Exception as e:
            logger.error(f'❌ Failed to create role {role_name}: {e}')

async def create_new_channels(guild):
    """Create only new channels that don't exist"""
    logger.info('📁 Creating new channels...')
    
    for category_name, config in CHANNELS_TO_CREATE.items():
        try:
            # Create or get category
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                category = await guild.create_category(category_name)
                logger.info(f'✅ Created category: {category_name}')
            else:
                logger.info(f'✅ Category {category_name} already exists')
            
            # Create channels in category
            for channel_name in config['channels']:
                existing_channel = discord.utils.get(guild.channels, name=channel_name)
                if existing_channel:
                    logger.info(f'✅ Channel #{channel_name} already exists - skipping')
                    continue
                
                try:
                    channel = await guild.create_text_channel(
                        channel_name,
                        category=category,
                        reason='Tier system channel creation'
                    )
                    logger.info(f'✅ Created channel: #{channel_name}')
                except Exception as e:
                    logger.error(f'❌ Failed to create channel #{channel_name}: {e}')
        
        except Exception as e:
            logger.error(f'❌ Failed to create category {category_name}: {e}')

async def update_existing_channel_permissions(guild):
    """Update permissions for existing channels"""
    logger.info('🔐 Updating permissions for existing channels...')
    
    # Get roles
    free_role = discord.utils.get(guild.roles, name='Free')
    standard_role = discord.utils.get(guild.roles, name='Standard')
    instant_role = discord.utils.get(guild.roles, name='Instant')
    
    if not all([free_role, standard_role, instant_role]):
        logger.error('❌ Not all required roles found!')
        return
    
    # Update permissions for existing channels
    for category_name, config in EXISTING_CHANNELS_TO_UPDATE.items():
        logger.info(f'🔧 Updating permissions for {category_name} channels...')
        
        for channel_name in config['channels']:
            channel = discord.utils.get(guild.channels, name=channel_name)
            if channel:
                await set_channel_permissions(channel, config['permissions'], free_role, standard_role, instant_role)
                logger.info(f'✅ Updated permissions for #{channel_name}')
            else:
                logger.warning(f'⚠️ Channel #{channel_name} not found - skipping')


async def set_category_permissions(category, permissions, free_role, standard_role, instant_role):
    """Set permissions for a category"""
    try:
        # Deny access to @everyone by default
        await category.set_permissions(guild.default_role, read_messages=False)
        
        # Set role permissions
        for role_name, perms in permissions.items():
            role = None
            if role_name == 'Free':
                role = free_role
            elif role_name == 'Standard':
                role = standard_role
            elif role_name == 'Instant':
                role = instant_role
            
            if role:
                await category.set_permissions(role, **perms)
                logger.info(f'✅ Set {role_name} permissions for category {category.name}')
    
    except Exception as e:
        logger.error(f'❌ Failed to set category permissions: {e}')

async def set_channel_permissions(channel, permissions, free_role, standard_role, instant_role):
    """Set permissions for a channel"""
    try:
        # Deny access to @everyone by default
        await channel.set_permissions(guild.default_role, read_messages=False)
        
        # Set role permissions
        for role_name, perms in permissions.items():
            role = None
            if role_name == 'Free':
                role = free_role
            elif role_name == 'Standard':
                role = standard_role
            elif role_name == 'Instant':
                role = instant_role
            
            if role:
                await channel.set_permissions(role, **perms)
                logger.info(f'✅ Set {role_name} permissions for channel #{channel.name}')
    
    except Exception as e:
        logger.error(f'❌ Failed to set channel permissions: {e}')

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Manual setup command for administrators"""
    try:
        await setup_server_channels(ctx.guild)
        await ctx.send('✅ Server setup completed!')
    except Exception as e:
        await ctx.send(f'❌ Setup failed: {e}')

@bot.command()
@commands.has_permissions(administrator=True)
async def check_setup(ctx):
    """Check if server is properly set up"""
    try:
        guild = ctx.guild
        
        # Check roles
        missing_roles = []
        for role_name in ROLES_TO_CREATE:
            if not discord.utils.get(guild.roles, name=role_name):
                missing_roles.append(role_name)
        
        # Check only channels that should be created
        missing_channels = []
        for category_name, config in CHANNELS_TO_CREATE.items():
            for channel_name in config['channels']:
                if not discord.utils.get(guild.channels, name=channel_name):
                    missing_channels.append(channel_name)
        
        # Check existing channels that should have permissions
        existing_channels_status = []
        for category_name, config in EXISTING_CHANNELS_TO_UPDATE.items():
            for channel_name in config['channels']:
                channel = discord.utils.get(guild.channels, name=channel_name)
                if channel:
                    existing_channels_status.append(f"✅ #{channel_name}")
                else:
                    existing_channels_status.append(f"❌ #{channel_name}")
        
        # Create status embed
        embed = discord.Embed(
            title="🔍 Server Setup Status",
            color=discord.Color.blue()
        )
        
        if missing_roles:
            embed.add_field(
                name="❌ Missing Roles",
                value="\n".join(missing_roles),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Roles",
                value="All required roles exist",
                inline=False
            )
        
        if missing_channels:
            embed.add_field(
                name="❌ Missing New Channels",
                value="\n".join(missing_channels),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ New Channels",
                value="All required new channels exist",
                inline=False
            )
        
        # Show existing channels status (limit to first 10)
        embed.add_field(
            name="📋 Existing Channels Status",
            value="\n".join(existing_channels_status[:10]),
            inline=False
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f'❌ Check failed: {e}')

@bot.command()
@commands.has_permissions(administrator=True)
async def cleanup(ctx):
    """Clean up only newly created channels and roles (use with caution!)"""
    try:
        guild = ctx.guild
        
        # Delete only channels that were created by this script
        for category_name, config in CHANNELS_TO_CREATE.items():
            for channel_name in config['channels']:
                channel = discord.utils.get(guild.channels, name=channel_name)
                if channel:
                    await channel.delete()
                    logger.info(f'🗑️ Deleted channel: #{channel_name}')
        
        # Delete only categories that were created by this script
        for category_name in CHANNELS_TO_CREATE.keys():
            category = discord.utils.get(guild.categories, name=category_name)
            if category:
                await category.delete()
                logger.info(f'🗑️ Deleted category: {category_name}')
        
        # Delete roles
        for role_name in ROLES_TO_CREATE:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await role.delete()
                logger.info(f'🗑️ Deleted role: {role_name}')
        
        await ctx.send('✅ Cleanup completed! (Only deleted newly created items)')
        
    except Exception as e:
        await ctx.send(f'❌ Cleanup failed: {e}')

def main():
    """Main function to run the setup script"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error('❌ DISCORD_BOT_TOKEN environment variable not set!')
        return
    
    logger.info('🚀 Starting Discord bot for channel setup...')
    bot.run(token)

if __name__ == '__main__':
    main()
