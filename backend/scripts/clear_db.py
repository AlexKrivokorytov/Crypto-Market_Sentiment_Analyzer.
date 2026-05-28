"""
Utility script to wipe the MongoDB database completely.
Enables fresh seed execution and LLM news parser sweeps.
"""

import asyncio
import sys
from backend.app.core.database import client
from backend.app.core.config import settings


async def clear_database() -> None:
    """
    Drops the entire database from MongoDB.
    """
    db_name = settings.MONGODB_DB_NAME
    print(f"Dropping database '{db_name}'...")
    await client.drop_database(db_name)
    print("Database cleared completely successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(clear_database())
    except Exception as exc:
        print(f"Error: Database clearance failed: {str(exc)}", file=sys.stderr)
        sys.exit(1)
