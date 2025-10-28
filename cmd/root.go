package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	cfgFile string
	apiToken string
	dashboardURL string
	logLevel string
)

var rootCmd = &cobra.Command{
	Use:   "storjcloud-client",
	Short: "Storj Cloud monitoring client",
	Long: `A client application for Storj node operators to automatically
discover and sync node data with the Storj Cloud monitoring dashboard.

Authenticate with your dashboard account to enable automatic node
discovery and real-time monitoring synchronization.`,
}

func Execute() error {
	return rootCmd.Execute()
}

func init() {
	cobra.OnInitialize(initConfig)

	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.storjcloud.yaml)")
	rootCmd.PersistentFlags().StringVarP(&apiToken, "token", "t", "", "API token from Storj Cloud dashboard")
	rootCmd.PersistentFlags().StringVar(&dashboardURL, "url", "https://storj.cloud", "Dashboard URL")
	rootCmd.PersistentFlags().StringVar(&logLevel, "log-level", "info", "Log level (debug, info, warn, error)")

	viper.BindPFlag("api.token", rootCmd.PersistentFlags().Lookup("token"))
	viper.BindPFlag("api.url", rootCmd.PersistentFlags().Lookup("url"))
	viper.BindPFlag("logging.level", rootCmd.PersistentFlags().Lookup("log-level"))
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		home, err := os.UserHomeDir()
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error getting home directory: %v\n", err)
			os.Exit(1)
		}

		viper.AddConfigPath(home)
		viper.AddConfigPath(".")
		viper.SetConfigName(".storjcloud")
		viper.SetConfigType("yaml")
	}

	viper.SetEnvPrefix("STORJCLOUD")
	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err == nil {
		fmt.Fprintf(os.Stderr, "Using config file: %s\n", viper.ConfigFileUsed())
	}
}
