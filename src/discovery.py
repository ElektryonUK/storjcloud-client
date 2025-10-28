"""
Docker-based Storj node discovery

Automatically discovers Storj storage nodes running in Docker containers
by inspecting container metadata, port mappings, and environment variables.
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional

import aiohttp
import docker
from docker.errors import DockerException


class DockerDiscovery:
    """Discovers Storj nodes from Docker containers"""
    
    def __init__(self, docker_host: str = "unix:///var/run/docker.sock", logger=None):
        self.docker_host = docker_host
        self.logger = logger or logging.getLogger(__name__)
        self.client = None
    
    async def discover_nodes(self) -> List[Dict]:
        """Discover all Storj nodes from Docker containers"""
        try:
            self.client = docker.DockerClient(base_url=self.docker_host)
            self.client.ping()  # Test connection
            
            containers = self._get_storj_containers()
            self.logger.info("Found %d Storj containers", len(containers))
            
            nodes = []
            for container in containers:
                node_info = await self._extract_node_info(container)
                if node_info:
                    nodes.append(node_info)
            
            return nodes
            
        except DockerException as e:
            self.logger.error("Docker connection failed: %s", e)
            return []
        finally:
            if self.client:
                self.client.close()
    
    def _get_storj_containers(self) -> List:
        """Get all running Storj storage node containers"""
        try:
            # Find containers with Storj images
            containers = self.client.containers.list(
                filters={
                    'status': 'running',
                    'ancestor': ['storjlabs/storagenode', 'storj/storagenode']
                }
            )
            
            # Also check for containers with storj in the name
            all_containers = self.client.containers.list(filters={'status': 'running'})
            for container in all_containers:
                if any(name for name in container.attrs.get('Names', []) 
                      if 'storj' in name.lower() or 'storagenode' in name.lower()):
                    if container not in containers:
                        containers.append(container)
            
            return containers
            
        except Exception as e:
            self.logger.error("Failed to list containers: %s", e)
            return []
    
    async def _extract_node_info(self, container) -> Optional[Dict]:
        """Extract node information from container"""
        try:
            # Get container details
            container.reload()
            attrs = container.attrs
            
            # Extract basic info
            name = attrs['Name'].lstrip('/')
            image = attrs['Config']['Image']
            
            # Get dashboard port
            dashboard_port = self._get_dashboard_port(attrs)
            if not dashboard_port:
                self.logger.warning("No dashboard port found for container %s", name)
                return None
            
            # Get host IP (use 127.0.0.1 for local containers)
            host_ip = '127.0.0.1'
            
            # Try to get node data from dashboard API
            node_data = await self._fetch_node_data(host_ip, dashboard_port)
            if not node_data:
                self.logger.warning("Could not fetch node data for %s:%d", host_ip, dashboard_port)
                return None
            
            return {
                'node_id': node_data.get('nodeID', ''),
                'name': name,
                'address': host_ip,
                'dashboard_port': dashboard_port,
                'storage_port': self._get_storage_port(attrs),
                'version': node_data.get('version', ''),
                'status': self._determine_status(node_data),
                'disk_space': {
                    'used': node_data.get('diskSpace', {}).get('used', 0),
                    'available': node_data.get('diskSpace', {}).get('available', 0),
                    'total': node_data.get('diskSpace', {}).get('used', 0) + 
                           node_data.get('diskSpace', {}).get('available', 0)
                },
                'bandwidth': node_data.get('bandwidth', {}),
                'uptime': node_data.get('uptime', 0),
                'last_contact': node_data.get('lastContactSuccess'),
                'container_id': container.id,
                'container_name': name,
                'image': image,
                'detected_from': 'docker'
            }
            
        except Exception as e:
            self.logger.error("Failed to extract info from container %s: %s", 
                            container.name, e)
            return None
    
    def _get_dashboard_port(self, attrs: Dict) -> Optional[int]:
        """Extract dashboard port from container configuration"""
        # Check port mappings first
        ports = attrs.get('NetworkSettings', {}).get('Ports', {})
        
        # Look for mapped port 14002 (default dashboard port)
        if '14002/tcp' in ports and ports['14002/tcp']:
            host_port = ports['14002/tcp'][0]['HostPort']
            return int(host_port)
        
        # Check environment variables for CONSOLE_ADDRESS
        env_vars = attrs.get('Config', {}).get('Env', [])
        for env_var in env_vars:
            if env_var.startswith('CONSOLE_ADDRESS='):
                address = env_var.split('=', 1)[1]
                # Extract port from address like "127.0.0.1:14002"
                if ':' in address:
                    return int(address.split(':')[-1])
        
        # Look for any port mapping that might be dashboard
        for port_spec, mapping in ports.items():
            if mapping and port_spec.endswith('/tcp'):
                container_port = int(port_spec.split('/')[0])
                # Dashboard ports are typically in 14000-15000 range
                if 14000 <= container_port <= 15000:
                    return int(mapping[0]['HostPort'])
        
        return None
    
    def _get_storage_port(self, attrs: Dict) -> int:
        """Extract storage port from container configuration"""
        # Check port mappings for 28967 (default storage port)
        ports = attrs.get('NetworkSettings', {}).get('Ports', {})
        
        if '28967/tcp' in ports and ports['28967/tcp']:
            return int(ports['28967/tcp'][0]['HostPort'])
        
        # Check environment variables
        env_vars = attrs.get('Config', {}).get('Env', [])
        for env_var in env_vars:
            if env_var.startswith('ADDRESS='):
                address = env_var.split('=', 1)[1]
                if ':' in address:
                    return int(address.split(':')[-1])
        
        return 28967  # Default
    
    async def _fetch_node_data(self, host: str, port: int) -> Optional[Dict]:
        """Fetch node data from dashboard API"""
        url = f"http://{host}:{port}/api/sno"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.debug("API request failed: %s %d", url, response.status)
        except Exception as e:
            self.logger.debug("Failed to fetch node data from %s: %s", url, e)
        
        return None
    
    def _determine_status(self, node_data: Dict) -> str:
        """Determine node status from API data"""
        if not node_data.get('lastContactSuccess'):
            return 'OFFLINE'
        
        # Check reputation scores
        if 'reputation' in node_data:
            reputation = node_data['reputation']
            audit_score = reputation.get('auditScore', 1.0)
            suspension_score = reputation.get('suspensionScore', 0.0)
            
            if suspension_score > 0:
                return 'SUSPENDED'
            elif audit_score < 0.95:
                return 'WARNING'
        
        return 'ONLINE'


class PortScanner:
    """Scans specific ports for Storj nodes"""
    
    def __init__(self, host: str, timeout: int = 5, logger=None):
        self.host = host
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)
    
    async def scan_ports(self, ports: List[int]) -> List[Dict]:
        """Scan list of ports for Storj nodes"""
        tasks = [self._check_port(port) for port in ports]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        nodes = []
        for result in results:
            if isinstance(result, dict):  # Successful result
                nodes.append(result)
        
        return nodes
    
    async def _check_port(self, port: int) -> Optional[Dict]:
        """Check if a specific port has a Storj node"""
        url = f"http://{self.host}:{port}/api/sno"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status == 200:
                        node_data = await response.json()
                        
                        return {
                            'node_id': node_data.get('nodeID', ''),
                            'name': f"Node-{port}",
                            'address': self.host,
                            'dashboard_port': port,
                            'storage_port': 28967,  # Default
                            'version': node_data.get('version', ''),
                            'status': self._determine_status(node_data),
                            'disk_space': {
                                'used': node_data.get('diskSpace', {}).get('used', 0),
                                'available': node_data.get('diskSpace', {}).get('available', 0),
                                'total': node_data.get('diskSpace', {}).get('used', 0) + 
                                       node_data.get('diskSpace', {}).get('available', 0)
                            },
                            'bandwidth': node_data.get('bandwidth', {}),
                            'uptime': node_data.get('uptime', 0),
                            'last_contact': node_data.get('lastContactSuccess'),
                            'detected_from': 'port_scan'
                        }
        except Exception as e:
            self.logger.debug("Port %d check failed: %s", port, e)
        
        return None
    
    def _determine_status(self, node_data: Dict) -> str:
        """Determine node status from API data"""
        if not node_data.get('lastContactSuccess'):
            return 'OFFLINE'
        
        # Check reputation scores
        if 'reputation' in node_data:
            reputation = node_data['reputation']
            audit_score = reputation.get('auditScore', 1.0)
            suspension_score = reputation.get('suspensionScore', 0.0)
            
            if suspension_score > 0:
                return 'SUSPENDED'
            elif audit_score < 0.95:
                return 'WARNING'
        
        return 'ONLINE'
