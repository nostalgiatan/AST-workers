package cmd

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
)

// Version information (set via ldflags during build)
var Version = "dev"

// CLI flags
var (
	modulePath string
)

// Execute runs the CLI
func Execute() error {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	// Parse subcommand
	subcommand := os.Args[1]

	// Create a new flagset for each subcommand
	switch subcommand {
	case "list-functions", "lf":
		return listFunctions()
	case "list-imports", "li":
		return listImports()
	case "list-structs", "ls":
		return listStructs()
	case "show":
		return showSymbol()
	case "insert-function", "if":
		return insertFunction()
	case "insert-struct", "is":
		return insertStruct()
	case "insert-import", "ii":
		return insertImport()
	case "update-function", "uf":
		return updateFunction()
	case "delete-function", "df":
		return deleteFunction()
	case "delete-struct", "ds":
		return deleteStruct()
	case "validate":
		return validate()
	case "version", "-v", "--version":
		fmt.Printf("ast-go %s\n", Version)
		return nil
	case "help", "-h", "--help":
		printUsage()
		return nil
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n\n", subcommand)
		printUsage()
		os.Exit(1)
	}
	return nil
}

func printUsage() {
	fmt.Println(`ast-go - Go AST manipulation CLI tool

Usage:
  ast-go <command> [options]

Commands:
  list-functions, lf    List all functions in a module
  list-imports, li      List all imports in a module
  list-structs, ls      List all structs in a module
  show                  Show a symbol with context
  insert-function, if   Insert a function
  insert-struct, is     Insert a struct
  insert-import, ii     Insert an import
  update-function, uf   Update a function
  delete-function, df   Delete a function
  delete-struct, ds     Delete a struct
  validate              Validate syntax
  version               Show version

Options:
  -m, --module string   Path to Go source file (required)
  -n, --name string     Symbol name
  -h, --help            Show this help message
  -v, --version         Show version`)
}

func parseModuleFlag(fs *flag.FlagSet) {
	fs.StringVar(&modulePath, "module", "", "Path to Go source file (required)")
	fs.StringVar(&modulePath, "m", "", "Path to Go source file (required)")
}

func checkError(err error) {
	if err != nil {
		printError(err)
		os.Exit(1)
	}
}

func printError(err error) {
	fmt.Fprintf(os.Stderr, "Error: %s\n", err.Error())
}

func printJSON(v interface{}) {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling JSON: %s\n", err)
		return
	}
	fmt.Println(string(b))
}
