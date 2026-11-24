import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import db
import profile_ui
import war_points


class TestParsersAndDB(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        db.init_db(self.db_path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            p = self.db_path + suffix
            if os.path.exists(p):
                os.remove(p)

    def test_parse_amount_variants(self):
        self.assertEqual(db.parse_amount("181032"), 181032)
        self.assertEqual(db.parse_amount("181 032"), 181032)
        self.assertEqual(db.parse_amount("14.4k"), 14400)
        self.assertEqual(db.parse_amount("75,1K"), 75100)
        self.assertEqual(db.parse_amount("2.08m"), 2080000)
        with self.assertRaises(ValueError):
            db.parse_amount("abc")
        with self.assertRaises(ValueError):
            db.parse_amount("-50")

    def test_db_persistence(self):
        p = db.get_or_create_profile(12345, "Plolipop", db_path=self.db_path)
        self.assertEqual(p["pseudo"], "Plolipop")
        self.assertEqual(p["fioles_vertes"], 0)
        self.assertEqual(p["fusion_montures"], 0)
        self.assertEqual(p["fusion_pets"], 0)

        updated = db.update_profile(
            12345,
            {
                "marteaux": 181032,
                "fioles_vertes": 93,
                "fusion_montures": 697,
                "fusion_pets": 949,
            },
            db_path=self.db_path,
        )
        self.assertEqual(updated["marteaux"], 181032)
        self.assertEqual(updated["fioles_vertes"], 93)
        self.assertEqual(updated["fusion_montures"], 697)
        self.assertEqual(updated["fusion_pets"], 949)


class TestProfileUI(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        db.init_db(self.db_path)

    def tearDown(self):
        for suffix in ("", "-wal", "-shm"):
            p = self.db_path + suffix
            if os.path.exists(p):
                os.remove(p)

    def _mock_interaction(self, user_id: int, display_name: str = "Plolipop"):
        inter = MagicMock()
        inter.user = MagicMock()
        inter.user.id = user_id
        inter.user.display_name = display_name
        inter.response = MagicMock()
        inter.response.send_message = AsyncMock()
        inter.response.edit_message = AsyncMock()
        inter.response.send_modal = AsyncMock()
        return inter

    async def test_view_and_modals_end_to_end(self):
        view = profile_ui.ProfileView(1001, emoji_map={}, db_path=self.db_path)
        self.assertEqual(len(view.children), 8)

        # Stranger blocked
        stranger = self._mock_interaction(9999, "Intruder")
        self.assertFalse(await view._check_owner(stranger))
        stranger.response.send_message.assert_awaited_once()

        # Fioles vertes modal
        owner = self._mock_interaction(1001, "Plolipop")
        m1 = profile_ui.AmountModal(view, "fioles_vertes", "Fioles vertes", 0)
        m1.amount_input._value = "93"
        await m1.on_submit(owner)
        owner.response.edit_message.assert_awaited_once()

        # Fusion Montures modal
        owner2 = self._mock_interaction(1001, "Plolipop")
        m2 = profile_ui.AmountModal(view, "fusion_montures", "Fusion Montures", 0)
        m2.amount_input._value = "697"
        await m2.on_submit(owner2)

        # Fusion Pets modal
        owner3 = self._mock_interaction(1001, "Plolipop")
        m3 = profile_ui.AmountModal(view, "fusion_pets", "Fusion Pets", 0)
        m3.amount_input._value = "949"
        await m3.on_submit(owner3)

        p = db.get_or_create_profile(1001, db_path=self.db_path)
        self.assertEqual(p["fioles_vertes"], 93)
        self.assertEqual(p["fusion_montures"], 697)
        self.assertEqual(p["fusion_pets"], 949)

        embed = profile_ui.build_profile_embed(
            p,
            "Plolipop",
            emoji_map={},
            now=datetime(2026, 11, 24, 12, 0, tzinfo=war_points.PARIS_TZ),  # Mardi = J1
        )
        self.assertIn("Fioles vertes", embed.description)
        self.assertEqual(len(embed.fields), 2)
        self.assertEqual(embed.fields[0].name, "Fusions disponibles")
        self.assertIn("697", embed.fields[0].value)
        self.assertIn("949", embed.fields[0].value)
        self.assertEqual(embed.fields[1].name, "Points potentiels")
        self.assertIn("J1 — Mardi", embed.fields[1].value)
        self.assertIn("J2 — Mercredi", embed.fields[1].value)

    async def test_war_points_all_days(self):
        sample = {
            "marteaux": 1000,
            "competences": 400,     # 10 invocs
            "cles_monture": 500,    # 10 invocs
            "oeufs": 200,           # 2 invocs
            "fusion_montures": 10,
            "fusion_pets": 5,
        }
        # J1 Mardi: 1000*5 + 10*225 = 7250
        self.assertEqual(war_points.compute_day_potential(sample, 1)[0], 7250)
        # J2 Mercredi: 10*600 + 10*600 = 12000
        self.assertEqual(war_points.compute_day_potential(sample, 2)[0], 12000)
        # J3 Jeudi: 1000*4 + 10*175 + 2*400 + 5*1250 = 12800
        self.assertEqual(war_points.compute_day_potential(sample, 3)[0], 12800)
        # J4 Vendredi: 10*600 + 10*600 = 12000
        self.assertEqual(war_points.compute_day_potential(sample, 4)[0], 12000)
        # J5 Samedi: 1000*4 + 2*400 + 5*1250 = 11050
        self.assertEqual(war_points.compute_day_potential(sample, 5)[0], 11050)
        # Dimanche (None): 0
        self.assertEqual(war_points.compute_day_potential(sample, None)[0], 0)

        # Lundi (2026-11-23) -> Aujourd'hui Hors guerre, Demain J1 Mardi
        mon = datetime(2026, 11, 23, 12, 0, tzinfo=war_points.PARIS_TZ)
        pair = war_points.get_today_and_tomorrow_potentials(sample, now=mon)
        self.assertIsNone(pair[0]["war_day"])
        self.assertEqual(pair[1]["war_day"], 1)


if __name__ == "__main__":
    unittest.main()
