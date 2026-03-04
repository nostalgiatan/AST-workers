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

// ExprToString converts an AST expression to its string representation
func ExprToString(expr ast.Expr) string {
	switch t := expr.(type) {
	case *ast.Ident:
		return t.Name
	case *ast.StarExpr:
		return "*" + ExprToString(t.X)
	case *ast.ArrayType:
		return "[]" + ExprToString(t.Elt)
	case *ast.MapType:
		return "map[" + ExprToString(t.Key) + "]" + ExprToString(t.Value)
	case *ast.SelectorExpr:
		return ExprToString(t.X) + "." + t.Sel.Name
	case *ast.InterfaceType:
		return "interface{}"
	case *ast.FuncType:
		return "func(...)"
	case *ast.ChanType:
		return "chan " + ExprToString(t.Value)
	case *ast.Ellipsis:
		return "..." + ExprToString(t.Elt)
	case *ast.ParenExpr:
		return "(" + ExprToString(t.X) + ")"
	case *ast.UnaryExpr:
		return t.Op.String() + ExprToString(t.X)
	case *ast.BinaryExpr:
		return ExprToString(t.X) + " " + t.Op.String() + " " + ExprToString(t.Y)
	default:
		return "unknown"
	}
}

// exprToString is an alias for ExprToString (for backward compatibility)
func exprToString(expr ast.Expr) string {
	return ExprToString(expr)
}
