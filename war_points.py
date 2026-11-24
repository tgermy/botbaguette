from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")

# Python weekday(): 0=Lundi, 1=Mardi(J1), 2=Mercredi(J2), 3=Jeudi(J3), 4=Vendredi(J4), 5=Samedi(J5), 6=Dimanche
WEEKDAY_NAMES = {
    0: "Lundi",
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
    6: "Dimanche",
}

WEEKDAY_TO_WAR_DAY: Dict[int, Optional[int]] = {
    0: None,  # Lundi (repos)
    1: 1,     # Mardi = J1
    2: 2,     # Mercredi = J2
    3: 3,     # Jeudi = J3
    4: 4,     # Vendredi = J4
    5: 5,     # Samedi = J5
    6: None,  # Dimanche (repos)
}

# Coûts d'invocation moyens (Forge Master)
SKILL_SUMMON_COST = 40      # ~37-50 tickets par invocation selon l'arbre techno
MOUNT_SUMMON_COST = 50      # 48-50 clés par invocation
EGG_SUMMON_COST = 100       # 100 coquilles par œuf invoqué
EGG_MIN_HATCH_PTS = 400     # Minimum garanti (œuf Commun = +400, jusqu'à +65 000 Éternel)


def get_day_info(dt: datetime) -> Tuple[Optional[int], str]:
    """Retourne (numéro de jour de guerre 1..5 ou None, nom du jour en FR)."""
    wd = dt.weekday()
    return WEEKDAY_TO_WAR_DAY[wd], WEEKDAY_NAMES[wd]


def compute_day_potential(profile: Dict[str, Any], war_day: Optional[int]) -> Tuple[int, List[Tuple[str, int]]]:
    """
    Calcule les points potentiels de guerre de clan pour un jour donné (J1..J5)
    à partir des ressources et fusions du profil.
    Retourne (total_points, [(emoji_key, points), ...]).
    """
    if war_day is None:
        return 0, []

    marteaux = int(profile.get("marteaux") or 0)
    competences = int(profile.get("competences") or 0)
    cles_monture = int(profile.get("cles_monture") or 0)
    oeufs = int(profile.get("oeufs") or 0)
    fusion_montures = int(profile.get("fusion_montures") or 0)
    fusion_pets = int(profile.get("fusion_pets") or 0)

    # Paramètres secrets stockés par joueur (repli sur les estimations par défaut)
    skill_cost = max(1.0, float(profile.get("skill_summon_cost") or SKILL_SUMMON_COST))
    mount_cost = max(1.0, float(profile.get("mount_summon_cost") or MOUNT_SUMMON_COST))
    egg_cost = max(1.0, float(profile.get("egg_summon_cost") or EGG_SUMMON_COST))
    forge_pts_j1 = int(profile.get("forge_tier_j1") or 5)
    forge_pts_j3 = int(profile.get("forge_tier_j3") or 4)

    breakdown: List[Tuple[str, int]] = []

    if war_day == 1:
        # J1 (Mardi) : Forge + Invocation compétence (+225)
        pts_forge = marteaux * forge_pts_j1
        pts_skills = int(competences // skill_cost) * 225
        if pts_forge:
            breakdown.append(("fm_hammer", pts_forge))
        if pts_skills:
            breakdown.append(("fm_ticket", pts_skills))

    elif war_day == 2:
        # J2 (Mercredi) : Invocation monture (+600) + Fusion monture (+600)
        pts_mount_summon = int(cles_monture // mount_cost) * 600
        pts_mount_merge = fusion_montures * 600
        if pts_mount_summon:
            breakdown.append(("fm_mountkey", pts_mount_summon))
        if pts_mount_merge:
            breakdown.append(("fm_mount_merge", pts_mount_merge))

    elif war_day == 3:
        # J3 (Jeudi) : Forge + Compétence (+175) + Éclosion œuf (+400 mini) + Fusion pet (+1250)
        pts_forge = marteaux * forge_pts_j3
        pts_skills = int(competences // skill_cost) * 175
        pts_eggs = int(oeufs // egg_cost) * EGG_MIN_HATCH_PTS
        pts_pet_merge = fusion_pets * 1250
        if pts_forge:
            breakdown.append(("fm_hammer", pts_forge))
        if pts_skills:
            breakdown.append(("fm_ticket", pts_skills))
        if pts_eggs:
            breakdown.append(("fm_egg", pts_eggs))
        if pts_pet_merge:
            breakdown.append(("fm_pet_merge", pts_pet_merge))

    elif war_day == 4:
        # J4 (Vendredi) : Invocation monture (+600) + Fusion monture (+600)
        pts_mount_summon = int(cles_monture // mount_cost) * 600
        pts_mount_merge = fusion_montures * 600
        if pts_mount_summon:
            breakdown.append(("fm_mountkey", pts_mount_summon))
        if pts_mount_merge:
            breakdown.append(("fm_mount_merge", pts_mount_merge))

    elif war_day == 5:
        # J5 (Samedi) : Forge + Éclosion œuf (+400 mini) + Fusion pet (+1250)
        pts_forge = marteaux * forge_pts_j3
        pts_eggs = int(oeufs // egg_cost) * EGG_MIN_HATCH_PTS
        pts_pet_merge = fusion_pets * 1250
        if pts_forge:
            breakdown.append(("fm_hammer", pts_forge))
        if pts_eggs:
            breakdown.append(("fm_egg", pts_eggs))
        if pts_pet_merge:
            breakdown.append(("fm_pet_merge", pts_pet_merge))

    total = sum(pts for _, pts in breakdown)
    return total, breakdown


def get_today_and_tomorrow_potentials(
    profile: Dict[str, Any],
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Retourne les projections pour aujourd'hui et demain (heure de Paris)."""
    current = now.astimezone(PARIS_TZ) if now is not None else datetime.now(PARIS_TZ)
    tomorrow = current + timedelta(days=1)

    results = []
    for label, dt in (("Aujourd'hui", current), ("Demain", tomorrow)):
        war_day, day_name = get_day_info(dt)
        total, breakdown = compute_day_potential(profile, war_day)
        results.append(
            {
                "prefix": label,
                "war_day": war_day,
                "day_name": day_name,
                "total": total,
                "breakdown": breakdown,
            }
        )
    return results
