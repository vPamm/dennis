import discord
from datetime import datetime, timedelta
import asyncio
import pytz
import os

# Replace with your bot token (keep this secret)
BOT_TOKEN = 'token'

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

# Intents needed by the bot (replace with any others your bot requires)
intents = discord.Intents.default()
intents.messages = True  # Required for sending messages

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print(f'Working directory: {os.getcwd()}')
    print(f'Video file path: {VIDEO_FILE_PATH}')
    client.loop.create_task(scheduled_task())
    client.loop.create_task(update_status())


@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignore bot's own messages

# send message to server, else fails and print to console
async def send_video():
    guild = client.get_guild(TARGET_GUILD_ID)
    if not guild:
        print(f'Could not find guild with ID {TARGET_GUILD_ID}')
        return

    channel = guild.get_channel(TARGET_CHANNEL_ID)
    if not channel:
        print(f'Could not find channel with ID {TARGET_CHANNEL_ID} within guild {guild.name}')
        return

    try:
        if os.path.exists(VIDEO_FILE_PATH):
            await channel.send(file=discord.File(VIDEO_FILE_PATH))
            print(f'Video sent to channel {channel.name} at {datetime.now(TIMEZONE)}')
        else:
            print(f'File not found: {VIDEO_FILE_PATH}')
    except Exception as e:
        print(f'Failed to send video: {e}')

# logging in console
async def scheduled_task():
    while True:
        now = datetime.now(TIMEZONE)
        target_time_today = now.replace(hour=TARGET_TIME[0], minute=TARGET_TIME[1], second=0, microsecond=0)
        print(f'Current time: {now}')
        print(f'Target time today: {target_time_today}')

        if now > target_time_today:
            target_time_today += timedelta(days=1)
            print(f'Target time adjusted to next day: {target_time_today}')

        time_until_target = (target_time_today - now).total_seconds()
        print(f'Sleeping for {time_until_target} seconds until the next video send time.')
        await asyncio.sleep(time_until_target)
        await send_video()

#timer until message send, displayed in status
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
