"""
init_db.py — Database Initialization Script
============================================

Run this script once to create all database tables.

Usage (from the project root):
    python scripts/init_db.py

This script:
  1. Connects to your Postgres database (from .env)
  2. Creates all tables defined in app/models/
  3. Prints confirmation when done

Note: Running this when tables already exist is SAFE —
SQLAlchemy uses CREATE TABLE IF NOT EXISTS under the hood.
"""

import sys
import os

# Add the project root to Python's module search path
# so Python can find the 'app' package when running this script directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.db.session import engine
from app.models.base import Base

# ── Import ALL models so SQLAlchemy knows about them ──────────────────
# Each import registers the model's table with Base.metadata.
# If you add a new model, add an import here too!
from app.models.jobs import Job                          # Phase 0
from app.models.resumes import Resume                    # Phase 1
from app.models.candidate_profile import CandidateProfile  # Phase 2
from app.models.ranking import Ranking                   # Phase 3 & 4


async def init_models():
    """Create all database tables if they don't already exist."""
    async with engine.begin() as conn:
        # run_sync is required because create_all is a synchronous call
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    print("Connecting to database and creating tables...")
    asyncio.run(init_models())
    print("✅ All tables created successfully!")
    print("\nTables created:")
    print("  - jobs")
    print("  - resumes")
    print("  - candidate_profiles")
