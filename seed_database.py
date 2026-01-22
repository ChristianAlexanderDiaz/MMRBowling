#!/usr/bin/env python3
"""
Database Seeding Script for MMR Bowling Bot

This script populates the database with initial configuration data:
- Rank tiers (Bronze, Silver, Gold, Platinum, Grandmaster)
- Config values (K-factor, decay settings)
- Bonus configurations (200 Club, 225 Club, etc.)

Safe to run multiple times - checks for existing data before inserting.

Usage:
    python seed_database.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal, init_db
from database.models import RankTier, Config, BonusConfig


def seed_rank_tiers(db):
    """Seed rank tier data."""
    print("\n=== Seeding Rank Tiers ===")

    # Destructive reset: clear existing rank tiers so we can seed a clean scale
    existing_count = db.query(RankTier).count()
    if existing_count > 0:
        print(f"  ⚠️  Removing {existing_count} existing rank tiers to reset scale")
        db.query(RankTier).delete()
        db.commit()

    rank_tiers = [
        {"rank_name": "Bronze", "mmr_threshold": 6600, "color": "#CD7F32", "order": 14},
        {"rank_name": "Bronze II", "mmr_threshold": 6800, "color": "#CD7F32", "order": 13},
        {"rank_name": "Bronze III", "mmr_threshold": 7000, "color": "#CD7F32", "order": 12},
        {"rank_name": "Silver", "mmr_threshold": 7200, "color": "#C0C0C0", "order": 11},
        {"rank_name": "Silver II", "mmr_threshold": 7400, "color": "#C0C0C0", "order": 10},
        {"rank_name": "Silver III", "mmr_threshold": 7600, "color": "#C0C0C0", "order": 9},
        {"rank_name": "Gold", "mmr_threshold": 7800, "color": "#FFD700", "order": 8},
        {"rank_name": "Gold II", "mmr_threshold": 8100, "color": "#FFD700", "order": 7},
        {"rank_name": "Platinum", "mmr_threshold": 8400, "color": "#4794FF", "order": 6},
        {"rank_name": "Platinum II", "mmr_threshold": 8700, "color": "#4794FF", "order": 5},
        {"rank_name": "Emerald", "mmr_threshold": 9000, "color": "#50C878", "order": 4},
        {"rank_name": "Ruby", "mmr_threshold": 9300, "color": "#E0115F", "order": 3},
        {"rank_name": "Diamond", "mmr_threshold": 9600, "color": "#B9F2FF", "order": 2},
        {"rank_name": "Master", "mmr_threshold": 10000, "color": "#000000", "order": 1},
        {"rank_name": "Grandmaster", "mmr_threshold": 11000, "color": "#7F0CA2", "order": 0},
    ]

    added = 0
    skipped = 0
    updated = 0

    for tier_data in rank_tiers:
        # Prefer updating the row at the target threshold (avoids UNIQUE conflicts)
        existing_threshold = db.query(RankTier).filter(
            RankTier.mmr_threshold == tier_data["mmr_threshold"]
        ).first()
        if existing_threshold:
            changes = []
            if existing_threshold.rank_name != tier_data["rank_name"]:
                existing_threshold.rank_name = tier_data["rank_name"]
                changes.append("rank_name")
            if existing_threshold.color != tier_data["color"]:
                existing_threshold.color = tier_data["color"]
                changes.append("color")
            if existing_threshold.order != tier_data["order"]:
                existing_threshold.order = tier_data["order"]
                changes.append("order")

            if changes:
                print(f"  🔁 Updated tier at threshold {tier_data['mmr_threshold']} -> '{tier_data['rank_name']}' ({', '.join(changes)})")
                updated += 1
            else:
                print(f"  ⏭️  Skipping '{tier_data['rank_name']}' (already exists at threshold)")
                skipped += 1
            continue

        # If threshold not present, check for a row with the same name and update its threshold safely
        existing_name = db.query(RankTier).filter(
            RankTier.rank_name == tier_data["rank_name"]
        ).first()
        if existing_name:
            changes = []
            if existing_name.mmr_threshold != tier_data["mmr_threshold"]:
                existing_name.mmr_threshold = tier_data["mmr_threshold"]
                changes.append("mmr_threshold")
            if existing_name.color != tier_data["color"]:
                existing_name.color = tier_data["color"]
                changes.append("color")
            if existing_name.order != tier_data["order"]:
                existing_name.order = tier_data["order"]
                changes.append("order")
            if changes:
                print(f"  🔄 Updated '{tier_data['rank_name']}' ({', '.join(changes)})")
                updated += 1
            else:
                print(f"  ⏭️  Skipping '{tier_data['rank_name']}' (already exists)")
                skipped += 1
        else:
            tier = RankTier(**tier_data)
            db.add(tier)
            print(f"  ✅ Added '{tier_data['rank_name']}' (MMR {tier_data['mmr_threshold']}+)")
            added += 1

    if added > 0 or updated > 0:
        db.commit()
    if added > 0:
        print(f"\n✅ Successfully added {added} rank tiers")
    if updated > 0:
        print(f"🔄 Updated {updated} rank tiers")
    if skipped > 0:
        print(f"⏭️  Skipped {skipped} existing rank tiers")


def seed_config(db):
    """Seed configuration values."""
    print("\n=== Seeding Config Values ===")

    configs = [
        {
            "key": "k_factor",
            "value": "100",
            "value_type": "int",
            "description": "K-factor for Elo calculations"
        },
        {
            "key": "decay_amount",
            "value": "200",
            "value_type": "int",
            "description": "MMR decay per miss after threshold"
        },
        {
            "key": "decay_threshold",
            "value": "4",
            "value_type": "int",
            "description": "Unexcused misses before decay starts"
        },
        {
            "key": "session_activation_threshold",
            "value": "3",
            "value_type": "int",
            "description": "Number of Game 1 submissions needed to activate session"
        },
    ]

    added = 0
    updated = 0

    for config_data in configs:
        existing = db.query(Config).filter(Config.key == config_data["key"]).first()

        if existing:
            # Update if value differs
            if existing.value != config_data["value"]:
                existing.value = config_data["value"]
                existing.description = config_data["description"]
                print(f"  🔄 Updated '{config_data['key']}' = {config_data['value']}")
                updated += 1
            else:
                print(f"  ⏭️  Skipping '{config_data['key']}' (already exists)")
        else:
            config = Config(**config_data)
            db.add(config)
            print(f"  ✅ Added '{config_data['key']}' = {config_data['value']}")
            added += 1

    if added > 0 or updated > 0:
        db.commit()
    if added > 0:
        print(f"\n✅ Successfully added {added} config values")
    if updated > 0:
        print(f"🔄 Updated {updated} config values")


def seed_bonus_config(db):
    """Seed bonus configuration."""
    print("\n=== Seeding Bonus Config ===")

    bonuses = [
        {
            "bonus_name": "200 Club",
            "bonus_amount": 5.0,
            "condition_type": "score_threshold",
            "condition_value": {"threshold": 200},
            "description": "Score 200+ in a game",
            "is_active": True
        },
        {
            "bonus_name": "225 Club",
            "bonus_amount": 8.0,
            "condition_type": "score_threshold",
            "condition_value": {"threshold": 225},
            "description": "Score 225+ in a game",
            "is_active": True
        },
        {
            "bonus_name": "250 Club",
            "bonus_amount": 12.0,
            "condition_type": "score_threshold",
            "condition_value": {"threshold": 250},
            "description": "Score 250+ in a game",
            "is_active": True
        },
        {
            "bonus_name": "275 Club",
            "bonus_amount": 18.0,
            "condition_type": "score_threshold",
            "condition_value": {"threshold": 275},
            "description": "Score 275+ in a game",
            "is_active": True
        },
        {
            "bonus_name": "Perfect Game",
            "bonus_amount": 50.0,
            "condition_type": "score_threshold",
            "condition_value": {"threshold": 300},
            "description": "Perfect 300 game",
            "is_active": True
        },
    ]

    added = 0
    skipped = 0

    for bonus_data in bonuses:
        existing = db.query(BonusConfig).filter(
            BonusConfig.bonus_name == bonus_data["bonus_name"]
        ).first()

        if existing:
            print(f"  ⏭️  Skipping '{bonus_data['bonus_name']}' (already exists)")
            skipped += 1
        else:
            bonus = BonusConfig(**bonus_data)
            db.add(bonus)
            print(f"  ✅ Added '{bonus_data['bonus_name']}' (+{bonus_data['bonus_amount']} MMR)")
            added += 1

    if added > 0:
        db.commit()
        print(f"\n✅ Successfully added {added} bonus configurations")
    if skipped > 0:
        print(f"⏭️  Skipped {skipped} existing bonus configurations")


def main():
    """Main seeding function."""
    print("=" * 60)
    print("MMR Bowling Bot - Database Seeding Script")
    print("=" * 60)

    # Load environment variables
    load_dotenv()

    if not os.getenv("DATABASE_URL"):
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("Please create a .env file with your database connection string")
        sys.exit(1)

    print(f"\n📦 Database: {os.getenv('DATABASE_URL')[:30]}...")

    # Initialize database (create tables if they don't exist)
    try:
        print("\n🔧 Initializing database tables...")
        init_db()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"❌ ERROR initializing database: {e}")
        sys.exit(1)

    # Create database session
    db = SessionLocal()

    try:
        # Seed all data
        seed_rank_tiers(db)
        seed_config(db)
        seed_bonus_config(db)

        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Start the bot: python bot.py")
        print("  2. Run /newseason to create your first season")
        print("  3. Run /addplayer to add players")
        print("  4. Run /startcheckin to begin a bowling session")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
