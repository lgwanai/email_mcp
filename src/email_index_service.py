from typing import Any, Dict, List, Optional, Tuple
import json
import logging
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class IndexedEmail:
    uid: str
    account: str
    folder: str
    date: datetime
    sender: str
    recipients: List[str]
    cc: List[str]
    subject: str
    snippet: str
    has_attachments: bool
    attachment_names: List[str]
    body: Optional[str] = None
    flags: List[str] = None
    message_id: Optional[str] = None
    attachment_dir: Optional[str] = None

class EmailIndexService:
    """Service for indexing emails in SQLite for fast retrieval and offline access."""

    def __init__(self, db_path: str = "email_index.db", attachment_manager: Any = None):
        self.db_path = db_path
        self.attachment_manager = attachment_manager
        self._init_db()

    def _get_connection(self):
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        try:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            
            # Create emails table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS emails (
                account TEXT,
                folder TEXT,
                uid TEXT,
                date TEXT,
                sender TEXT,
                recipients TEXT,
                cc TEXT,
                subject TEXT,
                snippet TEXT,
                has_attachments INTEGER,
                attachment_names_json TEXT,
                body TEXT,
                flags_json TEXT,
                message_id TEXT,
                attachment_dir TEXT,
                PRIMARY KEY (account, folder, uid)
            )
            """)
            
            # Try to add attachment_dir column if it doesn't exist (migration)
            try:
                conn.execute("ALTER TABLE emails ADD COLUMN attachment_dir TEXT")
            except sqlite3.OperationalError:
                # Column likely already exists
                pass
            
            # Create sync_state table
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                account TEXT,
                folder TEXT,
                last_seen_uid TEXT,
                last_sync_at TEXT,
                uidvalidity TEXT,
                PRIMARY KEY (account, folder)
            )
            """)
            
            # Create FTS table
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS emails_fts USING fts5(
                subject, 
                sender, 
                recipients, 
                snippet, 
                body, 
                content='emails', 
                content_rowid='rowid'
            )
            """)
            
            # Triggers to keep FTS updated
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS emails_ai AFTER INSERT ON emails BEGIN
                INSERT INTO emails_fts(rowid, subject, sender, recipients, snippet, body) 
                VALUES (new.rowid, new.subject, new.sender, new.recipients, new.snippet, new.body);
            END;
            """)
            
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS emails_ad AFTER DELETE ON emails BEGIN
                INSERT INTO emails_fts(emails_fts, rowid, subject, sender, recipients, snippet, body) 
                VALUES('delete', old.rowid, old.subject, old.sender, old.recipients, old.snippet, old.body);
            END;
            """)
            
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS emails_au AFTER UPDATE ON emails BEGIN
                INSERT INTO emails_fts(emails_fts, rowid, subject, sender, recipients, snippet, body) 
                VALUES('delete', old.rowid, old.subject, old.sender, old.recipients, old.snippet, old.body);
                INSERT INTO emails_fts(rowid, subject, sender, recipients, snippet, body) 
                VALUES (new.rowid, new.subject, new.sender, new.recipients, new.snippet, new.body);
            END;
            """)
            
            conn.commit()
            logger.info(f"Initialized email index at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        finally:
            conn.close()

    async def save_emails(self, emails: List[IndexedEmail]):
        """Save a batch of emails to the index."""
        if not emails:
            return

        logger.debug(f"Saving {len(emails)} emails to database")
        
        def _save():
            conn = self._get_connection()
            try:
                conn.execute("BEGIN TRANSACTION")
                for email in emails:
                    logger.debug(f"Saving email UID {email.uid} from {email.account}/{email.folder}")
                    conn.execute("""
                    INSERT OR REPLACE INTO emails (
                        account, folder, uid, date, sender, recipients, cc, 
                        subject, snippet, has_attachments, attachment_names_json, 
                        body, flags_json, message_id, attachment_dir
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        email.account,
                        email.folder,
                        email.uid,
                        email.date.isoformat(),
                        str(email.sender),
                        json.dumps(email.recipients),
                        json.dumps(email.cc),
                        str(email.subject),
                        str(email.snippet),
                        1 if email.has_attachments else 0,
                        json.dumps(email.attachment_names),
                        email.body,
                        json.dumps(email.flags) if email.flags else "[]",
                        email.message_id,
                        email.attachment_dir
                    ))
                conn.commit()
                logger.debug("Batch save committed successfully")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to save emails: {e}")
                raise
            finally:
                conn.close()

        await asyncio.get_event_loop().run_in_executor(None, _save)

    async def get_sync_state(self, account: str, folder: str) -> Optional[Dict[str, Any]]:
        """Get synchronization state for a folder."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT * FROM sync_state WHERE account = ? AND folder = ?", 
                    (account, folder)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def update_sync_state(self, account: str, folder: str, last_seen_uid: str, uidvalidity: str = None):
        """Update synchronization state."""
        def _update():
            conn = self._get_connection()
            try:
                # Get current state to preserve uidvalidity if not provided
                current = conn.execute(
                    "SELECT uidvalidity FROM sync_state WHERE account = ? AND folder = ?",
                    (account, folder)
                ).fetchone()
                
                current_uidvalidity = current['uidvalidity'] if current else None
                new_uidvalidity = uidvalidity if uidvalidity is not None else current_uidvalidity

                conn.execute("""
                INSERT OR REPLACE INTO sync_state (account, folder, last_seen_uid, last_sync_at, uidvalidity)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    account, 
                    folder, 
                    last_seen_uid, 
                    datetime.now().isoformat(),
                    new_uidvalidity
                ))
                conn.commit()
            finally:
                conn.close()

        await asyncio.get_event_loop().run_in_executor(None, _update)

    async def list_emails(self, account: str, folder: str, 
                         limit: int = 50, 
                         start_uid: Optional[str] = None, 
                         reverse_order: bool = True,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """List emails from the index."""
        def _list():
            conn = self._get_connection()
            try:
                query = "SELECT * FROM emails WHERE account = ? AND folder = ?"
                params = [account, folder]

                if start_uid:
                    if reverse_order:
                        query += " AND CAST(uid AS INTEGER) < CAST(? AS INTEGER)"
                    else:
                        query += " AND CAST(uid AS INTEGER) > CAST(? AS INTEGER)"
                    params.append(start_uid)
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date.isoformat())

                query += " ORDER BY CAST(uid AS INTEGER) " + ("DESC" if reverse_order else "ASC")
                query += " LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

        return await asyncio.get_event_loop().run_in_executor(None, _list)
    
    async def get_email(self, account: str, folder: str, uid: str) -> Optional[Dict[str, Any]]:
        """Get a specific email from the index."""
        def _get():
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT * FROM emails WHERE account = ? AND folder = ? AND uid = ?",
                    (account, folder, uid)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

        return await asyncio.get_event_loop().run_in_executor(None, _get)

    async def update_email_body(self, account: str, folder: str, uid: str, body: str):
        """Update the body of an existing email."""
        def _update():
            conn = self._get_connection()
            try:
                conn.execute("""
                UPDATE emails 
                SET body = ? 
                WHERE account = ? AND folder = ? AND uid = ?
                """, (body, account, folder, uid))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to update email body: {e}")
                raise
            finally:
                conn.close()

        await asyncio.get_event_loop().run_in_executor(None, _update)

    async def update_attachment_dir(self, account: str, folder: str, uid: str, attachment_dir: str):
        """Update the attachment_dir of an existing email."""
        def _update():
            conn = self._get_connection()
            try:
                conn.execute("""
                UPDATE emails 
                SET attachment_dir = ? 
                WHERE account = ? AND folder = ? AND uid = ?
                """, (attachment_dir, account, folder, uid))
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to update attachment dir: {e}")
                raise
            finally:
                conn.close()

        await asyncio.get_event_loop().run_in_executor(None, _update)

    async def search_emails(self, account: Optional[str], keywords: List[str], search_fields: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        """Search emails using FTS with advanced options.
        
        Args:
            account: Email account to search (Optional, if None search all accounts)
            keywords: List of keywords to search for (OR logic)
            search_fields: List of fields to search in (sender, recipients, subject, body). If None, search all.
            limit: Max results
            offset: Pagination offset
            
        Returns:
            Tuple containing:
            - List of email dictionaries
            - Total count of matching emails
        """
        def _search():
            conn = self._get_connection()
            try:
                if not keywords:
                    return [], 0

                # Construct FTS query
                # Sanitize keywords: escape double quotes
                sanitized_keywords = []
                for k in keywords:
                    safe_k = k.replace('"', '""')
                    sanitized_keywords.append(f'"{safe_k}"')
                
                # Combine keywords with OR (any keyword match is a hit)
                combined_keywords = " OR ".join(sanitized_keywords)
                
                final_query = ""
                if not search_fields:
                    # Comprehensive search (all columns)
                    final_query = combined_keywords
                else:
                    # Specific fields
                    # Map user fields to DB columns
                    db_fields = []
                    valid_fields = ["sender", "recipients", "subject", "body"]
                    
                    for f in search_fields:
                        # Handle mapping if needed (e.g. 'recipient' -> 'recipients')
                        if f == "recipient":
                            db_fields.append("recipients")
                        elif f in valid_fields:
                            db_fields.append(f)
                    
                    if not db_fields:
                        final_query = combined_keywords
                    else:
                        fields_str = " ".join(db_fields)
                        final_query = f"{{{fields_str}}} : ({combined_keywords})"

                # Base query parts
                base_query = """
                FROM emails e
                JOIN emails_fts f ON e.rowid = f.rowid
                WHERE emails_fts MATCH ?
                """
                params = [final_query]

                if account:
                    base_query += " AND e.account = ?"
                    params.append(account)

                # Get Total Count
                count_sql = f"SELECT COUNT(*) {base_query}"
                cursor = conn.execute(count_sql, params)
                total_count = cursor.fetchone()[0]

                # Get Results
                # We order by date DESC to show newest matches first
                sql = f"SELECT e.* {base_query} ORDER BY e.date DESC LIMIT ? OFFSET ?"
                
                # Copy params for the second query and add limit/offset
                query_params = params.copy()
                query_params.extend([limit, offset])
                
                cursor = conn.execute(sql, query_params)
                return [dict(row) for row in cursor.fetchall()], total_count
            finally:
                conn.close()

        return await asyncio.get_event_loop().run_in_executor(None, _search)

    async def get_all_uids(self, account: str, folder: str) -> List[str]:
        """Get all UIDs for a specific account and folder."""
        def _get_uids():
            conn = self._get_connection()
            try:
                cursor = conn.execute(
                    "SELECT uid FROM emails WHERE account = ? AND folder = ?",
                    (account, folder)
                )
                return [row['uid'] for row in cursor.fetchall()]
            finally:
                conn.close()

        return await asyncio.get_event_loop().run_in_executor(None, _get_uids)

    async def _download_attachments_and_update(self, emails: List[Any], account: str):
        """Download attachments for a batch of emails and update their info."""
        if not self.attachment_manager:
            return

        for email in emails:
            if email.attachments:
                try:
                    # Download attachments
                    # We pass email.uid and email.attachments (which has part objects)
                    downloaded = await self.attachment_manager.download_attachments(
                        account, # Use account as email address for folder structure
                        email.uid,
                        email.attachments
                    )
                    # Update parsed email attachments with downloaded info
                    email.attachments = downloaded
                except Exception as e:
                    logger.error(f"Failed to download attachments for {email.uid}: {e}")

    async def sync_all_emails(self, client, folder: str = "INBOX", batch_size: int = 50):
        """Perform full synchronization for a folder, fetching any missing emails."""
        account = client.config.username
        logger.info(f"Starting full sync check for {account}/{folder}")
        
        try:
            # 1. Get all UIDs from server
            await asyncio.get_event_loop().run_in_executor(
                None, client._connection.select, folder
            )
            
            typ, data = await asyncio.get_event_loop().run_in_executor(
                None, client._connection.search, None, "ALL"
            )
            
            if typ != 'OK':
                logger.error(f"Failed to search UIDs for {folder}")
                return

            server_uids_bytes = data[0].split()
            if not server_uids_bytes:
                logger.info(f"No emails found in {folder} on server")
                return
            
            server_uids = [u.decode() for u in server_uids_bytes]
            logger.debug(f"Found {len(server_uids)} total emails on server")

            # 2. Get local UIDs
            local_uids = await self.get_all_uids(account, folder)
            local_uids_set = set(local_uids)
            logger.info(f"Loaded {len(local_uids_set)} local UIDs for {account}/{folder}")
            
            # 3. Identify missing UIDs
            missing_uids = [u for u in server_uids if u not in local_uids_set]
            
            if not missing_uids:
                logger.info(f"Local index is up to date with server ({len(server_uids)} emails). No new emails to fetch.")
                # Update sync state to ensure last_seen_uid is correct
                if server_uids:
                    max_uid = max([int(u) for u in server_uids])
                    await self.update_sync_state(account, folder, str(max_uid))
                return

            logger.info(f"Found {len(missing_uids)} missing emails to fetch")
            
            # 4. Fetch in batches
            # Sort missing UIDs numerically to fetch in order
            missing_uids_int = sorted([int(u) for u in missing_uids])
            missing_uids_sorted = [str(u) for u in missing_uids_int]
            
            total_batches = (len(missing_uids_sorted) + batch_size - 1) // batch_size
            
            for i in range(0, len(missing_uids_sorted), batch_size):
                batch_uids = missing_uids_sorted[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                logger.info(f"Fetching batch {batch_num}/{total_batches} ({len(batch_uids)} emails)")
                
                try:
                    # Fetch full emails (including attachments)
                    emails = await client.fetch_full_emails_batch(batch_uids, folder)
                    
                    if emails:
                        # Download attachments
                        await self._download_attachments_and_update(emails, account)
                        
                        # Save to DB
                        indexed_emails = self._convert_to_indexed(emails, account, folder)
                        await self.save_emails(indexed_emails)
                        logger.debug(f"Saved batch {batch_num}")
                    
                    # Optional: sleep slightly to be nice to server?
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process batch {batch_num}: {e}")
                    # Continue to next batch instead of aborting
                    continue

            # 5. Update sync state
            max_uid = max([int(u) for u in server_uids])
            await self.update_sync_state(account, folder, str(max_uid))
            logger.info(f"Full sync completed. Last UID: {max_uid}")

        except Exception as e:
            logger.error(f"Full sync failed for {folder}: {e}")

    async def sync_initial(self, client, folder: str = "INBOX", limit: int = 100):
        """Perform initial synchronization for a folder."""
        logger.info(f"Starting initial sync for {client.config.username} folder {folder}")
        try:
            # 1. Select folder and get all UIDs
            await asyncio.get_event_loop().run_in_executor(
                None, client._connection.select, folder
            )
            
            typ, data = await asyncio.get_event_loop().run_in_executor(
                None, client._connection.search, None, "ALL"
            )
            
            if typ != 'OK':
                logger.error(f"Failed to search UIDs for {folder}")
                return

            all_uids = data[0].split()
            if not all_uids:
                logger.info(f"No emails found in {folder}")
                return
            
            logger.debug(f"Found {len(all_uids)} total emails in {folder}")

            # Sort UIDs (numeric)
            all_uids_int = sorted([int(u) for u in all_uids])
            
            # Take last N
            uids_to_fetch = [str(u) for u in all_uids_int[-limit:]]
            if not uids_to_fetch:
                return
                
            logger.debug(f"Fetching full content for {len(uids_to_fetch)} emails (limit={limit})")

            # 2. Fetch full emails
            emails = await client.fetch_full_emails_batch(uids_to_fetch, folder)
            logger.debug(f"Fetched {len(emails)} emails")
            
            # Download attachments
            await self._download_attachments_and_update(emails, client.config.username)
            
            # 3. Save to DB
            indexed_emails = self._convert_to_indexed(emails, client.config.username, folder)
            await self.save_emails(indexed_emails)
            
            # 4. Update sync state
            last_uid = str(all_uids_int[-1])
            await self.update_sync_state(client.config.username, folder, last_uid)
            
            logger.info(f"Initial sync completed for {folder}: {len(emails)} emails indexed. Last UID: {last_uid}")
            
        except Exception as e:
            logger.error(f"Initial sync failed for {folder}: {e}")

    async def sync_incremental(self, client, folder: str = "INBOX"):
        """Perform incremental synchronization for a folder."""
        account = client.config.username
        logger.debug(f"Starting incremental sync check for {account}/{folder}")
        
        # 1. Get sync state
        state = await self.get_sync_state(account, folder)
        if not state or not state.get('last_seen_uid'):
            logger.info(f"No sync state found for {folder}, falling back to initial sync")
            await self.sync_initial(client, folder)
            return

        last_seen_uid = state['last_seen_uid']
        logger.debug(f"Last seen UID for {folder}: {last_seen_uid}")
        
        try:
            # 2. Search for new UIDs
            await asyncio.get_event_loop().run_in_executor(
                None, client._connection.select, folder
            )
            
            # UID SEARCH UID last_seen+1:*
            search_crit = f"UID {int(last_seen_uid) + 1}:*"
            logger.debug(f"Searching for new emails with criteria: {search_crit}")
            
            typ, data = await asyncio.get_event_loop().run_in_executor(
                None, client._connection.search, None, search_crit
            )
            
            if typ != 'OK':
                return

            new_uids = data[0].split()
            if not new_uids:
                # logger.debug(f"No new emails in {folder}")
                return

            # Filter out the last_seen_uid itself if returned (sometimes happens with range queries if exact match)
            new_uids = [u.decode() for u in new_uids if int(u) > int(last_seen_uid)]
            
            if not new_uids:
                logger.debug("No new UIDs found after filtering")
                return
                
            logger.info(f"Found {len(new_uids)} new emails in {folder}: {new_uids}")

            # 3. Fetch full emails
            emails = await client.fetch_full_emails_batch(new_uids, folder)
            logger.debug(f"Fetched {len(emails)} new emails")
            
            # Download attachments
            await self._download_attachments_and_update(emails, account)
            
            # 4. Save to DB
            indexed_emails = self._convert_to_indexed(emails, account, folder)
            await self.save_emails(indexed_emails)
            
            # 5. Update sync state
            # Get max UID from fetched emails to be safe, or just max of new_uids
            max_uid = max([int(u) for u in new_uids])
            await self.update_sync_state(account, folder, str(max_uid))
            logger.info(f"Incremental sync updated last UID to {max_uid}")
            
        except Exception as e:
            logger.error(f"Incremental sync failed for {folder}: {e}")

    def _convert_to_indexed(self, emails: List[Any], account: str, folder: str) -> List[IndexedEmail]:
        """Convert ParsedEmail objects to IndexedEmail."""
        logger.debug(f"Converting {len(emails)} emails to indexed format")
        indexed = []
        for email in emails:
            # Convert attachments list of dicts/objects to list of names for indexing
            att_names = []
            attachment_dir = None
            
            if email.attachments:
                for att in email.attachments:
                    if isinstance(att, dict):
                        name = att.get('filename') or att.get('name') or "unknown"
                        att_names.append(name)
                        
                        # Try to find attachment directory from local_path
                        if not attachment_dir and att.get('local_path'):
                            try:
                                attachment_dir = str(Path(att['local_path']).parent)
                            except Exception:
                                pass
            
            indexed.append(IndexedEmail(
                uid=email.uid,
                account=account,
                folder=folder,
                date=email.date,
                sender=email.sender,
                recipients=email.recipients,
                cc=email.cc,
                subject=email.subject,
                snippet=email.content[:200] if email.content else "",
                has_attachments=bool(email.attachments),
                attachment_names=att_names,
                body=email.content,
                # flags not fetched in ParsedEmail currently, or are they? 
                # ParsedEmail doesn't have flags field in dataclass?
                # Wait, ParsedEmail definition in email_client.py:
                # uid, sender, recipients, cc, bcc, subject, content, date, attachments, raw_message.
                # No flags.
                flags=[],
                message_id=None, # ParsedEmail doesn't have message_id
                attachment_dir=attachment_dir
            ))
        return indexed

    async def start_background_sync(self, client_factory, config_manager, interval: int = 60):
        """Start background synchronization loop."""
        logger.info(f"Background sync service started with interval {interval}s")
        while True:
            try:
                accounts = config_manager.get_enabled_accounts()
                logger.debug(f"Running background sync for {len(accounts)} accounts")
                for account_config in accounts.values():
                    try:
                        email_address = getattr(account_config, "email_address", None)
                        protocol = (getattr(account_config, "protocol", "") or "").lower()

                        if not email_address:
                            logger.error("Skipping account with missing email_address in configuration")
                            continue

                        if getattr(account_config, "enabled", True) is False:
                            logger.debug(f"Skipping disabled account: {email_address}")
                            continue

                        if not getattr(account_config, "password", None):
                            logger.error(f"Skipping account {email_address}: missing password in configuration")
                            continue

                        if protocol == "imap":
                            if not getattr(account_config, "imap_host", None):
                                logger.error(f"Skipping IMAP account {email_address}: missing imap_host in configuration")
                                continue
                            if not getattr(account_config, "imap_port", None):
                                logger.error(f"Skipping IMAP account {email_address}: missing imap_port in configuration")
                                continue
                        elif protocol == "pop3":
                            logger.error(f"Skipping account {email_address}: background sync supports IMAP only (protocol=pop3)")
                            continue
                        elif protocol == "smtp":
                            logger.debug(f"Skipping SMTP-only account (no inbox to sync): {email_address}")
                            continue
                        else:
                            logger.error(f"Skipping account {email_address}: unsupported protocol '{protocol}'")
                            continue

                        logger.debug(f"Processing account: {email_address} (protocol={protocol})")
                        # Create client
                        client = client_factory.create_client(account_config)
                        async with client:
                            # Sync INBOX (default)
                            # Could also sync other folders if configured
                            folder = getattr(account_config, "default_folder", None) or "INBOX"
                            # Use sync_all_emails to ensure complete sync and backfill
                            await self.sync_all_emails(client, folder)
                    except Exception as e:
                        logger.error(f"Sync failed for account {getattr(account_config, 'email_address', '<unknown>')}: {e}")
            except Exception as e:
                logger.error(f"Error in background sync loop: {e}")
            
            await asyncio.sleep(interval)
