import os
import sys
import asyncio
import logging

# Ensure root directory is in sys.path so we can import backend packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import (
    assets_collection,
    articles_collection,
    historical_collection,
    ticks_collection,
    ticks_buckets_collection,
    ensure_indexes,
)
from backend.app.handlers.factory import handler_factory
from backend.app.services.market_data import seed_database_if_empty
from backend.app.services.registry import dynamic_registry
from backend.app.core.seed import (
    get_default_assets,
    DEFAULT_CRYPTO_LEXICON,
    DEFAULT_MULTI_WORD_LEXICON,
)
from backend.app.schemas.registry import AssetConfig, LexiconConfig

# Set up logging to console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("reset_db")


async def reset_and_seed() -> None:
    logger.info("🚀 Starting database reset and seeding process...")

    # 1. Drop existing collections to start completely from scratch
    logger.info("🗑️ Dropping existing database collections...")
    await assets_collection.drop()
    await articles_collection.drop()
    await historical_collection.drop()
    await ticks_collection.drop()
    await ticks_buckets_collection.drop()
    logger.info("✅ Database collections dropped successfully.")

    # 2. Re-create all indexes for MongoDB performance and unique constraints
    logger.info("📁 Re-creating fresh database indexes...")
    await ensure_indexes()
    logger.info("✅ Database indexes ready.")

    # 3. Bootstrap handler factory
    logger.info("⚙️ Bootstrapping asset handler factory...")
    default_assets = [AssetConfig(**cfg) for cfg in get_default_assets()]
    default_lexicon = LexiconConfig(
        id="global",
        crypto_lexicon=DEFAULT_CRYPTO_LEXICON,
        multi_word_lexicon=DEFAULT_MULTI_WORD_LEXICON,
    )
    await dynamic_registry.initialize_defaults(default_assets, default_lexicon)
    await handler_factory.bootstrap(dynamic_registry)
    logger.info(
        f"✅ Handler factory ready with {len(handler_factory)} assets: {handler_factory.asset_ids()}"
    )

    # 4. Seed database from scratch
    logger.info("🌱 Seeding database with fresh asset metrics, articles, and charts...")
    await seed_database_if_empty()
    logger.info(
        "🎉 Database seeding complete! Your database is now 100% clean and fully seeded."
    )


if __name__ == "__main__":
    # Run the async script
    asyncio.run(reset_and_seed())
