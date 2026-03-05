package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/token"
	"os"
	"strings"
)

var (
	updateStructFieldName    string
	updateStructFieldStruct  string
	updateStructFieldNewType string
	updateStructFieldNewTag  string
	updateStructFieldNewName string
)

func updateStructField() error {
	fs := flag.NewFlagSet("update-struct-field", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&updateStructFieldStruct, "struct", "", "Struct name (required)")
	fs.StringVar(&updateStructFieldStruct, "s", "", "Struct name")
	fs.StringVar(&updateStructFieldName, "name", "", "Field name to update (required)")
	fs.StringVar(&updateStructFieldName, "n", "", "Field name")
	fs.StringVar(&updateStructFieldNewType, "type", "", "New field type")
	fs.StringVar(&updateStructFieldNewType, "t", "", "New field type")
	fs.StringVar(&updateStructFieldNewTag, "tag", "", "New field tag (e.g., 'json:\"name\"')")
	fs.StringVar(&updateStructFieldNewName, "new-name", "", "New field name (for renaming)")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if updateStructFieldStruct == "" {
		return fmt.Errorf("struct name is required (-s or --struct)")
	}
	if updateStructFieldName == "" {
		return fmt.Errorf("field name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	// Find and update the struct field
	found := false
	for _, decl := range file.Decls {
		if gen, ok := decl.(*ast.GenDecl); ok {
			for _, spec := range gen.Specs {
				if typeSpec, ok := spec.(*ast.TypeSpec); ok {
					if typeSpec.Name.Name == updateStructFieldStruct {
						structType, ok := typeSpec.Type.(*ast.StructType)
						if !ok {
							return fmt.Errorf("'%s' is not a struct", updateStructFieldStruct)
						}

						for _, field := range structType.Fields.List {
							for i, name := range field.Names {
								if name.Name == updateStructFieldName {
									found = true

									// Update field name
									if updateStructFieldNewName != "" {
										field.Names[i].Name = updateStructFieldNewName
									}

									// Update field type
									if updateStructFieldNewType != "" {
										field.Type = parseTypeExpr(updateStructFieldNewType)
									}

									// Update field tag
									if updateStructFieldNewTag != "" {
										field.Tag = &ast.BasicLit{
											Kind:  token.STRING,
											Value: fmt.Sprintf("`%s`", updateStructFieldNewTag),
										}
									}
								}
							}
						}
					}
				}
			}
		}
	}

	if !found {
		return fmt.Errorf("field '%s' not found in struct '%s'", updateStructFieldName, updateStructFieldStruct)
	}

	// Format and write
	var buf strings.Builder
	err = format.Node(&buf, fset, file)
	checkError(err)

	err = os.WriteFile(modulePath, []byte(buf.String()), 0644)
	checkError(err)

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "update_struct_field",
			"struct":    updateStructFieldStruct,
			"field":     updateStructFieldName,
			"modified":  true,
		},
	})
	return nil
}

func parseTypeExpr(typeStr string) ast.Expr {
	// Handle pointer types
	if strings.HasPrefix(typeStr, "*") {
		return &ast.StarExpr{
			X: parseTypeExpr(typeStr[1:]),
		}
	}

	// Handle slice types
	if strings.HasPrefix(typeStr, "[]") {
		return &ast.ArrayType{
			Elt: parseTypeExpr(typeStr[2:]),
		}
	}

	// Handle map types
	if strings.HasPrefix(typeStr, "map[") {
		// Find the closing bracket for key
		depth := 1
		i := 4
		for ; i < len(typeStr); i++ {
			if typeStr[i] == '[' {
				depth++
			} else if typeStr[i] == ']' {
				depth--
				if depth == 0 {
					break
				}
			}
		}
		keyType := typeStr[4:i]
		valueType := typeStr[i+1:]
		return &ast.MapType{
			Key:   parseTypeExpr(keyType),
			Value: parseTypeExpr(valueType),
		}
	}

	// Handle qualified identifiers (e.g., "pkg.Type")
	if strings.Contains(typeStr, ".") {
		parts := strings.SplitN(typeStr, ".", 2)
		return &ast.SelectorExpr{
			X:   ast.NewIdent(parts[0]),
			Sel: ast.NewIdent(parts[1]),
		}
	}

	// Simple identifier
	return ast.NewIdent(typeStr)
}