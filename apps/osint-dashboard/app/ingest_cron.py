"""CronJob entry point for scheduled ingestion."""

import asyncio
import os
import sys
from pathlib import Path

# Add app dir to path
sys.path.insert(0, str(Path(__file__).parent))

from sources import ingest_rss_feed, ingest_gdelt, ingest_earthquakes
from ingestor import fetch_and_process

INGESTOR_TYPE = os.getenv("INGESTOR_TYPE", "rss")
RSS_URL = os.getenv("RSS_URL", "")


async def main():
    print(f"Starting ingester: {INGESTOR_TYPE}")

    if INGESTOR_TYPE == "rss":
        if not RSS_URL:
            print("No RSS_URL set, skipping")
            return
        count = await ingest_rss_feed(RSS_URL)
        print(f"RSS: ingested {count} items")

    elif INGESTOR_TYPE == "gdelt":
        count = await ingest_gdelt(max_articles=50)
        print(f"GDELT: ingested {count} articles")

    elif INGESTOR_TYPE == "earthquake":
        count = await ingest_earthquakes()
        print(f"Earthquakes: ingested {count} events")

    elif INGESTOR_TYPE == "nats":
        count = await fetch_and_process(batch_size=500)
        print(f"NATS: processed {count} messages")

    else:
        print(f"Unknown ingestor type: {INGESTOR_TYPE}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
