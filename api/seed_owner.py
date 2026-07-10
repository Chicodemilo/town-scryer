"""
Seed the owner account on first boot.
Run once: OWNER_PASSWORD=yourpassword python3 seed_owner.py

Creates the owner account with a real hashed password
and admin privileges. The password is read from the OWNER_PASSWORD
environment variable — never hardcode it. Username and email come
from OWNER_USERNAME / OWNER_EMAIL (with defaults). Safe to re-run —
skips if the account already exists.
"""
import os
import sys

# Add the api directory to path so we can import the app
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models.user import User
from app.models.user_preferences import UserPreferences
from werkzeug.security import generate_password_hash

owner_username = os.environ.get('OWNER_USERNAME', 'owner')
owner_email = os.environ.get('OWNER_EMAIL', 'owner@example.com')
owner_password = os.environ.get('OWNER_PASSWORD')
if not owner_password:
    print('Error: set the OWNER_PASSWORD environment variable, e.g.')
    print('  OWNER_PASSWORD=yourpassword python3 seed_owner.py')
    sys.exit(1)

app = create_app()

with app.app_context():
    # Check if already seeded
    existing = User.query.filter_by(email=owner_email).first()
    if existing:
        print(f'Owner account already exists (id={existing.id}, username={existing.username}). Skipping.')
        sys.exit(0)

    # Create owner account
    owner = User(
        username=owner_username,
        email=owner_email,
        password_hash=generate_password_hash(owner_password),
        email_verified=True,
        terms_accepted=True,
        is_admin=True,
        monthly_image_count=0,
        monthly_session_count=0,
    )
    db.session.add(owner)
    db.session.flush()  # get the id

    # Create default preferences
    prefs = UserPreferences(
        user_id=owner.id,
        game_type='fantasy_dnd',
        art_style='Oil Painting',
        rating='PG-13',
    )
    db.session.add(prefs)
    db.session.commit()

    print(f'Owner account created:')
    print(f'  Username: {owner_username}')
    print(f'  Email:    {owner_email}')
    print(f'  Password: (from OWNER_PASSWORD env var)')
    print(f'  Status:   admin')
    print(f'  ID:       {owner.id}')
