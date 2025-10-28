# Storj Cloud Client Applications

Client applications for Storj node operators to automatically discover and sync node data with the [Storj Cloud monitoring dashboard](https://storj.cloud).

## Overview

This repository contains client-side applications that:
- 🔍 **Auto-discover** Storj nodes on your servers
- 📊 **Sync real-time data** with your Storj Cloud dashboard
- 🔐 **Authenticate securely** with your dashboard account
- 🎯 **Zero-config setup** for most common node configurations

## Client Applications

### Node Discovery Client
- **Purpose**: Scan servers for Storj nodes and register them automatically
- **Supports**: Multiple nodes per server, custom dashboard ports
- **Detection**: Auto-detects common ports (14000-14005, 15000-15005)
- **Authentication**: Uses API tokens from your Storj Cloud account

### Node Sync Daemon
- **Purpose**: Continuous monitoring and data synchronization
- **Features**: Real-time metrics, earnings tracking, alert forwarding
- **Deployment**: Runs as system service or Docker container
- **Frequency**: Configurable sync intervals (default: 5 minutes)

## Quick Start

### 1. Get Your API Token
1. Login to [https://storj.cloud](https://storj.cloud)
2. Go to **Settings** → **API Tokens**
3. Generate a new token with **Node Management** permissions

### 2. Install Client
```bash
# Download latest client
wget https://github.com/ElektryonUK/storjcloud-client/releases/latest/download/storjcloud-client-linux
chmod +x storjcloud-client-linux

# Or use Docker
docker pull elektryonuk/storjcloud-client:latest
```

### 3. Discover Nodes
```bash
# Auto-discover all nodes on current server
./storjcloud-client-linux discover --token YOUR_API_TOKEN

# Custom port range
./storjcloud-client-linux discover --token YOUR_API_TOKEN --ports 14000,14001,14002,14003

# Specific server IP
./storjcloud-client-linux discover --token YOUR_API_TOKEN --server 192.168.1.100
```

### 4. Start Monitoring
```bash
# Start sync daemon
./storjcloud-client-linux sync --token YOUR_API_TOKEN --interval 300s

# Install as system service
sudo ./storjcloud-client-linux install-service
```

## Features

### ✅ Auto-Discovery
- Scans common Storj dashboard ports
- Detects node ID, version, and configuration
- Validates node accessibility and API responses
- Supports multiple nodes per server

### ✅ Real-Time Monitoring
- Disk usage and availability
- Bandwidth utilization
- Earnings and payouts
- Satellite connections
- Audit scores and uptime

### ✅ Secure Authentication
- API token-based authentication
- Encrypted communication with dashboard
- No stored credentials on local system
- Revokable access tokens

### ✅ Multi-Platform Support
- Linux (x64, ARM64)
- Windows (x64)
- macOS (Intel, Apple Silicon)
- Docker containers

## Configuration

### Environment Variables
```bash
STORJCLOUD_API_TOKEN=your_api_token_here
STORJCLOUD_DASHBOARD_URL=https://storj.cloud
STORJCLOUD_SYNC_INTERVAL=300s
STORJCLOUD_LOG_LEVEL=info
```

### Config File
```yaml
# ~/.config/storjcloud/client.yaml
api:
  token: "your_api_token_here"
  endpoint: "https://storj.cloud/api/v1"
  timeout: 30s

discovery:
  ports: [14000, 14001, 14002, 14003, 14004, 14005]
  timeout: 5s
  retry_attempts: 3

sync:
  interval: 300s
  batch_size: 10
  retry_failed: true

logging:
  level: info
  file: "/var/log/storjcloud-client.log"
```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Storj Nodes   │◄───│ StorjCloud Client │───►│ StorjCloud API  │
│ (Dashboard APIs)│    │   (This Repo)    │    │ (Dashboard)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
    Port 14000-14005         HTTP Client              HTTPS API
    Local Dashboard         Authentication            JWT Tokens
    Real-time Data           Data Parsing            Database Storage
```

## Development

### Prerequisites
- Go 1.21+
- Docker (for containerized deployment)
- Access to Storj nodes for testing

### Build from Source
```bash
git clone https://github.com/ElektryonUK/storjcloud-client.git
cd storjcloud-client
go mod download
go build -o storjcloud-client ./cmd/client
```

### Run Tests
```bash
go test ./...
```

### Build Docker Image
```bash
docker build -t storjcloud-client .
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- 📧 **Email**: support@storj.cloud
- 💬 **Discord**: [Storj Cloud Community](https://discord.gg/storjcloud)
- 🐛 **Issues**: [GitHub Issues](https://github.com/ElektryonUK/storjcloud-client/issues)
- 📚 **Docs**: [https://docs.storj.cloud](https://docs.storj.cloud)

---

**Made with ❤️ for the Storj community**