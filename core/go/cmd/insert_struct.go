package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"go/token"
	"os"
	"strings"
)

var (
	insertStructName      string
	insertStructFields    string
	insertStructDocstring string
)

func insertStruct() error {
	fs := flag.NewFlagSet("insert-struct", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&insertStructName, "name", "", "Struct name (required)")
	fs.StringVar(&insertStructName, "n", "", "Struct name (required)")
	fs.StringVar(&insertStructFields, "fields", "", "Struct fields")
	fs.StringVar(&insertStructFields, "f", "", "Struct fields")
	fs.StringVar(&insertStructDocstring, "docstring", "", "Struct documentation")
	fs.StringVar(&insertStructDocstring, "doc", "", "Struct documentation")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if insertStructName == "" {
		return fmt.Errorf("struct name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	// Build struct declaration
	structDecl := buildStructDecl(insertStructName, insertStructFields, insertStructDocstring)

	// Add to file
	file.Decls = append(file.Decls, structDecl)

	// Format and write back
	err = writeFile(fset, modulePath, file)
	checkError(err)

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "insert_struct",
			"name":      insertStructName,
			"line":      fset.Position(structDecl.Pos()).Line,
		},
	})
	return nil
}

func buildStructDecl(name, fields, docstring string) *ast.GenDecl {
	var fieldList []*ast.Field
	if fields != "" {
		fieldList = parseStructFields(fields)
	}

	typeSpec := &ast.TypeSpec{
		Name: ast.NewIdent(name),
		Type: &ast.StructType{
			Fields: &ast.FieldList{List: fieldList},
		},
	}

	decl := &ast.GenDecl{
		Tok:   token.TYPE,
		Specs: []ast.Spec{typeSpec},
	}

	if docstring != "" {
		decl.Doc = &ast.CommentGroup{
			List: []*ast.Comment{
				{Text: "// " + docstring},
			},
		}
	}

	return decl
}

func parseStructFields(s string) []*ast.Field {
	var fields []*ast.Field
	parts := splitFields(s)

	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		var name, typ, tag string

		// Check for tag
		if idx := strings.Index(part, "`"); idx >= 0 {
			tag = part[idx:]
			part = strings.TrimSpace(part[:idx])
		}

		tokens := strings.Fields(part)
		if len(tokens) >= 2 {
			name = tokens[0]
			typ = strings.Join(tokens[1:], " ")
		} else if len(tokens) == 1 {
			typ = tokens[0]
		}

		field := &ast.Field{
			Type: parseType(typ),
		}

		if name != "" {
			field.Names = []*ast.Ident{ast.NewIdent(name)}
		}

		if tag != "" {
			field.Tag = &ast.BasicLit{
				Kind:  token.STRING,
				Value: tag,
			}
		}

		fields = append(fields, field)
	}

	return fields
}