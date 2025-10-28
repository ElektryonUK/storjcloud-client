"""
Node synchronization service

Continuously monitors registered Storj nodes and syncs their data
with the Storj Cloud monitoring dashboard.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp


class NodeSync:
    """Synchronizes node data with dashboard"""
    
    def __init__(self, api_token: str, dashboard_url: str, interval: int = 300,
                 batch_size: int = 10, retry_failed: bool = True, logger=None):
        self.api_token = api_token
        self.dashboard_url = dashboard_url.rstrip('/')
        self.interval = interval
        self.batch_size = batch_size
        self.retry_failed = retry_failed
        self.logger = logger or logging.getLogger(__name__)
        
        self.session = None
        self.running = False
    
    async def start(self):
        """Start the sync daemon"""
        self.running = True
        self.session = aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {self.api_token}'}
        )
        
        self.logger.info("Sync daemon started")
        
        try:
            while self.running:
                await self._sync_cycle()
                await asyncio.sleep(self.interval)
        except KeyboardInterrupt:
            self.logger.info("Sync daemon interrupted")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the sync daemon"""
        self.running = False
        if self.session:
            await self.session.close()
        self.logger.info("Sync daemon stopped")
    
    async def _sync_cycle(self):
        """Perform one sync cycle"""
        try:
            # Get registered nodes from dashboard
            nodes = await self._get_registered_nodes()
            if not nodes:
                self.logger.debug("No registered nodes found")
                return
            
            self.logger.info("Syncing %d nodes", len(nodes))
            
            # Process nodes in batches
            for i in range(0, len(nodes), self.batch_size):
                batch = nodes[i:i + self.batch_size]
                await self._sync_batch(batch)
            
            self.logger.info("Sync cycle completed")
            
        except Exception as e:
            self.logger.error("Sync cycle failed: %s", e)
    
    async def _get_registered_nodes(self) -> List[Dict]:
        """Get list of registered nodes from dashboard"""
        url = f"{self.dashboard_url}/storj/nodes"
        
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('nodes', [])
                else:
                    self.logger.error("Failed to get nodes: HTTP %d", response.status)
                    return []
        except Exception as e:
            self.logger.error("Failed to get registered nodes: %s", e)
            return []
    
    async def _sync_batch(self, nodes: List[Dict]):
        """Sync a batch of nodes"""
        tasks = [self._sync_node(node) for node in nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        error_count = len(results) - success_count
        
        if error_count > 0:
            self.logger.warning("Batch sync: %d success, %d errors", success_count, error_count)
    
    async def _sync_node(self, node: Dict) -> bool:
        """Sync a single node"""
        try:
            # Fetch current node data
            node_data = await self._fetch_node_data(node)
            if not node_data:
                self.logger.warning("Failed to fetch data for node %s", node.get('nodeId', 'unknown'))
                return False
            
            # Update node in dashboard
            success = await self._update_node(node['id'], node_data)
            if success:
                self.logger.debug("Synced node %s", node.get('nodeId', 'unknown')[:8])
            
            return success
            
        except Exception as e:
            self.logger.error("Failed to sync node %s: %s", node.get('nodeId', 'unknown'), e)
            return False
    
    async def _fetch_node_data(self, node: Dict) -> Optional[Dict]:
        """Fetch current data from node dashboard API"""
        dashboard_port = node.get('dashboardPort') or 14002
        address = node.get('address', '127.0.0.1')
        url = f"http://{address}:{dashboard_port}/api/sno"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.debug("Node API returned %d for %s", response.status, url)
        except Exception as e:
            self.logger.debug("Failed to fetch from %s: %s", url, e)
        
        return None
    
    async def _update_node(self, node_id: str, node_data: Dict) -> bool:
        """Update node data in dashboard"""
        url = f"{self.dashboard_url}/storj/nodes/{node_id}"
        
        # Transform node data for dashboard API
        update_data = {
            'status': self._determine_status(node_data),
            'version': node_data.get('version'),
            'usedSpace': node_data.get('diskSpace', {}).get('used', 0),
            'availableSpace': node_data.get('diskSpace', {}).get('available', 0),
            'bandwidthUsed': node_data.get('bandwidth', {}).get('used', 0),
            'uptime': node_data.get('uptime', 0),
            'lastSeen': datetime.utcnow().isoformat(),
            'reputation': node_data.get('reputation', {}),
            'satellites': node_data.get('satellites', []),
            'auditScore': node_data.get('reputation', {}).get('auditScore'),
            'suspensionScore': node_data.get('reputation', {}).get('suspensionScore'),
        }
        
        try:
            async with self.session.patch(url, json=update_data) as response:
                if response.status in [200, 204]:
                    return True
                else:
                    self.logger.error("Failed to update node %s: HTTP %d", node_id, response.status)
                    if response.status == 401:
                        self.logger.error("Authentication failed - check API token")
                    return False
        except Exception as e:
            self.logger.error("Failed to update node %s: %s", node_id, e)
            return False
    
    def _determine_status(self, node_data: Dict) -> str:
        """Determine node status from API data"""
        if not node_data.get('lastContactSuccess'):
            return 'OFFLINE'
        
        # Check if node is disqualified
        if node_data.get('disqualified'):
            return 'DISQUALIFIED'
        
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
