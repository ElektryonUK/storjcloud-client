package cmd

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/elektryonuk/storjcloud-client/internal/logger"
	"github.com/elektryonuk/storjcloud-client/internal/sync"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	syncInterval time.Duration
	batchSize    int
	retryFailed  bool
)

var syncCmd = &cobra.Command{
	Use:   "sync",
	Short: "Start continuous node data synchronization",
	Long: `Start the sync daemon to continuously monitor registered Storj nodes
and synchronize their data with the Storj Cloud dashboard.`,
	RunE: runSync,
}

func init() {
	rootCmd.AddCommand(syncCmd)

	syncCmd.Flags().DurationVarP(&syncInterval, "interval", "i", 5*time.Minute, "Sync interval")
	syncCmd.Flags().IntVar(&batchSize, "batch-size", 10, "Number of nodes to sync in parallel")
	syncCmd.Flags().BoolVar(&retryFailed, "retry-failed", true, "Retry failed sync attempts")
}

func runSync(cmd *cobra.Command, args []string) error {
	log := logger.New(viper.GetString("logging.level"))

	// Validate API token
	token := viper.GetString("api.token")
	if token == "" {
		return fmt.Errorf("API token required. Get one from %s/settings/api-tokens", viper.GetString("api.url"))
	}

	// Initialize sync service
	syncService := sync.New(sync.Config{
		APIToken:     token,
		DashboardURL: viper.GetString("api.url"),
		Interval:     syncInterval,
		BatchSize:    batchSize,
		RetryFailed:  retryFailed,
		Logger:       log,
	})

	// Setup graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start sync service
	log.Info("Starting Storj Cloud sync daemon...")
	log.Infof("Sync interval: %v", syncInterval)
	log.Infof("Batch size: %d", batchSize)

	errChan := make(chan error, 1)
	go func() {
		errChan <- syncService.Start(ctx)
	}()

	// Wait for shutdown signal or error
	select {
	case <-sigChan:
		log.Info("Received shutdown signal, stopping...")
		cancel()
	case err := <-errChan:
		if err != nil {
			return fmt.Errorf("sync service failed: %w", err)
		}
	}

	log.Info("Storj Cloud sync daemon stopped")
	return nil
}
