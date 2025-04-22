import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import pytz
from datetime import datetime, timedelta
import logging
import requests
import wavelink
from wavelink import Node, Player, Pool, Playable, Playlist, exceptions
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Set up Spotipy credentials
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="",
    client_secret=""
))

BOT_TOKEN = ''
# Dictionary containing guilds and their corresponding channel IDs
TARGET_GUILDS = {
    GUILD_ID: CHANNEL_ID,  # Server 1
    GUILD_ID: CHANNEL_ID,  # Server 2
    # Add more guilds and channels as needed
}
VIDEO_FILE_PATH = 'rrh.mp4' # use the full path if on linux
TARGET_TIME = (3, 00)  # Hour and minute as a tuple (13:29 = 1:29 PM)
TIMEZONE = pytz.timezone('US/Eastern')

# Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = ''
TELEGRAM_CHAT_ID = ''  # Replace with your chat ID

# Set up basic discord Client (later we convert this into a Bot subclass)
intents = discord.Intents.default()
intents.messages = True
intents.voice_states = True

# Instead of using discord.Client, we use commands.Bot to allow slash commands.
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    await bot.tree.sync()
    logger.info("Slash commands synced!")
    await connect_to_lavalink()
    bot.loop.create_task(scheduled_task())
    bot.loop.create_task(update_status())

@bot.tree.command(name="ping", description="Responds with Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")


@bot.tree.command(name="play", description="Play a song from YouTube, Spotify, SoundCloud, etc.")
async def play(interaction: discord.Interaction, query: str):
    # 1) Make sure the user is in voice
    if not interaction.user.voice:
        return await interaction.response.send_message("You need to be in a voice channel first!")

    # 2) Connect or get existing player
    channel = interaction.user.voice.channel
    player: wavelink.Player = interaction.guild.voice_client or await channel.connect(cls=wavelink.Player)

    # 3) Search via the unified Playable API
    result = await Playable.search(query)   # returns Playlist or list[Playable]
    if not result:
        return await interaction.response.send_message("❌ No results found.")

    # 4) Normalize into a list of tracks
    tracks = result.tracks if isinstance(result, Playlist) else result

    # 5) Enqueue or play immediately
    track = tracks[0]
    if player.playing:
        await player.queue.put_wait(track)
        await interaction.response.send_message(f"➕ Enqueued **{track.title}**")
    else:
        await player.play(track)
        await interaction.response.send_message(f"▶️ Now playing **{track.title}**")

@bot.tree.command(name="pause", description="Pause the current track")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client.playing:
        voice_client.pause()
        await interaction.response.send_message("Paused the music.")
    else:
        await interaction.response.send_message("No music is currently playing.")

@bot.tree.command(name="skip", description="Skip the current track")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client.playing:
        voice_client.stop()
        await interaction.response.send_message("Skipped the current track.")
    else:
        await interaction.response.send_message("No music is currently playing.")

@bot.tree.command(name="stop", description="Stop the music and disconnect")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        voice_client.stop()
        await voice_client.disconnect()
        await interaction.response.send_message("Stopped the music and disconnected.")
    else:
        await interaction.response.send_message("The bot is not in a voice channel.")



# Function to connect to Lavalink

async def connect_to_lavalink():
    # 1) Instantiate a Node, not a dict
    lavalink_node = Node(
        uri="",    # the host:port of your Lavalink container
        password=""       # match your application.yml
        # optional: region="us_central", name="MyNode", etc.
    )

    # 2) Pass the Node object(s) into Pool.connect
    await Pool.connect(
        client=bot,
        nodes=[lavalink_node],
        # you can omit cache_capacity or set it as you like
    )

    logger.info("✅ Connected to Lavalink node.")

@bot.event
async def on_wavelink_node_disconnect(node):
    # this event fires when any Node drops
    logger.warning(f"⚠️ Lavalink node {node.identifier!r} disconnected. Reconnecting in 5 seconds...")
    await asyncio.sleep(5)

    try:
        # you can either reconnect just this node:
        await node.connect()
        logger.info("✅ Reconnected to Lavalink node.")
    except exceptions.ConnectionError as e:
        logger.error(f"Reconnection failed: {e}. Will retry on next disconnect event.")


# ---------------------------
# Real Raccoon Hours Code
# ---------------------------

# Send video to all configured servers
async def send_video():
    for guild_id, channel_id in TARGET_GUILDS.items():
        guild = bot.get_guild(guild_id)
        if not guild:
            logging.error(f'Could not find guild with ID {guild_id}')
            continue

        channel = guild.get_channel(channel_id)
        if not channel:
            logging.error(f'Could not find channel with ID {channel_id} within guild {guild.name}')
            continue

        try:
            if os.path.exists(VIDEO_FILE_PATH):
                await channel.send(file=discord.File(VIDEO_FILE_PATH))
                logging.info(f'Video sent to {channel.name} in {guild.name} at {datetime.now(TIMEZONE)}')
                
                # Send notification to Telegram
                send_telegram_message(f'Video sent to Discord channel {channel.name} in {guild.name} at {datetime.now(TIMEZONE)}')
            else:
                logging.error(f'File not found: {VIDEO_FILE_PATH}')
        except Exception as e:
            logging.error(f'Failed to send video to {guild.name}: {e}')
            send_telegram_message(f'Failed to send video to {guild.name}. Error: {e}')

# Function to send a message to Telegram
def send_telegram_message(message):
    try:
        telegram_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message
        }
        response = requests.get(telegram_url, params=params)
        if response.status_code == 200:
            logging.info(f'Telegram message sent: {message}')
        else:
            logging.error(f'Failed to send Telegram message. Status code: {response.status_code}')
    except Exception as e:
        logging.error(f'Error sending Telegram message: {e}')

# Scheduled task to send the video
async def scheduled_task():
    while True:
        now = datetime.now(TIMEZONE)
        target_time_today = now.replace(hour=TARGET_TIME[0], minute=TARGET_TIME[1], second=0, microsecond=0)
        logging.info(f'Current time: {now}')
        logging.info(f'Target time today: {target_time_today}')

        if now > target_time_today:
            target_time_today += timedelta(days=1)
            logging.info(f'Target time adjusted to next day: {target_time_today}')

        time_until_target = (target_time_today - now).total_seconds()
        logging.info(f'Sleeping for {time_until_target} seconds until the next video send time.')
        await asyncio.sleep(time_until_target)
        await send_video()

# Timer until message send, displayed in bot's status
async def update_status():
    while True:
        now = datetime.now(TIMEZONE)
        target_time_today = now.replace(hour=TARGET_TIME[0], minute=TARGET_TIME[1], second=0, microsecond=0)
        if now > target_time_today:
            target_time_today += timedelta(days=1)

        time_until_target = target_time_today - now
        hours, remainder = divmod(time_until_target.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        status = f'Time until Real Raccoon Hours: {hours}h {minutes}m {seconds}s'
        await bot.change_presence(activity=discord.Game(name=status))
        await asyncio.sleep(60)  # Update status every minute




# ---------------------------
# Run the Bot
# ---------------------------
bot.run(BOT_TOKEN)
