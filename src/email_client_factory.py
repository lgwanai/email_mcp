"""Email client factory for creating IMAP, POP3, or SMTP clients based on configuration."""

import logging
from typing import Union

from email_client import EmailClient
from pop3_client import POP3Client
from smtp_client import SMTPClient, SMTPConfig
from config_manager import EmailAccountConfig

logger = logging.getLogger(__name__)

class EmailClientFactory:
    """Factory class for creating email clients based on protocol configuration."""
    
    @staticmethod
    def create_client(config: EmailAccountConfig) -> Union[EmailClient, POP3Client, SMTPClient]:
        """Create an email client based on the protocol specified in configuration.
        
        Args:
            config: Email account configuration
            
        Returns:
            EmailClient, POP3Client, or SMTPClient instance based on protocol
            
        Raises:
            ValueError: If protocol is not supported
        """
        protocol = config.protocol.lower()
        
        if protocol == "imap":
            logger.info(f"Creating IMAP client for {config.email_address}")
            email_config = config.to_email_config()
            smtp_config = config.to_smtp_config()
            return EmailClient(email_config, smtp_config)
        elif protocol == "pop3":
            logger.info(f"Creating POP3 client for {config.email_address}")
            pop3_config = config.to_pop3_config()
            smtp_config = config.to_smtp_config()
            return POP3Client(pop3_config, smtp_config)
        elif protocol == "smtp":
            logger.info(f"Creating SMTP client for {config.email_address}")
            smtp_config = config.to_smtp_client_config()
            return SMTPClient(smtp_config)
        else:
            raise ValueError(f"Unsupported email protocol: {protocol}. Supported protocols: imap, pop3, smtp")
    
    @staticmethod
    def get_supported_protocols() -> list[str]:
        """Get list of supported email protocols.
        
        Returns:
            List of supported protocol names
        """
        return ["imap", "pop3", "smtp"]
    
    @staticmethod
    def validate_protocol(protocol: str) -> bool:
        """Validate if the given protocol is supported.
        
        Args:
            protocol: Protocol name to validate
            
        Returns:
            True if protocol is supported, False otherwise
        """
        return protocol.lower() in EmailClientFactory.get_supported_protocols()