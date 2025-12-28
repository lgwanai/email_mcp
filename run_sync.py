
import asyncio
import logging
import sys
from src.config_manager import ConfigManager
from src.email_client_factory import EmailClientFactory
from src.email_index_service import EmailIndexService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def main():
    config_manager = ConfigManager()
    account = config_manager.get_default_account()
    if not account:
        print("No account found")
        return

    print(f"Syncing {account.email_address}...")
    client = EmailClientFactory.create_client(account)
    index_service = EmailIndexService()
    
    async with client:
        # Run initial sync (full sync of last 1000)
        # This will re-fetch headers and overwrite existing entries in DB
        await index_service.sync_initial(client, "INBOX", limit=1000)
    
    print("Sync complete.")

if __name__ == "__main__":
    asyncio.run(main())
