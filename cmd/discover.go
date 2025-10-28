package cmd

import (
	"fmt"
	"net"
	"strconv"
	"strings"
	"time"

	"github.com/elektryonuk/storjcloud-client/internal/discovery"
	"github.com/elektryonuk/storjcloud-client/internal/logger"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	serverIP    string
	customPorts string
	timeout     time.Duration
	outputJSON  bool
)

var discoverCmd = &cobra.Command{
	Use:   "discover",
	Short: "Discover Storj nodes on servers",
	Long: `Automatically discover Storj storage nodes running on local or remote servers.
Scans common dashboard ports and validates node accessibility.`,
	RunE: runDiscover,
}

func init() {
	rootCmd.AddCommand(discoverCmd)

	discoverCmd.Flags().StringVarP(&serverIP, "server", "s", "", "Server IP address (default: detect local IP)")
	discoverCmd.Flags().StringVarP(&customPorts, "ports", "p", "", "Custom port range (e.g., 14000,14001,14002)")
	discoverCmd.Flags().DurationVar(&timeout, "timeout", 5*time.Second, "Connection timeout per port")
	discoverCmd.Flags().BoolVar(&outputJSON, "json", false, "Output results in JSON format")
}

func runDiscover(cmd *cobra.Command, args []string) error {
	log := logger.New(viper.GetString("logging.level"))

	// Validate API token
	token := viper.GetString("api.token")
	if token == "" {
		return fmt.Errorf("API token required. Get one from %s/settings/api-tokens", viper.GetString("api.url"))
	}

	// Determine server IP
	if serverIP == "" {
		var err error
		serverIP, err = getLocalIP()
		if err != nil {
			return fmt.Errorf("failed to detect local IP: %w", err)
		}
		log.Infof("Using detected local IP: %s", serverIP)
	}

	// Parse custom ports or use defaults
	var ports []int
	if customPorts != "" {
		portStrs := strings.Split(customPorts, ",")
		for _, portStr := range portStrs {
			port, err := strconv.Atoi(strings.TrimSpace(portStr))
			if err != nil {
				return fmt.Errorf("invalid port: %s", portStr)
			}
			ports = append(ports, port)
		}
	} else {
		// Default ports for Storj node dashboards
		ports = []int{14000, 14001, 14002, 14003, 14004, 14005}
	}

	// Initialize discovery service
	discoveryService := discovery.New(discovery.Config{
		APIToken:     token,
		DashboardURL: viper.GetString("api.url"),
		Timeout:      timeout,
		Logger:       log,
	})

	// Run discovery
	log.Infof("Scanning %s on ports %v...", serverIP, ports)
	nodes, err := discoveryService.ScanServer(serverIP, ports)
	if err != nil {
		return fmt.Errorf("discovery failed: %w", err)
	}

	if len(nodes) == 0 {
		log.Warn("No Storj nodes found")
		return nil
	}

	// Display results
	log.Infof("Found %d Storj nodes:", len(nodes))
	for _, node := range nodes {
		log.Infof("  Node %s on port %d (Status: %s, Used: %.2f GB)",
			node.NodeID[:8], node.DashboardPort, node.Status,
			float64(node.DiskSpace.Used)/1e9)
	}

	// Register nodes with dashboard
	registered, err := discoveryService.RegisterNodes(nodes)
	if err != nil {
		return fmt.Errorf("failed to register nodes: %w", err)
	}

	log.Infof("Successfully registered %d nodes with Storj Cloud dashboard", registered)

	return nil
}

func getLocalIP() (string, error) {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		return "", err
	}
	defer conn.Close()

	localAddr := conn.LocalAddr().(*net.UDPAddr)
	return localAddr.IP.String(), nil
}
