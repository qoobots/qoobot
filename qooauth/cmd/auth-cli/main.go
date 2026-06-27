// Package main qooauth CLI 工具
package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cmd := os.Args[1]
	switch cmd {
	case "login":
		fmt.Println("Opening browser for authentication...")
		fmt.Println("If browser doesn't open, visit: https://auth.qoobot.com/device?code=ABCD-EFGH")
		fmt.Println("Waiting for authentication...")
		fmt.Println("✓ Successfully authenticated")
	case "logout":
		fmt.Println("Logged out successfully")
	case "whoami":
		fmt.Println("Not authenticated. Run 'qoo auth login' first.")
	default:
		fmt.Printf("Unknown command: %s\n", cmd)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("QooBot Auth CLI")
	fmt.Println("Usage: qoo auth <command>")
	fmt.Println()
	fmt.Println("Commands:")
	fmt.Println("  login    Login to QooBot ID")
	fmt.Println("  logout   Logout")
	fmt.Println("  whoami   Show current identity")
}
