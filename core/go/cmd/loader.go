package cmd

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
)

// LoadFile loads a Go file and returns the FileSet and File
func LoadFile(module string) (*token.FileSet, *ast.File, error) {
	absPath, err := filepath.Abs(module)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get absolute path: %w", err)
	}

	// Check if file exists
	content, err := os.ReadFile(absPath)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to read file: %w", err)
	}

	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, absPath, content, parser.ParseComments|parser.DeclarationErrors)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to parse file: %w", err)
	}

	return fset, file, nil
}

// ParseFile parses a Go file and returns the AST
func ParseFile(module string) (*token.FileSet, *ast.File, error) {
	return LoadFile(module)
}

// ParseMethodReceiver parses "Receiver.Method" format
func ParseMethodReceiver(name string) (receiver, method string) {
	parts := strings.SplitN(name, ".", 2)
	if len(parts) == 2 {
		return parts[0], parts[1]
	}
	return "", name
}
