import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from database.connection import init_db
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MMRBowling')

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set")


class MMRBowlingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.reactions = True

        super().__init__(
            command_prefix='!',  # Fallback prefix, mainly using slash commands
            intents=intents,
            help_command=None
        )

        self.guild_id = int(GUILD_ID) if GUILD_ID else None

    async def setup_hook(self):
        """
        Called when the bot is starting up.
        Load cogs and sync commands here.
        """
        logger.info("Setting up bot...")

        # Initialize database
        try:
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

        # Load cogs
        cogs_to_load = [
            'cogs.admin',
            'cogs.session',
            'cogs.player',
        ]

        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")

        # Sync commands
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands synced to guild {self.guild_id}")
        else:
            await self.tree.sync()
            logger.info("Commands synced globally")

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

        # Set bot status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="bowling scores"
            )
        )


def main():
    """Main entry point for the bot."""
    bot = MMRBowlingBot()

    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
