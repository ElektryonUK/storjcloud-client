"""
PM2 process manager integration

Handles installation, configuration, and management of the client as a PM2 service.
"""

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional


class PM2Manager:
    """Manages PM2 service installation and control"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def is_pm2_installed(self) -> bool:
        """Check if PM2 is installed"""
        try:
            result = subprocess.run(['pm2', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_service(self, config: Dict) -> bool:
        """Install client as PM2 service"""
        if not self.is_pm2_installed():
            self.logger.error("PM2 is not installed. Install with: npm install -g pm2")
            return False
        
        try:
            # Create PM2 ecosystem file
            ecosystem_path = self._create_ecosystem_file(config)
            
            # Stop existing service if running
            self._stop_service(config['name'])
            
            # Start service from ecosystem file
            result = subprocess.run(
                ['pm2', 'start', str(ecosystem_path)],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self.logger.info("PM2 service installed successfully")
                
                # Save PM2 process list
                subprocess.run(['pm2', 'save'], capture_output=True)
                
                return True
            else:
                self.logger.error("Failed to start PM2 service: %s", result.stderr)
                return False
                
        except Exception as e:
            self.logger.error("Failed to install PM2 service: %s", e)
            return False
    
    def _create_ecosystem_file(self, config: Dict) -> Path:
        """Create PM2 ecosystem configuration file"""
        ecosystem_config = {
            'apps': [{
                'name': config['name'],
                'script': config['script'],
                'args': config.get('args', ''),
                'cwd': config.get('cwd', os.getcwd()),
                'env': config.get('env', {}),
                'error_file': config.get('error_file', f"/var/log/{config['name']}-error.log"),
                'out_file': config.get('out_file', f"/var/log/{config['name']}-out.log"),
                'log_file': config.get('log_file', f"/var/log/{config['name']}.log"),
                'time': config.get('time', True),
                'autorestart': config.get('autorestart', True),
                'watch': config.get('watch', False),
                'max_memory_restart': config.get('max_memory_restart', '200M'),
                'instances': config.get('instances', 1),
                'exec_mode': config.get('exec_mode', 'fork'),
                'min_uptime': config.get('min_uptime', '10s'),
                'max_restarts': config.get('max_restarts', 15)
            }]
        }
        
        # Write ecosystem file
        ecosystem_path = Path(f"{config['name']}.config.js")
        with open(ecosystem_path, 'w') as f:
            f.write(f"module.exports = {json.dumps(ecosystem_config, indent=2)};")
        
        return ecosystem_path
    
    def _stop_service(self, service_name: str):
        """Stop existing PM2 service"""
        try:
            subprocess.run(['pm2', 'stop', service_name], capture_output=True)
            subprocess.run(['pm2', 'delete', service_name], capture_output=True)
        except Exception:
            pass  # Service might not exist
    
    def get_service_status(self, service_name: str) -> Optional[Dict]:
        """Get PM2 service status"""
        try:
            result = subprocess.run(
                ['pm2', 'jlist'], capture_output=True, text=True
            )
            
            if result.returncode == 0:
                processes = json.loads(result.stdout)
                for process in processes:
                    if process.get('name') == service_name:
                        return {
                            'name': process.get('name'),
                            'pid': process.get('pid'),
                            'status': process.get('pm2_env', {}).get('status'),
                            'uptime': process.get('pm2_env', {}).get('pm_uptime'),
                            'restarts': process.get('pm2_env', {}).get('restart_time'),
                            'memory': process.get('monit', {}).get('memory'),
                            'cpu': process.get('monit', {}).get('cpu')
                        }
        except Exception as e:
            self.logger.error("Failed to get service status: %s", e)
        
        return None
    
    def start_service(self, service_name: str) -> bool:
        """Start PM2 service"""
        try:
            result = subprocess.run(
                ['pm2', 'start', service_name], capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error("Failed to start service: %s", e)
            return False
    
    def stop_service(self, service_name: str) -> bool:
        """Stop PM2 service"""
        try:
            result = subprocess.run(
                ['pm2', 'stop', service_name], capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error("Failed to stop service: %s", e)
            return False
    
    def restart_service(self, service_name: str) -> bool:
        """Restart PM2 service"""
        try:
            result = subprocess.run(
                ['pm2', 'restart', service_name], capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error("Failed to restart service: %s", e)
            return False
    
    def delete_service(self, service_name: str) -> bool:
        """Delete PM2 service"""
        try:
            subprocess.run(['pm2', 'stop', service_name], capture_output=True)
            result = subprocess.run(
                ['pm2', 'delete', service_name], capture_output=True, text=True
            )
            subprocess.run(['pm2', 'save'], capture_output=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error("Failed to delete service: %s", e)
            return False
