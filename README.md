# Storj Cloud Python Client

Python client application for Storj node operators to automatically discover and sync node data with the [Storj Cloud monitoring dashboard](https://storj.cloud).

## Features

- 🐳 **Docker Integration** - Auto-discovers Storj nodes from Docker containers
- 🔍 **Port Detection** - Finds dashboard ports from container mappings and env vars
- 🔐 **Secure Authentication** - API token-based auth with your dashboard
- 📊 **Real-time Sync** - Continuous monitoring with configurable intervals
- ⚡ **PM2 Integration** - Runs as managed service with auto-restart
- 🐧 **Cross-platform** - Linux, Windows, macOS support

## Quick Setup

### Automated Installation
```bash
# Download and run setup script
wget https://raw.githubusercontent.com/ElektryonUK/storjcloud-client/main/setup.sh
chmod +x setup.sh
sudo ./setup.sh
```

### Manual Installation
```bash
# Clone repository
git clone https://github.com/ElektryonUK/storjcloud-client.git
cd storjcloud-client

# Install dependencies
pip3 install -r requirements.txt

# Install PM2 (if not already installed)
npm install -g pm2

# Make executable
chmod +x storjcloud-client.py
```

## Usage

### 1. Get API Token
1. Login to [https://storj.cloud](https://storj.cloud)
2. Go to **Settings** → **API Tokens**
3. Generate token with **Node Management** permissions

### 2. Discover Nodes

#### From Docker (Recommended)
```bash
# Auto-discover from Docker containers
./storjcloud-client.py discover --token YOUR_TOKEN --from-docker

# Discover from Docker on remote host
./storjcloud-client.py discover --token YOUR_TOKEN --from-docker --docker-host tcp://192.168.1.100:2375
```

#### Custom Port Scanning
```bash
# Specific ports
./storjcloud-client.py discover --token YOUR_TOKEN --ports 14000,14001,14002,14003

# Port range
./storjcloud-client.py discover --token YOUR_TOKEN --port-range 14000-14005

# Auto-detect common ports
./storjcloud-client.py discover --token YOUR_TOKEN --auto
```

### 3. Start Monitoring Service

#### Using PM2 (Recommended)
```bash
# Install as PM2 service
./storjcloud-client.py install-service --token YOUR_TOKEN

# Start service
pm2 start storjcloud-sync

# Check status
pm2 status
pm2 logs storjcloud-sync
```

#### Direct Sync
```bash
# Start sync daemon
./storjcloud-client.py sync --token YOUR_TOKEN --interval 300
```

## Configuration

### Environment Variables
```bash
export STORJCLOUD_API_TOKEN="your_token_here"
export STORJCLOUD_DASHBOARD_URL="https://storj.cloud"
export STORJCLOUD_SYNC_INTERVAL="300"
export STORJCLOUD_LOG_LEVEL="info"
export DOCKER_HOST="unix:///var/run/docker.sock"  # or tcp://host:2375
```

### Config File
```yaml
# ~/.storjcloud/config.yaml
api:
  token: "your_token_here"
  endpoint: "https://storj.cloud/api/v1"
  timeout: 30

discovery:
  from_docker: true
  docker_host: "unix:///var/run/docker.sock"
  custom_ports: [14000, 14001, 14002, 14003]
  port_range: [14000, 14010]
  timeout: 5
  retry_attempts: 3

sync:
  interval: 300
  batch_size: 10
  retry_failed: true

logging:
  level: "info"
  file: "/var/log/storjcloud-client.log"
```

## Docker Discovery

The client automatically discovers Storj nodes by:

1. **Container Detection** - Finds containers with `storjlabs/storagenode` image
2. **Port Mapping** - Resolves host ports mapped to container port 14002
3. **Environment Parsing** - Reads `CONSOLE_ADDRESS` for custom dashboard ports
4. **API Validation** - Probes `/api/sno` endpoint to confirm node accessibility
5. **Metadata Extraction** - Gets node ID, version, and status information

## PM2 Service Management

```bash
# Service lifecycle
pm2 start storjcloud-sync    # Start service
pm2 stop storjcloud-sync     # Stop service
pm2 restart storjcloud-sync  # Restart service
pm2 delete storjcloud-sync   # Remove service

# Monitoring
pm2 status                   # Service status
pm2 logs storjcloud-sync     # View logs
pm2 monit                    # Real-time monitoring

# Persistence
pm2 save                     # Save current processes
pm2 startup                  # Setup auto-start on boot
```

## Architecture

```
┌─────────────────┐    ┌────────────────────┐    ┌─────────────────┐
│  Docker Engine  │◄──┤ StorjCloud Client  ├───►│ StorjCloud API  │
│   (Containers)  │    │   (Python + PM2)   │    │   (Dashboard)   │
└─────────────────┘    └────────────────────┘    └─────────────────┘
         │                       │                       │
    Container Info           HTTP Requests              HTTPS API
    Port Mappings           Node Discovery            Authentication
    Environment Vars        Data Synchronisation       Database Storage
```

## Development

### Setup Development Environment
```bash
git clone https://github.com/ElektryonUK/storjcloud-client.git
cd storjcloud-client
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running Tests
```bash
pytest tests/
pytest tests/ --cov=src/
```

### Code Formatting
```bash
black src/
flake8 src/
mypy src/
```

## Troubleshooting

### Docker Permission Issues
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Re-login or run:
newgrp docker
```

### API Token Issues
```bash
# Test token validity
./storjcloud-client.py auth --token YOUR_TOKEN

# Generate new token at:
https://storj.cloud/settings/api-tokens
```

### Service Issues
```bash
# Check PM2 logs
pm2 logs storjcloud-sync --lines 50

# Restart service
pm2 restart storjcloud-sync

# Check system resources
pm2 monit
```

## Support

- 📧 **Email**: support@storj.cloud
- 🐛 **Issues**: [GitHub Issues](https://github.com/ElektryonUK/storjcloud-client/issues)
- 📚 **Docs**: [https://docs.storj.cloud](https://docs.storj.cloud)

---

**Made with 🐍 and ❤️ for the Storj community**