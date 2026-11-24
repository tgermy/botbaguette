import os
from datetime import datetime
from typing import Dict, Any, Optional, Union
import discord

import db
import war_points

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
GAME_ICON_URL = (
    "https://play-lh.googleusercontent.com/"
    "WGcdbzoUWweXOg3knrsZFyDCqODfblSjIsyDdsEnYot1DBdq4_p38QYN5z-vgS6LyphN5C8HPfSKQyEa6LGAUAk"
)

EMOJI_SPECS = {
    "fm_hammer":      ("fm_hammer.png",      "🔨"),
    "fm_ticket":      ("fm_ticket.png",      "🎟️"),
    "fm_mountkey":    ("fm_mountkey.png",    "🗝️"),
    "fm_potion":      ("fm_potion.png",      "🧪"),
    "fm_greenvial":   ("fm_greenvial.png",   "🧫"),
    "fm_egg":         ("fm_egg.png",         "🥚"),
    "fm_mount_merge": ("fm_mount_merge.png", "🐎"),
    "fm_pet_merge":   ("fm_pet_merge.png",   "🐾"),
}


async def sync_application_emojis(bot: discord.Client) -> Dict[str, discord.Emoji]:
    """Fetch or upload Forge Master sprites as Discord Application Emojis."""
    emoji_map: Dict[str, discord.Emoji] = {}
    try:
        existing = {e.name: e for e in await bot.fetch_application_emojis()}
    except Exception:
        return emoji_map

    for name, (filename, _fallback) in EMOJI_SPECS.items():
        if name in existing:
            emoji_map[name] = existing[name]
            continue
        path = os.path.join(ASSETS_DIR, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                created = await bot.create_application_emoji(name=name, image=f.read())
                emoji_map[name] = created
        except Exception:
            pass
    return emoji_map


def emoji_str(emoji_map: Dict[str, discord.Emoji], key: str) -> str:
    em = emoji_map.get(key)
    if em is not None:
        return f"<:{em.name}:{em.id}>"
    return EMOJI_SPECS[key][1]


def button_emoji(emoji_map: Dict[str, discord.Emoji], key: str) -> Union[discord.PartialEmoji, str]:
    em = emoji_map.get(key)
    if em is not None:
        return discord.PartialEmoji(name=em.name, id=em.id)
    return EMOJI_SPECS[key][1]


def build_profile_embed(
    profile: Dict[str, Any],
    display_name: str,
    emoji_map: Dict[str, discord.Emoji],
    can_edit: bool = True,
    now: Optional[datetime] = None,
) -> discord.Embed:
    pseudo = profile.get("pseudo") or display_name
    e = lambda k: emoji_str(emoji_map, k)
    fmt = lambda k: db.format_amount(int(profile.get(k) or 0))

    embed = discord.Embed(
        title=f"Profil — {pseudo}",
        color=discord.Color.from_rgb(230, 126, 34),
        description=(
            "\u200b\n"
            f"• {e('fm_hammer')} **Marteaux :** `{fmt('marteaux')}`\n"
            f"• {e('fm_ticket')} **Compétences :** `{fmt('competences')}`\n"
            f"• {e('fm_mountkey')} **Clés Monture :** `{fmt('cles_monture')}`\n"
            f"• {e('fm_potion')} **Potions :** `{fmt('potions')}`\n"
            f"• {e('fm_greenvial')} **Fioles vertes :** `{fmt('fioles_vertes')}`\n"
            f"• {e('fm_egg')} **Œufs :** `{fmt('oeufs')}`"
        ),
    )
    embed.set_thumbnail(url=GAME_ICON_URL)

    embed.add_field(
        name="Fusions disponibles",
        value=(
            f"• {e('fm_mount_merge')} **Montures :** `{fmt('fusion_montures')}`\n"
            f"• {e('fm_pet_merge')} **Pets :** `{fmt('fusion_pets')}`"
        ),
        inline=False,
    )

    potentials = war_points.get_today_and_tomorrow_potentials(profile, now=now)
    pot_lines = []
    for item in potentials:
        wday = item["war_day"]
        day_name = item["day_name"]
        prefix = item["prefix"]
        if wday is None:
            pot_lines.append(f"• **{prefix} ({day_name}) :** *Hors guerre*")
        else:
            total_str = db.format_amount(item["total"])
            if item["breakdown"]:
                parts = " • ".join(f"{e(k)} `{db.format_amount(v)}`" for k, v in item["breakdown"])
                pot_lines.append(f"• **{prefix} (J{wday} — {day_name}) :** `~{total_str} pts`\n  └ {parts}")
            else:
                pot_lines.append(f"• **{prefix} (J{wday} — {day_name}) :** `0 pts`")

    embed.add_field(
        name="Points potentiels",
        value="\n".join(pot_lines),
        inline=False,
    )

    footer_text = (
        "Cliquez sur un bouton ci-dessous pour paramétrer vos ressources ou fusions."
        if can_edit
        else f"Profil Forge Master de {pseudo}"
    )
    embed.set_footer(text=footer_text)
    return embed


class AmountModal(discord.ui.Modal):
    def __init__(
        self,
        view: "ProfileView",
        field_key: str,
        label: str,
        current_value: int,
    ):
        super().__init__(title=f"Modifier — {label}")
        self.profile_view = view
        self.field_key = field_key
        self.amount_input = discord.ui.TextInput(
            label=f"Nombre ({label})",
            placeholder="Ex: 181032, 14.4k, 75.1k, 697",
            default=str(current_value),
            required=True,
            max_length=20,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            parsed = db.parse_amount(self.amount_input.value)
        except ValueError as err:
            return await interaction.response.send_message(f"❌ {err}", ephemeral=True)

        profile = db.update_profile(
            self.profile_view.user_id,
            {self.field_key: parsed, "pseudo": interaction.user.display_name},
            db_path=self.profile_view.db_path,
        )
        embed = build_profile_embed(profile, interaction.user.display_name, self.profile_view.emoji_map, can_edit=True)
        await interaction.response.edit_message(embed=embed, view=self.profile_view)


class ProfileView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        emoji_map: Dict[str, discord.Emoji],
        db_path: Optional[str] = None,
        timeout: float = 600,
    ):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.emoji_map = emoji_map
        self.db_path = db_path

        buttons = [
            # Row 0: Ressources
            ("marteaux",        "Marteaux",        "fm_hammer",      discord.ButtonStyle.secondary, 0),
            ("competences",     "Compétences",     "fm_ticket",      discord.ButtonStyle.secondary, 0),
            ("cles_monture",    "Clés Monture",    "fm_mountkey",    discord.ButtonStyle.secondary, 0),
            ("potions",         "Potions",         "fm_potion",      discord.ButtonStyle.secondary, 0),
            # Row 1: Fioles vertes, Œufs & Fusions
            ("fioles_vertes",   "Fioles vertes",   "fm_greenvial",   discord.ButtonStyle.secondary, 1),
            ("oeufs",           "Œufs",            "fm_egg",         discord.ButtonStyle.secondary, 1),
            ("fusion_montures", "Fusion Montures", "fm_mount_merge", discord.ButtonStyle.primary,   1),
            ("fusion_pets",     "Fusion Pets",     "fm_pet_merge",   discord.ButtonStyle.primary,   1),
        ]

        for field_key, label, icon_key, style, row in buttons:
            btn = discord.ui.Button(
                label=label,
                emoji=button_emoji(emoji_map, icon_key),
                style=style,
                row=row,
                custom_id=f"fm_cfg_{field_key}",
            )
            btn.callback = self._make_callback(field_key, label)
            self.add_item(btn)

    async def _check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ Seul le propriétaire de ce profil peut le modifier. Utilise `/profil` pour le tien.",
                ephemeral=True,
            )
            return False
        return True

    def _make_callback(self, field_key: str, label: str):
        async def callback(interaction: discord.Interaction):
            if not await self._check_owner(interaction):
                return
            profile = db.get_or_create_profile(self.user_id, interaction.user.display_name, db_path=self.db_path)
            modal = AmountModal(self, field_key, label, int(profile.get(field_key) or 0))
            await interaction.response.send_modal(modal)

        return callback
