import discord
from datetime import datetime, timedelta

# Replace with your bot token (keep this secret)
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# Replace with the ID of the target guild (use developer mode to copy ID)
TARGET_GUILD_ID = 123456789012345678  # Example guild ID

# Replace with the ID of the target channel within the guild (use developer mode to copy ID)
TARGET_CHANNEL_ID = 123456789012345678  # Example channel ID

# Replace with the path to your video file (ensure the bot has access)
VIDEO_FILE_PATH = 'path/to/rrh.mp4'

# Schedule the video to be sent at this time EVERY DAY (adjust hours and minutes)
TARGET_TIME = datetime(hour=18, minute=0)  # Example time (6:00 PM)

client = discord.Client()

@client.event
async def on_ready():
  print(f'Logged in as {client.user} (ID: {client.user.id})')

@client.event
async def on_message(message):
  if message.author == client.user:
    return  # Ignore bot's own messages

  now = datetime.utcnow()

  # Check if it's time to send the video (considering year)
  if now.replace(year=TARGET_TIME.year, hour=TARGET_TIME.hour, minute=TARGET_TIME.minute) == TARGET_TIME:
    guild = client.get_guild(TARGET_GUILD_ID)
    if guild:
      channel = guild.get_channel(TARGET_CHANNEL_ID)
      if channel:
        await channel.send(file=discord.File(VIDEO_FILE_PATH))
        print(f'Video sent to channel {channel.name} at {now}')
      else:
        print(f'Could not find channel with ID {TARGET_CHANNEL_ID} within guild {guild.name}')
    else:
      print(f'Could not find guild with ID {TARGET_GUILD_ID}')

# Ensures the bot only runs when the target time is reached
async def scheduled_task():
  while True:
    now = datetime.utcnow()
    # Calculate the time difference until the target time today (considering year)
    target_time_today = TARGET_TIME.replace(year=now.year)
    time_until_target = target_time_today - now
    if time_until_target.total_seconds() <= 0:
      break
    await asyncio.sleep(time_until_target.total_seconds())

  await client.start(BOT_TOKEN)

client.loop.create_task(scheduled_task())
client.run()
