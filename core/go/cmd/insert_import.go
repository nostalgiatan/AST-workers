package cmd

import (
	"flag"
	"fmt"
	"go/format"
	"os"
	"strings"
)

var (
	insertImportPath  string
	insertImportAlias string
)

func insertImport() error {
	fs := flag.NewFlagSet("insert-import", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&insertImportPath, "path", "", "Import path (required)")
	fs.StringVar(&insertImportPath, "p", "", "Import path (required)")
	fs.StringVar(&insertImportAlias, "alias", "", "Import alias (optional)")
	fs.StringVar(&insertImportAlias, "a", "", "Import alias (optional)")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if insertImportPath == "" {
		return fmt.Errorf("import path is required (-p or --path)")
	}

	// Read file content
	content, err := os.ReadFile(modulePath)
	if err != nil {
		return fmt.Errorf("failed to read file: %w", err)
	}

	src := string(content)

	// Check if import already exists
	quotedPath := fmt.Sprintf(`"%s"`, insertImportPath)
	if strings.Contains(src, quotedPath) {
		printJSON(Response{
			Success: false,
			Error:   fmt.Sprintf("import '%s' already exists", insertImportPath),
		})
		return nil
	}

	// Build import line
	var importLine string
	if insertImportAlias != "" {
		importLine = fmt.Sprintf("%s %s", insertImportAlias, quotedPath)
	} else {
		importLine = quotedPath
	}

	// Find package declaration
	pkgIdx := strings.Index(src, "package ")
	if pkgIdx == -1 {
		return fmt.Errorf("no package declaration found")
	}

	// Find end of package line
	pkgEnd := strings.Index(src[pkgIdx:], "\n")
	if pkgEnd == -1 {
		pkgEnd = len(src) - pkgIdx
	}
	pkgEnd += pkgIdx

	// Check if there's already an import block
	importIdx := strings.Index(src, "import ")
	if importIdx != -1 && importIdx > pkgEnd {
		// There's an existing import declaration
		// Check if it's a block import (with parentheses) or single import
		afterImport := src[importIdx+7:]
		afterImport = strings.TrimLeft(afterImport, " \t")

		if strings.HasPrefix(afterImport, "(") {
			// Block import - add to the block
			// Find the opening parenthesis
			openParen := strings.Index(src[importIdx:], "(")
			if openParen != -1 {
				// Find the closing parenthesis
				closeParen := strings.Index(src[importIdx:], ")")
				if closeParen != -1 && closeParen > openParen {
					// Insert before closing parenthesis
					insertPos := importIdx + closeParen
					newSrc := src[:insertPos] + "\n\t" + importLine + src[insertPos:]

					// Format and write
					formatted, err := formatSource(newSrc)
					if err != nil {
						return err
					}

					if err := os.WriteFile(modulePath, formatted, 0644); err != nil {
						return fmt.Errorf("failed to write file: %w", err)
					}

					printJSON(Response{
						Success: true,
						Result: map[string]interface{}{
							"operation": "insert_import",
							"path":      insertImportPath,
							"alias":     insertImportAlias,
						},
					})
					return nil
				}
			}
		} else {
			// Single import - convert to block
			// Find the end of the single import line
			importLineEnd := strings.Index(src[importIdx:], "\n")
			if importLineEnd != -1 {
				// Get the existing import
				existingImport := strings.TrimSpace(src[importIdx+7 : importIdx+importLineEnd])
				// Replace single import with block
				newImportBlock := fmt.Sprintf("import (\n\t%s\n\t%s\n)", existingImport, importLine)
				newSrc := src[:importIdx] + newImportBlock + src[importIdx+importLineEnd:]

				// Format and write
				formatted, err := formatSource(newSrc)
				if err != nil {
					return err
				}

				if err := os.WriteFile(modulePath, formatted, 0644); err != nil {
					return fmt.Errorf("failed to write file: %w", err)
				}

				printJSON(Response{
					Success: true,
					Result: map[string]interface{}{
						"operation": "insert_import",
						"path":      insertImportPath,
						"alias":     insertImportAlias,
					},
				})
				return nil
			}
		}
	}

	// No existing import - add new import block after package
	importBlock := fmt.Sprintf("\nimport (\n\t%s\n)", importLine)
	newSrc := src[:pkgEnd] + importBlock + src[pkgEnd:]

	// Format and write
	formatted, err := formatSource(newSrc)
	if err != nil {
		return err
	}

	if err := os.WriteFile(modulePath, formatted, 0644); err != nil {
		return fmt.Errorf("failed to write file: %w", err)
	}

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "insert_import",
			"path":      insertImportPath,
			"alias":     insertImportAlias,
		},
	})
	return nil
}

func formatSource(src string) ([]byte, error) {
	formatted, err := format.Source([]byte(src))
	if err != nil {
		return nil, fmt.Errorf("failed to format source: %w", err)
	}
	return formatted, nil
}