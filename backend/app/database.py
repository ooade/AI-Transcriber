import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Database Configuration
# ============================================================================
# Supports both SQLite (dev) and PostgreSQL (production)
# Priority:
# 1. DATABASE_URL environment variable (explicit configuration)
# 2. Default: SQLite for local development

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Default to SQLite for development
    DATABASE_URL = "sqlite:///./transcriber.db"
    print("ℹ️  Using default SQLite database. Set DATABASE_URL for PostgreSQL.")
elif DATABASE_URL.startswith("postgresql"):
    print(f"✅ Using PostgreSQL database")
elif DATABASE_URL.startswith("sqlite"):
    print(f"✅ Using SQLite database")
else:
    print(f"⚠️  Using custom database: {DATABASE_URL}")

# ============================================================================
# Engine Configuration
# ============================================================================
if "postgresql" in DATABASE_URL:
    # PostgreSQL-specific settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Test connections before using
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )
else:
    # SQLite-specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=os.getenv("SQL_ECHO", "false").lower() == "true"
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
