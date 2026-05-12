// N-Xyme MIND - Unified Personal AI System
// ================================
// Go rewrite to create a standalone binary like opencode.
//
// Usage:
//     nx-mind "task description"
//     nx-mind --agent hephaestus "fix the bug"
//     nx-mind --mode visual "design UI"
//     nx-mind interactive
//
// Build:
//     go build -o nx-mind ./cmd/nx-mind
//
// Install:
//     go install -o ~/.local/nx-mind/bin/nx-mind ./cmd/nx-mind

package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// Version
const Version = "1.0.0"

// Colors for TUI
const (
	ColorReset  = "\033[0m"
	ColorBold  = "\033[1m"
	ColorDim  = "\033[2m"
	ColorCyan  = "\033[36m"
	ColorBlue  = "\033[34m"
	ColorGreen = "\033[32m"
	ColorRed  = "\033[31m"
	ColorGold = "\033[33m"
)

// Agent definitions
var Agents = map[string]Agent{
	"sisyphus":      {Name: "Sisyphus", Level: 5, Role: "orchestrator", Model: "minimax-m2.5-free"},
	"hephaestus":   {Name: "Hephaestus", Level: 3, Role: "implementation", Model: "minimax-m2.5-free"},
	"oracle":      {Name: "Oracle", Level: 5, Role: "architecture", Model: "minimax-m2.5-free"},
	"explore":     {Name: "Explore", Level: 2, Role: "research", Model: "minimax-m2.5-free"},
	"librarian":   {Name: "Librarian", Level: 2, Role: "research", Model: "minimax-m2.5-free"},
	"atlas":       {Name: "Atlas", Level: 4, Role: "executor", Model: "minimax-m2.5-free"},
	"sisyphus-junior": {Name: "Sisyphus-Junior", Level: 1, Role: "trivial", Model: "minimax-m2.5-free"},
}

// Agent represents an agent configuration
type Agent struct {
	Name        string `json:"name"`
	Level       int    `json:"level"`
	Role        string `json:"role"`
	Model       string `json:"model"`
	Description string `json:"description,omitempty"`
}

// RouteDecision represents the routing decision
type RouteDecision struct {
	Agent         string  `json:"agent"`
	Level        int     `json:"level"`
	Confidence   float64 `json:"confidence"`
	Strategy     string  `json:"strategy_used"`
	Reason       string  `json:"reason"`
	LatencyMs    float64 `json:"latency_ms"`
	TaskDesc     string  `json:"task_description"`
	CategoryHint string  `json:"category_hint,omitempty"`
	Subtasks     []string `json:"subtasks,omitempty"`
	Prompt       string  `json:"prompt,omitempty"`
	Context      string  `json:"context,omitempty"`
}

// Flags
var (
	flagAgent    = flag.String("agent", "", "Force specific agent")
	flagMode    = flag.String("mode", "", "Execution mode: fast, visual, deep, writing")
	flagInteractive = flag.Bool("interactive", false, "Start interactive mode")
	flagContext  = flag.String("context", "", "Additional context to inject")
	flagJSON    = flag.Bool("json", false, "Output as JSON")
	flagVerbose = flag.Bool("verbose", false, "Verbose output")
	flagVersion = flag.Bool("version", false, "Print version")
	flagHelp    = flag.Bool("help", false, "Print help")
)

// Keyword patterns for routing
var KeywordPatterns = map[string][]string{
	"quick":           {"fix", "typo", "update", "change", "simple", "easy"},
	"visual-engineering": {"design", "UI", "css", "layout", "style", "visual", "frontend", "react"},
	"deep":            {"architecture", "complex", "system", "analyze", "understand"},
	"writing":         {"write", "document", "readme", "docs", "prose"},
	"ultrabrain":      {"algorithm", "logic", "hard", "difficult", "debug"},
}

// Simple routing function (replicates Python logic)
func routeTask(taskDesc string, categoryHint string) RouteDecision {
	start := time.Now()
	
	// Convert to lowercase for matching
	taskLower := strings.ToLower(taskDesc)
	
	// Determine level from keywords
	level := 2
	if containsAny(taskLower, "fix", "typo", "update") {
		level = 1
	} else if containsAny(taskLower, "implement", "create", "build", "add") {
		level = 3
	} else if containsAny(taskLower, "architecture", "system design", "complex") {
		level = 5
	}
	
	// Determine agent from level
	agent := "hephaestus"
	switch level {
	case 1:
		agent = "sisyphus-junior"
	case 2:
		agent = "explore"
	case 3:
		agent = "hephaestus"
	case 4:
		agent = "atlas"
	case 5:
		agent = "sisyphus"
	}
	
	// Override with mode if provided
	if *flagMode != "" {
		switch *flagMode {
		case "fast":
			agent = "sisyphus-junior"
			level = 1
		case "visual":
			agent = "hephaestus" // Will route to visual-engineering
		case "deep":
			agent = "oracle"
			level = 5
		case "writing":
			agent = "librarian"
		}
	}
	
	// Override with explicit agent if provided
	if *flagAgent != "" {
		agent = *flagAgent
	}
	
	// Override with category hint if provided
	if categoryHint != "" {
		if hints, ok := Agents[categoryHint]; ok {
			agent = categoryHint
			level = hints.Level
		}
	}
	
	latencyMs := float64(time.Since(start).Milliseconds() * 1000)
	
	return RouteDecision{
		Agent:       agent,
		Level:      level,
		Confidence:  0.85,
		Strategy:   "keyword",
		Reason:     fmt.Sprintf("Matched level %d from keyword analysis", level),
		LatencyMs:  latencyMs,
		TaskDesc:   taskDesc,
	}
}

// Helper: check if string contains any of the keywords
func containsAny(s string, keywords ...string) bool {
	for _, kw := range keywords {
		if strings.Contains(s, kw) {
			return true
		}
	}
	return false
}

// Print routing decision
func printResult(result RouteDecision, jsonOutput, verbose bool) {
	if jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.Encode(result)
		return
	}
	
	fmt.Printf("\n%s🤖 Agent:%s %s\n", ColorCyan, ColorReset, result.Agent)
	fmt.Printf("%s📊 Level:%s %d/5\n", ColorCyan, ColorReset, result.Level)
	fmt.Printf("%s🎯 Confidence:%s %.0f%%\n", ColorCyan, ColorReset, result.Confidence*100)
	fmt.Printf("%s⚡ Strategy:%s %s\n", ColorCyan, ColorReset, result.Strategy)
	fmt.Printf("%s💡 Reason:%s %s\n", ColorCyan, ColorReset, result.Reason)
	
	if verbose {
		fmt.Printf("\n%slatency: %.2fms%s\n", ColorGold, ColorReset, result.LatencyMs)
	}
}

// Interactive REPL mode
func interactiveMode() {
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("N-Xyme MIND - Interactive Mode")
	fmt.Println("Type 'exit' or 'quit' to exit")
	fmt.Println(strings.Repeat("=", 60))
	
	scanner := bufio.NewScanner(os.Stdin)
	for {
		fmt.Print("\n🎯 > ")
		if !scanner.Scan() {
			break
		}
		
		task := scanner.Text()
		task = strings.TrimSpace(task)
		
		if strings.ToLower(task) == "exit" || strings.ToLower(task) == "quit" || task == "q" {
			fmt.Println("👋 Goodbye!")
			break
		}
		
		if task == "" {
			continue
		}
		
		result := routeTask(task, "")
		printResult(result, false, true)
	}
}

// Execute task by invoking the Python routing system
func executeWithBackend(taskDesc string) RouteDecision {
	// Try to use Python backend if available
	pythonCmd := exec.Command("python3", "-c", fmt.Sprintf(`
import sys
sys.path.insert(0, '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND')
from packages.nx_mcp.nx_delegate import nx_delegate
result = nx_delegate(%q)
print(result)
`, taskDesc))
	
	output, err := pythonCmd.Output()
	if err == nil {
		// Parse JSON output from Python
		var result RouteDecision
		if json.Unmarshal(output, &result) == nil {
			return result
		}
	}
	
	// Fallback to simple routing
	return routeTask(taskDesc, "")
}

var (
	mu       sync.Mutex
	initOnce sync.Once
)

func main() {
	flag.Parse()
	
	// Handle flags
	if *flagVersion {
		fmt.Printf("nx-mind v%s\n", Version)
		return
	}
	
	if *flagHelp || flag.NArg() == 0 && !*flagInteractive {
		fmt.Printf("N-Xyme MIND v%s\n\n", Version)
		fmt.Println("Usage: nx-mind [options] \"task description\"")
		fmt.Println("")
		flag.PrintDefaults()
		fmt.Println("")
		fmt.Println("Examples:")
		fmt.Println("  nx-mind \"implement JWT authentication\"")
		fmt.Println("  nx-mind --agent=hephaestus \"fix the bug\"")
		fmt.Println("  nx-mind --mode=visual \"design sidebar\"")
		fmt.Println("  nx-mind --interactive")
		return
	}
	
	// Interactive mode
	if *flagInteractive {
		interactiveMode()
		return
	}
	
	// Get task from arguments
	taskDesc := strings.Join(flag.Args(), " ")
	
	if taskDesc == "" {
		fmt.Fprintf(os.Stderr, "Error: Task required\n")
		os.Exit(1)
	}
	
	// Execute
	result := executeWithBackend(taskDesc)
	
	// Print result
	printResult(result, *flagJSON, *flagVerbose)
	
	// Show next step hint
	if !*flagJSON {
		fmt.Printf("\n💡 Next: Execute with %s agent\n", result.Agent)
	}
}