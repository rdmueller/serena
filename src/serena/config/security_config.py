"""
Security configuration for Serena.

This module provides security-related configuration options to control
network access and external service integrations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class SecurityMode(str, Enum):
    """Security modes that control external network access."""
    
    STRICT = "strict"
    """No external network access allowed (most secure)"""
    
    SELECTIVE = "selective"  
    """Allow only explicitly configured external access"""
    
    PERMISSIVE = "permissive"
    """Allow all external access (least secure)"""


@dataclass
class NetworkAccessConfig:
    """Configuration for network access controls."""
    
    allow_language_server_downloads: bool = False
    """Allow language servers to download external dependencies"""
    
    allow_anthropic_token_counting: bool = False
    """Allow sending code to Anthropic API for token counting"""
    
    allow_tiktoken_model_downloads: bool = True
    """Allow downloading tiktoken models (one-time, no code sent)"""
    
    allowed_download_domains: List[str] = None
    """Whitelist of domains allowed for downloads. If None, all domains blocked when downloads disabled."""
    
    def __post_init__(self):
        if self.allowed_download_domains is None:
            self.allowed_download_domains = []


@dataclass  
class SecurityConfig:
    """Main security configuration for Serena."""
    
    mode: SecurityMode = SecurityMode.STRICT
    network_access: NetworkAccessConfig = None
    warn_on_network_access: bool = True
    """Show warnings when network access is attempted"""
    
    def __post_init__(self):
        if self.network_access is None:
            self.network_access = NetworkAccessConfig()
            
        # Apply security mode defaults
        if self.mode == SecurityMode.STRICT:
            self.network_access.allow_language_server_downloads = False
            self.network_access.allow_anthropic_token_counting = False
            self.network_access.allow_tiktoken_model_downloads = False
        elif self.mode == SecurityMode.SELECTIVE:
            # Keep user-specified settings
            pass
        elif self.mode == SecurityMode.PERMISSIVE:
            self.network_access.allow_language_server_downloads = True
            self.network_access.allow_anthropic_token_counting = True  
            self.network_access.allow_tiktoken_model_downloads = True


def create_secure_config() -> SecurityConfig:
    """Create a secure default configuration."""
    return SecurityConfig(
        mode=SecurityMode.STRICT,
        network_access=NetworkAccessConfig(
            allow_language_server_downloads=False,
            allow_anthropic_token_counting=False,
            allow_tiktoken_model_downloads=False,
            allowed_download_domains=[]
        ),
        warn_on_network_access=True
    )


def create_development_config() -> SecurityConfig:
    """Create a configuration suitable for development (more permissive but with warnings)."""
    return SecurityConfig(
        mode=SecurityMode.SELECTIVE,
        network_access=NetworkAccessConfig(
            allow_language_server_downloads=True,
            allow_anthropic_token_counting=False,  # Still require explicit opt-in
            allow_tiktoken_model_downloads=True,
            allowed_download_domains=[
                "github.com",
                "services.gradle.org", 
                "VisualStudioExptTeam.gallery.vsassets.io",
                "marketplace.visualstudio.com",
                "download-cdn.jetbrains.com"
            ]
        ),
        warn_on_network_access=True
    )