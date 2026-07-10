# ==============================================================================
# File:      api/app/services/seed_service.py
# Purpose:   Seeds demo DMs, players, tables, characters, and preferences for
#            development. Run standalone or import seed_demo_data().
# Callers:   CLI (python3 api/app/services/seed_service.py [--clear])
# Callees:   models/user.py, models/game_table.py, models/table_member.py,
#            models/player_character.py, models/user_preferences.py,
#            SQLAlchemy (db), werkzeug.security
# Modified:  2026-06-03
# ==============================================================================
import os
import sys
import argparse
import logging

# When run standalone, ensure the api directory is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.models.user import User
from app.models.game_table import GameTable
from app.models.table_member import TableMember
from app.models.player_character import PlayerCharacter
from app.models.user_preferences import UserPreferences
from werkzeug.security import generate_password_hash
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo data definitions
# ---------------------------------------------------------------------------

DEMO_DMS = [
    {
        'username': 'Grimjaw_DM',
        'email': 'grimjaw@example.com',
        'table_name': "Grimjaw's Descent into Avernus",
        'prefs': {'game_type': 'fantasy_dnd', 'art_style': 'frazetta', 'rating': 'R'},
    },
    {
        'username': 'LadyHex',
        'email': 'ladyhex@example.com',
        'table_name': "The Hexblood Chronicles",
        'prefs': {'game_type': 'horror', 'art_style': 'watercolor', 'rating': 'PG-13'},
    },
    {
        'username': 'OldManDungeon',
        'email': 'oldmandungeon@example.com',
        'table_name': "Old Man's Tomb of Annihilation",
        'prefs': {'game_type': 'fantasy_dnd', 'art_style': 'retro_add', 'rating': 'PG'},
    },
]

DEMO_PLAYERS = [
    {
        'username': 'RogueOfShadows',
        'email': 'rogue@example.com',
        'character': {'name': 'Vex Nighthollow', 'description': 'Tiefling rogue with crimson skin and a tattered black cloak. Twin daggers at the hip, one eye scarred shut.'},
    },
    {
        'username': 'PaladinPete',
        'email': 'paladin@example.com',
        'character': {'name': 'Ser Aldric Dawnforge', 'description': 'Human paladin in dented silver plate. Greatsword wreathed in faint golden light. Square jaw, cropped grey hair.'},
    },
    {
        'username': 'WildMage99',
        'email': 'wildmage@example.com',
        'character': {'name': 'Zephyra Sparkmantle', 'description': 'Gnome wild magic sorcerer. Bright purple hair that crackles with static. Oversized goggles, singed robes.'},
    },
    {
        'username': 'BarbarianBex',
        'email': 'barbarian@example.com',
        'character': {'name': 'Bex Ironjaw', 'description': 'Half-orc barbarian covered in tribal tattoos. Massive greataxe strapped to her back. Missing two teeth and proud of it.'},
    },
    {
        'username': 'ClericOfTheMoon',
        'email': 'cleric@example.com',
        'character': {'name': 'Lunara Tidewalker', 'description': 'Sea-elf cleric of the moon goddess. Flowing silver hair, pale blue skin, coral-and-shell holy symbol.'},
    },
    {
        'username': 'BardBardBard',
        'email': 'bard@example.com',
        'character': {'name': 'Finnegan Lark', 'description': 'Halfling bard with a lute bigger than he is. Patchwork vest, feathered cap, infectious grin.'},
    },
]

# Map: DM index -> list of player indices assigned to their table
TABLE_ASSIGNMENTS = {
    0: [0, 1],        # Grimjaw's table: Vex, Aldric
    1: [2, 3],        # LadyHex's table: Zephyra, Bex
    2: [4, 5],        # OldMan's table: Lunara, Finnegan
}

# Players who also join the owner's table (indices into DEMO_PLAYERS)
OWNER_TABLE_PLAYERS = [0, 3, 5]  # Vex, Bex, Finnegan

OWNER_TABLE_NAME = "Friday Night Game"

DEMO_PASSWORD = 'DemoPass123!'


# ---------------------------------------------------------------------------
# Clear function
# ---------------------------------------------------------------------------

def clear_demo_data():
    """Delete all non-admin users and their associated data."""
    admin = User.query.filter_by(is_admin=True).first()
    admin_id = admin.id if admin else None

    # Delete in FK order: characters -> members -> tables -> preferences -> users
    if admin_id:
        # Delete characters for non-admin users
        PlayerCharacter.query.filter(PlayerCharacter.user_id != admin_id).delete()
        # Delete all characters on non-admin-owned tables
        non_admin_tables = GameTable.query.filter(GameTable.owner_user_id != admin_id).all()
        for t in non_admin_tables:
            PlayerCharacter.query.filter_by(table_id=t.id).delete()

        # Delete members for non-admin users
        TableMember.query.filter(TableMember.user_id != admin_id).delete()
        # Delete admin's non-owner memberships on tables that will be deleted
        for t in non_admin_tables:
            TableMember.query.filter_by(table_id=t.id).delete()

        # Delete tables owned by admin (except keep admin clean)
        GameTable.query.filter(GameTable.owner_user_id == admin_id).delete()
        # Delete tables owned by non-admin users
        GameTable.query.filter(GameTable.owner_user_id != admin_id).delete()

        # Delete preferences for non-admin users
        UserPreferences.query.filter(UserPreferences.user_id != admin_id).delete()

        # Delete non-admin users
        User.query.filter(User.id != admin_id).delete()
    else:
        # No admin — nuke everything
        PlayerCharacter.query.delete()
        TableMember.query.delete()
        GameTable.query.delete()
        UserPreferences.query.delete()
        User.query.delete()

    db.session.commit()
    print('Cleared all demo data.')


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed_demo_data():
    """Seed demo DMs, players, tables, characters, and preferences."""
    admin = User.query.filter_by(is_admin=True).first()
    if not admin:
        print('No admin user found. Run seed_owner.py first.')
        return

    # Check idempotency — skip if demo users exist
    existing = User.query.filter_by(email=DEMO_DMS[0]['email']).first()
    if existing:
        print('Demo data already exists. Use --clear to reset.')
        return

    created_counts = {'dms': 0, 'players': 0, 'tables': 0, 'members': 0, 'characters': 0}

    # --- Create DM users + their tables ---
    dm_users = []
    dm_tables = []
    for dm in DEMO_DMS:
        user = User(
            username=dm['username'],
            email=dm['email'],
            password_hash=generate_password_hash(DEMO_PASSWORD),
            email_verified=True,
            terms_accepted=True,
            terms_accepted_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.flush()
        dm_users.append(user)
        created_counts['dms'] += 1

        # Preferences
        prefs = UserPreferences(
            user_id=user.id,
            game_type=dm['prefs']['game_type'],
            art_style=dm['prefs']['art_style'],
            rating=dm['prefs']['rating'],
        )
        db.session.add(prefs)

        # Table
        table = GameTable(
            owner_user_id=user.id,
            name=dm['table_name'],
        )
        db.session.add(table)
        db.session.flush()
        dm_tables.append(table)
        created_counts['tables'] += 1

        # DM as owner member
        db.session.add(TableMember(
            table_id=table.id,
            user_id=user.id,
            role='owner',
        ))
        created_counts['members'] += 1

    # --- Create player users ---
    player_users = []
    for p in DEMO_PLAYERS:
        user = User(
            username=p['username'],
            email=p['email'],
            password_hash=generate_password_hash(DEMO_PASSWORD),
            email_verified=True,
            terms_accepted=True,
            terms_accepted_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.flush()
        player_users.append(user)
        created_counts['players'] += 1

    # --- Assign players to DM tables ---
    for dm_idx, player_indices in TABLE_ASSIGNMENTS.items():
        table = dm_tables[dm_idx]
        for pi in player_indices:
            player = player_users[pi]
            char_data = DEMO_PLAYERS[pi]['character']

            db.session.add(TableMember(
                table_id=table.id,
                user_id=player.id,
                role='player',
            ))
            created_counts['members'] += 1

            db.session.add(PlayerCharacter(
                user_id=player.id,
                table_id=table.id,
                name=char_data['name'],
                description=char_data['description'],
            ))
            created_counts['characters'] += 1

    # --- Owner's table ---
    owner_table = GameTable(
        owner_user_id=admin.id,
        name=OWNER_TABLE_NAME,
    )
    db.session.add(owner_table)
    db.session.flush()
    created_counts['tables'] += 1

    # Admin as owner member
    db.session.add(TableMember(
        table_id=owner_table.id,
        user_id=admin.id,
        role='owner',
    ))
    created_counts['members'] += 1

    # Add select players to the owner's table with characters
    for pi in OWNER_TABLE_PLAYERS:
        player = player_users[pi]
        char_data = DEMO_PLAYERS[pi]['character']

        db.session.add(TableMember(
            table_id=owner_table.id,
            user_id=player.id,
            role='player',
        ))
        created_counts['members'] += 1

        db.session.add(PlayerCharacter(
            user_id=player.id,
            table_id=owner_table.id,
            name=char_data['name'],
            description=char_data['description'],
        ))
        created_counts['characters'] += 1

    db.session.commit()

    print(f'Seeded demo data:')
    print(f'  DMs:         {created_counts["dms"]}')
    print(f'  Players:     {created_counts["players"]}')
    print(f'  Tables:      {created_counts["tables"]} (3 DM + 1 admin)')
    print(f'  Members:     {created_counts["members"]}')
    print(f'  Characters:  {created_counts["characters"]}')


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Seed Town Scryer demo data')
    parser.add_argument('--clear', action='store_true',
                        help='Delete all demo data before seeding')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.clear:
            clear_demo_data()
        seed_demo_data()
