import discord
from datetime import datetime, timedelta
import asyncio
import pytz
import os
import logging
import requests

# Replace with your bot token (keep this secret)
BOT_TOKEN = 'discord_bot_token'

# Replace with the ID of the target guild (use developer mode to copy ID)
TARGET_GUILD_ID = 994733084341702736 # test server

# Replace with the ID of the target channel within the guild (use developer mode to copy ID)
TARGET_CHANNEL_ID = 1145944745311473785 # test channel

# Replace with the path to your video file (ensure the bot has access)
VIDEO_FILE_PATH = '/root/dennis/rrh.MP4'

# Schedule the video to be sent at this time EVERY DAY (adjust hours and minutes)
TARGET_TIME = (3, 00)  # Hour and minute as a tuple (3:00 AM)

# Time zone for scheduling (Eastern Standard Time)
TIMEZONE = pytz.timezone('US/Eastern')

# Telegram bot token and chat ID
TELEGRAM_BOT_TOKEN = 'telegram_bot_token'
TELEGRAM_CHAT_ID = 'your_chat_id'  # Replace with your chat ID

# Intents needed by the bot (replace with any others your bot requires)
intents = discord.Intents.default()
intents.messages = True  # Required for sending messages

client = discord.Client(intents=intents)
scheduled_task_running = False  # Flag to check if task is already running

# Set up logging to a file
LOG_FILE = 'bot_log.txt'
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user} (ID: {client.user.id})')
    logging.info(f'Working directory: {os.getcwd()}')
    logging.info(f'Video file path: {VIDEO_FILE_PATH}')
    
    global scheduled_task_running
    if not scheduled_task_running:
        scheduled_task_running = True
        client.loop.create_task(scheduled_task())
    client.loop.create_task(update_status())

@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignore bot's own messages

# send message to server, else fails and log error
async def send_video():
    guild = client.get_guild(TARGET_GUILD_ID)
    if not guild:
        logging.error(f'Could not find guild with ID {TARGET_GUILD_ID}')
        return

    channel = guild.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        logging.error(f'Could not find channel with ID {TARGET_CHANNEL_ID} within guild {guild.name}')
        return

    try:
        if os.path.exists(VIDEO_FILE_PATH):
            await channel.send(file=discord.File(VIDEO_FILE_PATH))
            logging.info(f'Video sent to channel {channel.name} at {datetime.now(TIMEZONE)}')
            
            # Send notification to Telegram
            send_telegram_message(f'Video sent to Discord channel {channel.name} at {datetime.now(TIMEZONE)}')
        else:
            logging.error(f'File not found: {VIDEO_FILE_PATH}')
    except Exception as e:
        logging.error(f'Failed to send video: {e}')
        send_telegram_message(f'Failed to send video to Discord. Error: {e}')

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

# logging the task scheduling
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

# timer until message send, displayed in status
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
        await client.change_presence(activity=discord.Game(name=status))
        await asyncio.sleep(60)  # Update status every minute

async def main():
    await client.start(BOT_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
