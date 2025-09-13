#!/usr/bin/env python3
"""
Requests-based scraper runner script (No ChromeDriver required)
"""
import logging
import sys
import os
from scraper import JIRARequestsScraper
from config import CRAWL_CONFIG


# Setup logging
current_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(current_dir, "logs"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(current_dir, "logs", "jira_requests_scraper.log")
        ),
        logging.StreamHandler(),
    ],
)


def main():
    """Main execution function"""
    print("JIRA Requests Scraper (No ChromeDriver Required)")
    print("=" * 50)

    # Create necessary directories
    print("✅ Created logs and data directories")

    # Create scraper instance
    scraper = JIRARequestsScraper()

    try:
        # Login to JIRA
        print("Logging into JIRA...")
        if not scraper.ensure_authenticated():
            print("❌ Failed to login to JIRA. Please check your credentials.")
            return 1

        print("✅ Successfully logged into JIRA!")

        # Display configuration
        print(f"\nConfiguration:")
        print(f"  Server: {os.getenv('JIRA_SERVER_URL')}")
        print(f"  Project: {CRAWL_CONFIG['project_key']}")
        print(
            f"  Ticket range: {CRAWL_CONFIG['project_key']}-{CRAWL_CONFIG['start_id']} to {CRAWL_CONFIG['project_key']}-{CRAWL_CONFIG['end_id']}"
        )
        print(f"  Output directory: {CRAWL_CONFIG['output_dir']}")
        print(f"  Delay between requests: {CRAWL_CONFIG['delay']} seconds")

        # Confirm before starting
        total_tickets = CRAWL_CONFIG["end_id"] - CRAWL_CONFIG["start_id"] + 1
        estimated_time = (total_tickets * CRAWL_CONFIG["delay"]) / 60  # minutes

        print(f"\nThis will attempt to scrape {total_tickets:,} tickets.")
        print(f"Estimated time: {estimated_time:.1f} minutes")

        response = input("\nDo you want to continue? (y/N): ").strip().lower()
        if response not in ["y", "yes"]:
            print("Scraping cancelled.")
            return 0

        # Start scraping
        print(f"\n🚀 Starting to scrape tickets...")

        stats = scraper.crawl_tickets(
            project_key=CRAWL_CONFIG["project_key"],
            start_id=CRAWL_CONFIG["start_id"],
            end_id=CRAWL_CONFIG["end_id"],
            output_dir=CRAWL_CONFIG["output_dir"],
            delay=CRAWL_CONFIG["delay"],
            max_retries=CRAWL_CONFIG["max_retries"],
        )

        # Display results
        print("\n" + "=" * 50)
        print("SCRAPING COMPLETED!")
        print("=" * 50)
        print(f"Total attempted: {stats['total_attempted']:,}")
        print(f"✅ Successful: {stats['successful']:,}")
        print(f"❌ Failed: {stats['failed']:,}")
        print(f"🔍 Not found: {stats['not_found']:,}")

        if stats["successful"] > 0:
            success_rate = (stats["successful"] / stats["total_attempted"]) * 100
            print(f"Success rate: {success_rate:.1f}%")
            print(f"\nData saved to: {os.path.abspath(CRAWL_CONFIG['output_dir'])}")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Scraping interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
