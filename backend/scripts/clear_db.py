"""
Utility script to clear MongoDB collections for assets and articles.
Enables fresh seed execution and LLM news parser sweeps.
"""

import asyncio
import sys
from backend.app.core.database import db


async def clear_database() -> None:
    """
    Drops the articles and assets collections from MongoDB.
    """
    print("Dropping 'articles' collection...")
    await db["articles"].drop()
    print("Dropping 'assets' collection...")
    await db["assets"].drop()
    print("Database collections cleared successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(clear_database())
    except Exception as exc:
        print(f"Error: Database clearance failed: {str(exc)}", file=sys.stderr)
        sys.exit(1)
