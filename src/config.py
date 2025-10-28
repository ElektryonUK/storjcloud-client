"""
Configuration management

Handles loading and managing configuration from files, environment variables, and CLI arguments.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class ApiConfig:
    """API configuration"""
    token: str = ""
    endpoint: str = "https://storj.cloud/api/v1"
    timeout: int = 30


@dataclass
class DiscoveryConfig:
    """Discovery configuration"""
    from_docker: bool = True
    docker_host: str = "unix:///var/run/docker.sock"
    common_ports: List[int] = field(default_factory=lambda: [14000, 14001, 14002, 14003, 14004, 14005])
    port_range: List[int] = field(default_factory=lambda: [14000, 14010])
    timeout: int = 5
    retry_attempts: int = 3


@dataclass
class SyncConfig:
    """Sync configuration"""
    interval: int = 300
    batch_size: int = 10
    retry_failed: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "info"
    file: Optional[str] = None


@dataclass
class Config:
    """Main configuration"""
    api: ApiConfig = field(default_factory=ApiConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from file and environment"""
        config = cls()
        
        # Load from file
        if config_path and Path(config_path).exists():
            config._load_from_file(config_path)
        else:
            # Try default locations
            default_paths = [
                Path.home() / '.storjcloud' / 'config.yaml',
                Path('/etc/storjcloud/config.yaml'),
                Path('config.yaml')
            ]
            
            for path in default_paths:
                if path.exists():
                    config._load_from_file(str(path))
                    break
        
        # Override with environment variables
        config._load_from_env()
        
        return config
    
    def _load_from_file(self, config_path: str):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if 'api' in data:
                api_data = data['api']
                self.api.token = api_data.get('token', self.api.token)
                self.api.endpoint = api_data.get('endpoint', self.api.endpoint)
                self.api.timeout = api_data.get('timeout', self.api.timeout)
            
            if 'discovery' in data:
                disc_data = data['discovery']
                self.discovery.from_docker = disc_data.get('from_docker', self.discovery.from_docker)
                self.discovery.docker_host = disc_data.get('docker_host', self.discovery.docker_host)
                self.discovery.common_ports = disc_data.get('common_ports', self.discovery.common_ports)
                self.discovery.port_range = disc_data.get('port_range', self.discovery.port_range)
                self.discovery.timeout = disc_data.get('timeout', self.discovery.timeout)
                self.discovery.retry_attempts = disc_data.get('retry_attempts', self.discovery.retry_attempts)
            
            if 'sync' in data:
                sync_data = data['sync']
                self.sync.interval = sync_data.get('interval', self.sync.interval)
                self.sync.batch_size = sync_data.get('batch_size', self.sync.batch_size)
                self.sync.retry_failed = sync_data.get('retry_failed', self.sync.retry_failed)
            
            if 'logging' in data:
                log_data = data['logging']
                self.logging.level = log_data.get('level', self.logging.level)
                self.logging.file = log_data.get('file', self.logging.file)
                
        except Exception as e:
            # If config file is invalid, use defaults
            pass
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # API config
        self.api.token = os.getenv('STORJCLOUD_API_TOKEN', self.api.token)
        self.api.endpoint = os.getenv('STORJCLOUD_DASHBOARD_URL', self.api.endpoint)
        
        if timeout := os.getenv('STORJCLOUD_API_TIMEOUT'):
            try:
                self.api.timeout = int(timeout)
            except ValueError:
                pass
        
        # Discovery config
        self.discovery.docker_host = os.getenv('DOCKER_HOST', self.discovery.docker_host)
        
        if from_docker := os.getenv('STORJCLOUD_FROM_DOCKER'):
            self.discovery.from_docker = from_docker.lower() in ('true', '1', 'yes')
        
        # Sync config
        if interval := os.getenv('STORJCLOUD_SYNC_INTERVAL'):
            try:
                self.sync.interval = int(interval)
            except ValueError:
                pass
        
        # Logging config
        self.logging.level = os.getenv('STORJCLOUD_LOG_LEVEL', self.logging.level)
        self.logging.file = os.getenv('STORJCLOUD_LOG_FILE', self.logging.file)
