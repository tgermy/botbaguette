import os
from typing import Dict, Optional
import discord
from discord import app_commands
from discord.ext import commands

import db
import profile_ui


def load_token() -> str:
    try:
        import credential as cred
        if getattr(cred, "token", None):
            return cred.token
    except ImportError:
        pass
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Token Discord introuvable : crée un fichier credential.py (token = '...') ou définis DISCORD_TOKEN."
        )
    return token


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
emoji_map: Dict[str, discord.Emoji] = {}


@bot.tree.command(name="profil", description="Affiche et paramètre ton profil Forge Master")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(membre="Afficher le profil d'un autre membre du clan (optionnel)")
async def profil(interaction: discord.Interaction, membre: Optional[discord.User] = None):
    target = membre or interaction.user
    can_edit = target.id == interaction.user.id
    profile = db.get_or_create_profile(target.id, target.display_name)
    embed = profile_ui.build_profile_embed(profile, target.display_name, emoji_map, can_edit=can_edit)

    if can_edit:
        view = profile_ui.ProfileView(target.id, emoji_map)
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():
    global emoji_map
    db.init_db()
    emoji_map = await profile_ui.sync_application_emojis(bot)
    print(f"Connecté en tant que {bot.user} ({len(emoji_map)}/{len(profile_ui.EMOJI_SPECS)} assets chargés)")
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commande(s) synchronisée(s)")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")


def main():
    db.init_db()
    bot.run(load_token())


if __name__ == "__main__":
    main()
