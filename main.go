package main

import (
	"os"

	"github.com/elektryonuk/storjcloud-client/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}
