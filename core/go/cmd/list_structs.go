package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"os"
	"strings"
)

var (
	listStructsIncludePrivate bool
	listStructsUseTypeInfo    bool
	listStructsWithMethods    bool
)

func listStructs() error {
	fs := flag.NewFlagSet("list-structs", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.BoolVar(&listStructsIncludePrivate, "include-private", false, "Include private structs")
	fs.BoolVar(&listStructsIncludePrivate, "p", false, "Include private structs")
	fs.BoolVar(&listStructsUseTypeInfo, "type-info", true, "Use type checker for detailed type information")
	fs.BoolVar(&listStructsWithMethods, "with-methods", false, "Include methods in output")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	// Create type checker if requested
	var tc *TypeChecker
	if listStructsUseTypeInfo {
		tc = NewTypeChecker(fset, file, modulePath)
	}

	var structs []StructInfo

	for _, decl := range file.Decls {
		if gen, ok := decl.(*ast.GenDecl); ok {
			for _, spec := range gen.Specs {
				if typeSpec, ok := spec.(*ast.TypeSpec); ok {
					if structType, ok := typeSpec.Type.(*ast.StructType); ok {
						info := StructInfo{
							Name:     typeSpec.Name.Name,
							Line:     fset.Position(typeSpec.Pos()).Line,
							EndLine:  fset.Position(typeSpec.End()).Line,
							Exported: ast.IsExported(typeSpec.Name.Name),
						}

						// Skip private structs if not included
						if !info.Exported && !listStructsIncludePrivate {
							continue
						}

						// Get docstring
						if gen.Doc != nil {
							info.Docstring = strings.TrimSpace(gen.Doc.Text())
						}

						// Get fields using type checker or AST
						if tc != nil && listStructsUseTypeInfo {
							info.Fields = tc.GetStructFields(typeSpec)
						} else {
							info.Fields = extractFieldsFromAST(structType)
						}

						// Get methods if requested
						if listStructsWithMethods && tc != nil {
							info.Methods = tc.GetStructMethods(info.Name)
						}

						structs = append(structs, info)
					}
				}
			}
		}
	}

	printJSON(Response{
		Success: true,
		Result:  structs,
	})
	return nil
}

func extractFieldsFromAST(structType *ast.StructType) []FieldInfo {
	var fields []FieldInfo

	if structType.Fields == nil {
		return fields
	}

	for _, field := range structType.Fields.List {
		fieldInfo := FieldInfo{
			Type:     exprToString(field.Type),
			Exported: true,
		}

		if len(field.Names) > 0 {
			fieldInfo.Name = field.Names[0].Name
			fieldInfo.Exported = ast.IsExported(field.Names[0].Name)
			fieldInfo.Embedded = false
		} else {
			// Embedded field
			fieldInfo.Name = exprToString(field.Type)
			fieldInfo.Embedded = true
		}

		if field.Tag != nil {
			fieldInfo.Tag = field.Tag.Value
		}

		fields = append(fields, fieldInfo)
	}

	return fields
}