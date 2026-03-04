package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"os"
	"strings"
)

func listStructs() error {
	fs := flag.NewFlagSet("list-structs", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

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

						// Get docstring
						if gen.Doc != nil {
							info.Docstring = strings.TrimSpace(gen.Doc.Text())
						}

						// Get fields
						if structType.Fields != nil {
							for _, field := range structType.Fields.List {
								fieldInfo := FieldInfo{
									Type:     exprToString(field.Type),
									Exported: true,
								}
								if len(field.Names) > 0 {
									fieldInfo.Name = field.Names[0].Name
									fieldInfo.Exported = ast.IsExported(field.Names[0].Name)
								}
								if field.Tag != nil {
									fieldInfo.Tag = field.Tag.Value
								}
								info.Fields = append(info.Fields, fieldInfo)
							}
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
