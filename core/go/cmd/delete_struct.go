package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"go/token"
	"os"
)

var deleteStructName string

func deleteStruct() error {
	fs := flag.NewFlagSet("delete-struct", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&deleteStructName, "name", "", "Struct name (required)")
	fs.StringVar(&deleteStructName, "n", "", "Struct name (required)")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if deleteStructName == "" {
		return fmt.Errorf("struct name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	var newDecls []ast.Decl
	found := false

	for _, decl := range file.Decls {
		if gen, ok := decl.(*ast.GenDecl); ok && gen.Tok == token.TYPE {
			var newSpecs []ast.Spec
			for _, spec := range gen.Specs {
				if typeSpec, ok := spec.(*ast.TypeSpec); ok {
					if typeSpec.Name.Name == deleteStructName {
						found = true
						continue
					}
				}
				newSpecs = append(newSpecs, spec)
			}
			if len(newSpecs) > 0 {
				gen.Specs = newSpecs
				newDecls = append(newDecls, gen)
			}
		} else {
			newDecls = append(newDecls, decl)
		}
	}

	if !found {
		printJSON(Response{
			Success: false,
			Error:   fmt.Sprintf("struct '%s' not found", deleteStructName),
		})
		return nil
	}

	file.Decls = newDecls

	err = writeFile(fset, modulePath, file)
	checkError(err)

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "delete_struct",
			"name":      deleteStructName,
		},
	})
	return nil
}