"""
Authentication manager

Handles API token validation and node registration with the dashboard.
"""

import logging
from typing import Dict, List, Optional

import aiohttp


class AuthManager:
    """Manages authentication with Storj Cloud dashboard"""
    
    def __init__(self, api_token: str, dashboard_url: str, logger=None):
        self.api_token = api_token
        self.dashboard_url = dashboard_url.rstrip('/')
        self.logger = logger or logging.getLogger(__name__)
    
    async def test_token(self) -> Optional[Dict]:
        """Test API token validity and get user info"""
        url = f"{self.dashboard_url}/auth/me"
        headers = {'Authorization': f'Bearer {self.api_token}'}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
                        self.logger.info("Token valid for user: %s", user_data.get('email', 'Unknown'))
                        return user_data
                    elif response.status == 401:
                        self.logger.error("Invalid API token")
                    else:
                        self.logger.error("Token validation failed: HTTP %d", response.status)
        except Exception as e:
            self.logger.error("Token validation error: %s", e)
        
        return None
    
    async def register_nodes(self, nodes: List[Dict]) -> int:
        """Register discovered nodes with the dashboard"""
        if not nodes:
            return 0
        
        registered_count = 0
        
        async with aiohttp.ClientSession() as session:
            for node in nodes:
                if await self._register_single_node(session, node):
                    registered_count += 1
        
        return registered_count
    
    async def _register_single_node(self, session: aiohttp.ClientSession, node: Dict) -> bool:
        """Register a single node with the dashboard"""
        url = f"{self.dashboard_url}/storj/nodes"
        headers = {'Authorization': f'Bearer {self.api_token}'}
        
        # Prepare node data for registration
        node_data = {
            'nodeId': node['node_id'],
            'name': node.get('name', f"Node-{node['dashboard_port']}"),
            'address': node['address'],
            'port': node.get('storage_port', 28967),
            'dashboardPort': node['dashboard_port'],
            'version': node.get('version'),
            'status': node.get('status', 'UNKNOWN'),
            'allocatedSpace': node.get('disk_space', {}).get('total', 0),
            'usedSpace': node.get('disk_space', {}).get('used', 0),
            'availableSpace': node.get('disk_space', {}).get('available', 0),
            'bandwidthUsed': node.get('bandwidth', {}).get('used', 0),
            'uptime': node.get('uptime', 0),
            'lastSeen': node.get('last_contact'),
            'config': {
                'detectedFrom': node.get('detected_from'),
                'containerId': node.get('container_id'),
                'containerName': node.get('container_name'),
                'image': node.get('image')
            }
        }
        
        try:
            async with session.post(url, json=node_data, headers=headers) as response:
                if response.status in [200, 201]:
                    self.logger.info("Registered node %s (%s)", 
                                   node['node_id'][:8], node.get('name'))
                    return True
                elif response.status == 409:
                    # Node already exists, try to update it
                    self.logger.info("Node %s already exists, updating...", node['node_id'][:8])
                    return await self._update_existing_node(session, node, node_data)
                elif response.status == 401:
                    self.logger.error("Authentication failed - check API token")
                    return False
                else:
                    error_text = await response.text()
                    self.logger.error("Failed to register node %s: HTTP %d - %s", 
                                    node['node_id'][:8], response.status, error_text)
                    return False
        except Exception as e:
            self.logger.error("Failed to register node %s: %s", node['node_id'][:8], e)
            return False
    
    async def _update_existing_node(self, session: aiohttp.ClientSession, 
                                   node: Dict, node_data: Dict) -> bool:
        """Update an existing node's information"""
        url = f"{self.dashboard_url}/storj/nodes/{node['node_id']}"
        headers = {'Authorization': f'Bearer {self.api_token}'}
        
        try:
            async with session.patch(url, json=node_data, headers=headers) as response:
                if response.status in [200, 204]:
                    self.logger.info("Updated node %s", node['node_id'][:8])
                    return True
                else:
                    self.logger.error("Failed to update node %s: HTTP %d", 
                                    node['node_id'][:8], response.status)
                    return False
        except Exception as e:
            self.logger.error("Failed to update node %s: %s", node['node_id'][:8], e)
            return False
