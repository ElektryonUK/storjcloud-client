#!/bin/bash

# Storj Cloud Client Setup Script
# Installs Python client with PM2 integration for automatic Storj node discovery and monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLIENT_DIR="/opt/storjcloud-client"
LOG_DIR="/var/log/storjcloud"
CONFIG_DIR="/etc/storjcloud"
SERVICE_USER="storjcloud"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Storj Cloud Client Setup                 ║${NC}"
echo -e "${BLUE}║            Automatic Node Discovery & Monitoring             ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   echo "Usage: sudo ./setup.sh"
   exit 1
fi

# Detect OS
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}Error: Cannot detect operating system${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Detected OS: $PRETTY_NAME${NC}"

# Install system dependencies
echo -e "${YELLOW}📦 Installing system dependencies...${NC}"

case $OS in
    ubuntu|debian)
        apt-get update
        apt-get install -y python3 python3-pip python3-venv curl software-properties-common
        
        # Install Node.js and npm for PM2
        if ! command -v node &> /dev/null; then
            curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
            apt-get install -y nodejs
        fi
        ;;
    centos|rhel|fedora)
        if command -v dnf &> /dev/null; then
            dnf install -y python3 python3-pip curl
        else
            yum install -y python3 python3-pip curl
        fi
        
        # Install Node.js and npm for PM2
        if ! command -v node &> /dev/null; then
            curl -fsSL https://rpm.nodesource.com/setup_lts.x | bash -
            if command -v dnf &> /dev/null; then
                dnf install -y nodejs
            else
                yum install -y nodejs
            fi
        fi
        ;;
    *)
        echo -e "${RED}Error: Unsupported operating system: $OS${NC}"
        exit 1
        ;;
esac

# Install PM2
echo -e "${YELLOW}🔧 Installing PM2 process manager...${NC}"
if ! command -v pm2 &> /dev/null; then
    npm install -g pm2
fi

# Create service user
echo -e "${YELLOW}👤 Creating service user...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd --system --home-dir $CLIENT_DIR --shell /bin/false $SERVICE_USER
    usermod -aG docker $SERVICE_USER 2>/dev/null || echo "Warning: Docker group not found, skipping"
fi

# Create directories
echo -e "${YELLOW}📁 Creating directories...${NC}"
mkdir -p $CLIENT_DIR $LOG_DIR $CONFIG_DIR
chown -R $SERVICE_USER:$SERVICE_USER $CLIENT_DIR $LOG_DIR
chmod 755 $CONFIG_DIR

# Download client files
echo -e "${YELLOW}📥 Downloading Storj Cloud client...${NC}"
cd $CLIENT_DIR

# Clone the repository
if [[ -d ".git" ]]; then
    git pull
else
    git clone https://github.com/ElektryonUK/storjcloud-client.git .
fi

# Set up Python virtual environment
echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
sudo -u $SERVICE_USER python3 -m venv venv
sudo -u $SERVICE_USER ./venv/bin/pip install --upgrade pip
sudo -u $SERVICE_USER ./venv/bin/pip install -r requirements.txt

# Make client executable
chmod +x storjcloud-client.py
chown $SERVICE_USER:$SERVICE_USER storjcloud-client.py

# Create wrapper script for PM2
cat > $CLIENT_DIR/run-client.sh << EOF
#!/bin/bash
cd $CLIENT_DIR
./venv/bin/python3 storjcloud-client.py "\$@"
EOF

chmod +x $CLIENT_DIR/run-client.sh
chown $SERVICE_USER:$SERVICE_USER $CLIENT_DIR/run-client.sh

# Create symlink for global access
ln -sf $CLIENT_DIR/run-client.sh /usr/local/bin/storjcloud-client

# Create default configuration
echo -e "${YELLOW}⚙️ Creating default configuration...${NC}"
cat > $CONFIG_DIR/config.yaml << EOF
api:
  endpoint: "https://storj.cloud/api/v1"
  timeout: 30

discovery:
  from_docker: true
  docker_host: "unix:///var/run/docker.sock"
  common_ports: [14000, 14001, 14002, 14003, 14004, 14005]
  port_range: [14000, 14010]
  timeout: 5
  retry_attempts: 3

sync:
  interval: 300
  batch_size: 10
  retry_failed: true

logging:
  level: "info"
  file: "$LOG_DIR/storjcloud-client.log"
EOF

# Set up log rotation
echo -e "${YELLOW}📝 Setting up log rotation...${NC}"
cat > /etc/logrotate.d/storjcloud-client << EOF
$LOG_DIR/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $SERVICE_USER $SERVICE_USER
    postrotate
        pm2 reload storjcloud-sync 2>/dev/null || true
    endscript
}
EOF

# Create systemd service for PM2 persistence
echo -e "${YELLOW}🚀 Setting up PM2 persistence...${NC}"
sudo -u $SERVICE_USER pm2 startup systemd

# Set PM2_HOME for service user
echo "export PM2_HOME=$CLIENT_DIR/.pm2" >> /home/$SERVICE_USER/.bashrc 2>/dev/null || true

echo
echo -e "${GREEN}✅ Installation completed successfully!${NC}"
echo
echo -e "${BLUE}📋 Next steps:${NC}"
echo -e "${YELLOW}1.${NC} Get your API token from https://storj.cloud/settings/api-tokens"
echo -e "${YELLOW}2.${NC} Discover your nodes:"
echo -e "   ${BLUE}storjcloud-client discover --token YOUR_TOKEN --from-docker${NC}"
echo -e "${YELLOW}3.${NC} Install monitoring service:"
echo -e "   ${BLUE}storjcloud-client install-service --token YOUR_TOKEN${NC}"
echo -e "${YELLOW}4.${NC} Start the service:"
echo -e "   ${BLUE}pm2 start storjcloud-sync${NC}"
echo -e "   ${BLUE}pm2 save${NC}"
echo
echo -e "${BLUE}🔧 Management commands:${NC}"
echo -e "   ${BLUE}pm2 status${NC}           - Check service status"
echo -e "   ${BLUE}pm2 logs storjcloud-sync${NC} - View logs"
echo -e "   ${BLUE}pm2 restart storjcloud-sync${NC} - Restart service"
echo -e "   ${BLUE}pm2 stop storjcloud-sync${NC} - Stop service"
echo
echo -e "${GREEN}🎉 Your Storj nodes will now be automatically monitored!${NC}"
