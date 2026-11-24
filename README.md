# botbaguette

Bot Discord **Forge Master** pour le clan **Baguette6**.

## Fonctionnalités

- **`/profil [membre]`** : affiche le profil Forge Master avec les vrais assets du jeu synchronisés automatiquement en Application Emojis au démarrage :
  - **Ressources** : Marteaux, Compétences, Clés Monture, Potions, Fioles vertes, Œufs.
  - **Fusions disponibles** : Montures et Pets à fusionner.
  - **Points potentiels** : projection automatique pour **Aujourd'hui** et **Demain** selon le calendrier de guerre de clan (`J1 = Mardi` à `J5 = Samedi`, heure de Paris).
- **Paramétrage interactif** : 8 boutons avec modales Discord pré-remplies (supporte `181032`, `14.4k`, `75.1k`, `2.08m`…) et mise à jour en direct de l'embed.
- **Persistance SQLite** automatique dans `botbaguette.db` (incluant des champs de calibration cachés pour affiner le calcul des points).

## Installation & Lancement

```bash
pip install -r requirements.txt
```

Créez `credential.py` à la racine du dépôt :

```python
token = "VOTRE_TOKEN_DISCORD"
```

*(ou définissez la variable d'environnement `DISCORD_TOKEN`)*

Puis lancez le bot :

```bash
python command.py
```

## Tests

```bash
python -m unittest discover -s tests -v
```
