import discord
from discord import app_commands
import asyncio
from openai import OpenAI
import os
import json
from dotenv import load_dotenv

### Set general variables

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

ai_client = OpenAI(
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio"
)

### Functions

# Get AI model name
def get_model_name():
    models = ai_client.models.list()
    
    if not models.data:
        return None
    
    return models.data[0].id

# Config file
def load_config():
    """Load configuration from config.json."""

    if not os.path.exists(CONFIG_FILE):
        config = {
            "personality": "You are a helpful AI assistant."
        }

        save_config(config)
        return config

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_config(config):
    """Save configuration to config.json."""

    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=4)

config = load_config()

### Slash commands

@tree.command(
    name="set-personality",
    description="Sets the personality for the AI",
)
async def set_personality(
    interaction: discord.Interaction,
    personality: str
):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "You don't have permission to use this command.",
            ephemeral=True
        )
        return

    config["personality"] = personality
    save_config(config)

    await interaction.response.send_message(
        f"Personality updated to:\n> {personality}"
    )

### Bot events

# Load bot
@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

# Prompt AI
@client.event
async def on_message(message):
    # Ignore message sent by the bot itself
    if message.author == client.user:
        return

    if message.content.startswith("!"):
        text = message.content[1:].strip()

        if not text:
            return

        # Check if the message is a reply
        replied_text = None

        if message.reference and message.reference.message_id:

            try:
                replied_message = await message.channel.fetch_message(
                    message.reference.message_id
                )

                replied_text = replied_message.content
            except discord.NotFound:
                replied_text = None

        # Build the prompt
        if replied_text:
            prompt = (
                f"The user is replying to this message:\n\n"
                f"--- Message being replied to ---\n"
                f"{replied_text}\n"
                f"--- End message ---\n\n"
                f"The user's reply is:\n"
                f"{text}"
            )
        else:
            prompt = text

        # Send the prompt
        model_name = get_model_name()
        if model_name:
            async with message.channel.typing():
                response = await asyncio.to_thread(
                    ai_client.chat.completions.create,
                    model=model_name,
                    messages=[
                        {"role": "system", "content": config["personality"]},
                        {"role": "user", "content": prompt}
                    ]
                )

            ai_message = response.choices[0].message.content
            if len(ai_message) > 2000:
                await message.channel.send(
                    f"Error: The AI response is too long to send to Discord "
                    f"({len(ai_message)} characters, maximum is 2000)."
                )
            else:
                await message.channel.send(ai_message)

client.run(TOKEN)