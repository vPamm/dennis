import discord
from discord.ext import commands
import asyncio
import datetime
import json

# Load configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

TOKEN = config["TOKEN"]
GUILD_ID = config["GUILD_ID"]
CHANNEL_ID = config["CHANNEL_ID"]
VIDEO_FILE_PATH = config["VIDEO_FILE_PATH"]
SEND_HOUR = config["SEND_HOUR"]
SEND_MINUTE = config["SEND_MINUTE"]

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def wait_until(target_time):
    now = datetime.datetime.now()
    future = datetime.datetime.combine(now, target_time)
    if future < now:
        future += datetime.timedelta(days=1)
    await asyncio.sleep((future - now).total_seconds())

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

    # Schedule the task to send the video at the specified time every day
    target_time = datetime.time(hour=SEND_HOUR, minute=SEND_MINUTE)

    while True:
        await wait_until(target_time)

        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        if guild is None:
            print("Guild not found. Double-check the provided GUILD_ID.")
            return

        channel = discord.utils.get(guild.channels, id=CHANNEL_ID)
        if channel is None:
            print("Channel not found. Double-check the provided CHANNEL_ID.")
            return

        try:
            await channel.send(file=discord.File(VIDEO_FILE_PATH))
            print(f"Successfully sent {VIDEO_FILE_PATH} to {channel.name}")
        except Exception as e:
            print(f"Failed to send video: {e}")

# Run the bot
bot.run(TOKEN)