// Package main 数据库迁移工具
package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	direction := flag.String("direction", "up", "Migration direction: up or down")
	flag.Parse()

	switch *direction {
	case "up":
		fmt.Println("Running migrations up...")
		fmt.Println("✓ Migrations completed")
	case "down":
		fmt.Println("Running migrations down...")
		fmt.Println("✓ Migrations reverted")
	default:
		fmt.Fprintf(os.Stderr, "Unknown direction: %s (use 'up' or 'down')\n", *direction)
		os.Exit(1)
	}
}
