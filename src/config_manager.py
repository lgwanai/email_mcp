"""Configuration manager for multi-email account support."""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EmailAccountConfig:
    """Configuration for a single email account."""
    email_address: str
    password: str
    display_name: str = ""
    
    # Protocol selection: 'imap' or 'pop3'
    protocol: str = "imap"
    
    # IMAP settings
    imap_host: str = ""
    imap_port: int = 993
    imap_use_ssl: bool = True
    
    # POP3 settings
    pop3_host: str = ""
    pop3_port: int = 995
    pop3_use_ssl: bool = True
    
    # SMTP settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    
    # Additional settings
    enabled: bool = True
    default_folder: str = "INBOX"
    
    def __post_init__(self):
        """Auto-configure server settings if not provided."""
        if not self.imap_host or not self.smtp_host:
            self._auto_configure_servers()
    
    def _auto_configure_servers(self):
        """Auto-configure IMAP/POP3 and SMTP servers based on email domain and protocol."""
        domain = self.email_address.split('@')[1].lower()
        
        # Common email provider configurations
        providers = {
            'gmail.com': {
                'imap_host': 'imap.gmail.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'pop.gmail.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            'outlook.com': {
                'imap_host': 'outlook.office365.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'outlook.office365.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp-mail.outlook.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            'hotmail.com': {
                'imap_host': 'outlook.office365.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'outlook.office365.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp-mail.outlook.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            'yahoo.com': {
                'imap_host': 'imap.mail.yahoo.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'pop.mail.yahoo.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp.mail.yahoo.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            'icloud.com': {
                'imap_host': 'imap.mail.me.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'pop.mail.me.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp.mail.me.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            '163.com': {
                'imap_host': 'imap.163.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'pop.163.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp.163.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            '126.com': {
                'imap_host': 'imap.126.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'pop.126.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp.126.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            },
            'qq.com': {
                'imap_host': 'imap.qq.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'pop3_host': 'pop.qq.com',
                'pop3_port': 995,
                'pop3_use_ssl': True,
                'smtp_host': 'smtp.qq.com',
                'smtp_port': 587,
                'smtp_use_tls': True
            }
        }
        
        config = providers.get(domain, {
            'imap_host': f'imap.{domain}',
            'imap_port': 993,
            'imap_use_ssl': True,
            'pop3_host': f'pop.{domain}',
            'pop3_port': 995,
            'pop3_use_ssl': True,
            'smtp_host': f'smtp.{domain}',
            'smtp_port': 587,
            'smtp_use_tls': True
        })
        
        # Configure IMAP settings
        if not self.imap_host:
            self.imap_host = config.get('imap_host', '')
        if not self.imap_port:
            self.imap_port = config.get('imap_port', 993)
        if 'imap_use_ssl' in config:
            self.imap_use_ssl = config['imap_use_ssl']
        
        # Configure POP3 settings
        if not self.pop3_host:
            self.pop3_host = config.get('pop3_host', '')
        if not self.pop3_port:
            self.pop3_port = config.get('pop3_port', 995)
        if 'pop3_use_ssl' in config:
            self.pop3_use_ssl = config['pop3_use_ssl']
        
        # Configure SMTP settings
        if not self.smtp_host:
            self.smtp_host = config.get('smtp_host', '')
        if not self.smtp_port:
            self.smtp_port = config.get('smtp_port', 587)
        if 'smtp_use_tls' in config:
            self.smtp_use_tls = config['smtp_use_tls']
    
    def get_email_folder_name(self) -> str:
        """Convert email address to safe folder name."""
        # Replace @ with - and . with _
        return self.email_address.replace('@', '-').replace('.', '_')
    
    def to_email_config(self):
        """Convert to EmailConfig for IMAP client."""
        from email_client import EmailConfig
        return EmailConfig(
            host=self.imap_host,
            port=self.imap_port,
            use_ssl=self.imap_use_ssl,
            username=self.email_address,
            password=self.password
        )
    
    def to_pop3_config(self):
        """Convert to POP3Config for POP3 client."""
        from pop3_client import POP3Config
        return POP3Config(
            host=self.pop3_host,
            port=self.pop3_port,
            use_ssl=self.pop3_use_ssl,
            username=self.email_address,
            password=self.password
        )
    
    def to_smtp_config(self):
        """Convert to SMTPConfig for email sending."""
        from email_client import SMTPConfig
        return SMTPConfig(
            host=self.smtp_host,
            port=self.smtp_port,
            use_tls=self.smtp_use_tls,
            username=self.email_address,
            password=self.password
        )
    
    def to_smtp_client_config(self):
        """Convert to SMTPConfig for standalone SMTP client."""
        from smtp_client import SMTPConfig
        return SMTPConfig(
            host=self.smtp_host,
            port=self.smtp_port,
            use_tls=self.smtp_use_tls,
            username=self.email_address,
            password=self.password
        )


class ConfigManager:
    """Manages email account configurations."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or os.getenv('EMAIL_CONFIG_FILE', 'email_accounts.json')
        self.config_path = Path(self.config_file)
        self.accounts: Dict[str, EmailAccountConfig] = {}
        self._load_config()
    
    def _load_config(self):
        """Load email accounts configuration from file."""
        if not self.config_path.exists():
            logger.info(f"Configuration file {self.config_path} not found, creating default")
            self._create_default_config()
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.accounts = {}
            for email, account_data in config_data.get('accounts', {}).items():
                try:
                    account = EmailAccountConfig(**account_data)
                    self.accounts[email] = account
                except Exception as e:
                    logger.error(f"Failed to load account config for {email}: {e}")
            
            logger.info(f"Loaded {len(self.accounts)} email accounts from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {self.config_path}: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Create a default configuration file."""
        default_config = {
            "accounts": {}
        }
        
        try:
            # Create directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created default configuration file: {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to create default configuration: {e}")
    
    def save_config(self):
        """Save current configuration to file."""
        try:
            config_data = {
                "accounts": {email: asdict(account) for email, account in self.accounts.items()}
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def add_account(self, account: EmailAccountConfig) -> bool:
        """Add a new email account configuration."""
        try:
            self.accounts[account.email_address] = account
            self.save_config()
            logger.info(f"Added email account: {account.email_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to add account {account.email_address}: {e}")
            return False
    
    def remove_account(self, email_address: str) -> bool:
        """Remove an email account configuration."""
        if email_address in self.accounts:
            del self.accounts[email_address]
            self.save_config()
            logger.info(f"Removed email account: {email_address}")
            return True
        else:
            logger.warning(f"Account {email_address} not found")
            return False
    
    def get_account(self, email_address: str) -> Optional[EmailAccountConfig]:
        """Get email account configuration by email address."""
        return self.accounts.get(email_address)
    
    def list_accounts(self) -> List[str]:
        """List all configured email addresses."""
        return list(self.accounts.keys())
    
    def get_enabled_accounts(self) -> Dict[str, EmailAccountConfig]:
        """Get all enabled email accounts."""
        return {email: account for email, account in self.accounts.items() if account.enabled}
    
    def find_account_by_domain(self, domain: str) -> List[EmailAccountConfig]:
        """Find accounts by email domain."""
        domain = domain.lower()
        return [account for account in self.accounts.values() 
                if account.email_address.split('@')[1].lower() == domain]
    
    def validate_account(self, email_address: str) -> bool:
        """Validate that an account exists and is enabled."""
        account = self.get_account(email_address)
        return account is not None and account.enabled
    
    def get_account_folder_name(self, email_address: str) -> str:
        """Get the folder name for an email account's attachments."""
        account = self.get_account(email_address)
        if account:
            return account.get_email_folder_name()
        else:
            # Fallback for unknown accounts
            return email_address.replace('@', '-').replace('.', '_')
    
    def get_account_config(self, email_address: str) -> Optional[EmailAccountConfig]:
        """Get email account configuration by email address (alias for get_account)."""
        return self.get_account(email_address)
    
    def get_default_account(self) -> Optional[EmailAccountConfig]:
        """Get the first enabled account as default."""
        enabled_accounts = self.get_enabled_accounts()
        if enabled_accounts:
            return next(iter(enabled_accounts.values()))
        return None


# Global configuration manager instance
_config_manager = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reload_config():
    """Reload the configuration from file."""
    global _config_manager
    _config_manager = None
    return get_config_manager()