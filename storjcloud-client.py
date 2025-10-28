#!/usr/bin/env python3
"""
Storj Cloud Client

Automatically discover and sync Storj storage nodes with the Storj Cloud monitoring dashboard.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

# Import our modules
from src.discovery import DockerDiscovery, PortScanner
from src.sync import NodeSync
from src.auth import AuthManager
from src.config import Config
from src.pm2 import PM2Manager
from src.logger import setup_logger


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logger(args.log_level or 'info')
    
    # Load configuration
    config = Config.load(args.config)
    
    # Override config with CLI args
    if args.token:
        config.api.token = args.token
    if args.url:
        config.api.endpoint = args.url
    
    # Validate configuration
    if not config.api.token and args.command not in ['install-service', 'help']:
        logger.error("API token required. Get one from %s/settings/api-tokens", config.api.endpoint)
        sys.exit(1)
    
    # Route to command handlers
    try:
        if args.command == 'discover':
            asyncio.run(handle_discover(args, config, logger))
        elif args.command == 'sync':
            asyncio.run(handle_sync(args, config, logger))
        elif args.command == 'install-service':
            handle_install_service(args, config, logger)
        elif args.command == 'auth':
            asyncio.run(handle_auth(args, config, logger))
        else:
            parser.print_help()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Command failed: %s", e)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create command line parser"""
    parser = argparse.ArgumentParser(
        description="Storj Cloud monitoring client",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global options
    parser.add_argument('--config', '-c', help='Config file path')
    parser.add_argument('--token', '-t', help='API token from Storj Cloud dashboard')
    parser.add_argument('--url', help='Dashboard URL (default: https://storj.cloud)')
    parser.add_argument('--log-level', choices=['debug', 'info', 'warn', 'error'], help='Log level')
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Discover command
    discover_parser = subparsers.add_parser('discover', help='Discover Storj nodes')
    discover_parser.add_argument('--from-docker', action='store_true', help='Discover from Docker containers')
    discover_parser.add_argument('--docker-host', help='Docker host (default: unix:///var/run/docker.sock)')
    discover_parser.add_argument('--server', '-s', help='Server IP address')
    discover_parser.add_argument('--ports', '-p', help='Custom ports (comma-separated)')
    discover_parser.add_argument('--port-range', help='Port range (e.g., 14000-14005)')
    discover_parser.add_argument('--auto', action='store_true', help='Auto-detect common ports')
    discover_parser.add_argument('--timeout', type=int, default=5, help='Connection timeout')
    discover_parser.add_argument('--json', action='store_true', help='Output JSON')
    
    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Start sync daemon')
    sync_parser.add_argument('--interval', '-i', type=int, default=300, help='Sync interval (seconds)')
    sync_parser.add_argument('--batch-size', type=int, default=10, help='Batch size for parallel sync')
    sync_parser.add_argument('--retry-failed', action='store_true', help='Retry failed syncs')
    
    # Service management
    service_parser = subparsers.add_parser('install-service', help='Install as PM2 service')
    service_parser.add_argument('--name', default='storjcloud-sync', help='Service name')
    
    # Auth testing
    auth_parser = subparsers.add_parser('auth', help='Test authentication')
    
    return parser


async def handle_discover(args, config: Config, logger):
    """Handle discover command"""
    logger.info("Starting node discovery...")
    
    discovered_nodes = []
    
    if args.from_docker:
        # Docker-based discovery
        docker_host = args.docker_host or config.discovery.docker_host
        discovery = DockerDiscovery(docker_host, logger)
        docker_nodes = await discovery.discover_nodes()
        discovered_nodes.extend(docker_nodes)
        logger.info("Found %d nodes from Docker", len(docker_nodes))
    
    if args.ports or args.port_range or args.auto:
        # Port-based discovery
        server_ip = args.server or '127.0.0.1'
        scanner = PortScanner(server_ip, args.timeout, logger)
        
        if args.ports:
            ports = [int(p.strip()) for p in args.ports.split(',')]
        elif args.port_range:
            start, end = map(int, args.port_range.split('-'))
            ports = list(range(start, end + 1))
        else:  # auto
            ports = config.discovery.common_ports
        
        port_nodes = await scanner.scan_ports(ports)
        discovered_nodes.extend(port_nodes)
        logger.info("Found %d nodes from port scanning", len(port_nodes))
    
    if not discovered_nodes:
        logger.warning("No nodes discovered")
        return
    
    # Remove duplicates based on node ID
    unique_nodes = {}
    for node in discovered_nodes:
        unique_nodes[node['node_id']] = node
    
    discovered_nodes = list(unique_nodes.values())
    logger.info("Total unique nodes found: %d", len(discovered_nodes))
    
    # Output results
    if args.json:
        print(json.dumps(discovered_nodes, indent=2, default=str))
    else:
        for node in discovered_nodes:
            logger.info("Node %s on %s:%d (Status: %s, Used: %.2f GB)",
                       node['node_id'][:8], node['address'], node['dashboard_port'],
                       node['status'], node['disk_space']['used'] / 1e9)
    
    # Register with dashboard
    auth = AuthManager(config.api.token, config.api.endpoint)
    registered = await auth.register_nodes(discovered_nodes)
    logger.info("Successfully registered %d nodes with dashboard", registered)


async def handle_sync(args, config: Config, logger):
    """Handle sync command"""
    logger.info("Starting sync daemon...")
    logger.info("Sync interval: %d seconds", args.interval)
    
    sync_service = NodeSync(
        config.api.token,
        config.api.endpoint,
        args.interval,
        args.batch_size,
        args.retry_failed,
        logger
    )
    
    await sync_service.start()


def handle_install_service(args, config: Config, logger):
    """Handle service installation"""
    logger.info("Installing PM2 service...")
    
    pm2 = PM2Manager(logger)
    
    # Create service configuration
    service_config = {
        'name': args.name,
        'script': os.path.abspath(__file__),
        'args': f'sync --token {config.api.token}',
        'cwd': os.getcwd(),
        'env': {
            'STORJCLOUD_API_TOKEN': config.api.token,
            'STORJCLOUD_DASHBOARD_URL': config.api.endpoint,
        },
        'error_file': f'/var/log/{args.name}-error.log',
        'out_file': f'/var/log/{args.name}-out.log',
        'log_file': f'/var/log/{args.name}.log',
        'time': True,
        'autorestart': True,
        'watch': False,
        'max_memory_restart': '200M'
    }
    
    pm2.install_service(service_config)
    logger.info("Service installed successfully!")
    logger.info("Start with: pm2 start %s", args.name)


async def handle_auth(args, config: Config, logger):
    """Handle auth testing"""
    logger.info("Testing authentication...")
    
    auth = AuthManager(config.api.token, config.api.endpoint)
    user_info = await auth.test_token()
    
    if user_info:
        logger.info("Authentication successful!")
        logger.info("User: %s", user_info.get('email', 'Unknown'))
        logger.info("Permissions: %s", ', '.join(user_info.get('permissions', [])))
    else:
        logger.error("Authentication failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
