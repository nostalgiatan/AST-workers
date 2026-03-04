package cmd

import (
	"bytes"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"strings"
)

var (
	insertFuncName      string
	insertFuncParams    string
	insertFuncReturn    string
	insertFuncBody      string
	insertFuncReceiver  string
	insertFuncDocstring string
)

func insertFunction() error {
	fs := flag.NewFlagSet("insert-function", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&insertFuncName, "name", "", "Function name (required)")
	fs.StringVar(&insertFuncName, "n", "", "Function name (required)")
	fs.StringVar(&insertFuncParams, "params", "", "Function parameters")
	fs.StringVar(&insertFuncParams, "p", "", "Function parameters")
	fs.StringVar(&insertFuncReturn, "return-type", "", "Return type")
	fs.StringVar(&insertFuncReturn, "r", "", "Return type")
	fs.StringVar(&insertFuncBody, "body", "", "Function body")
	fs.StringVar(&insertFuncBody, "b", "", "Function body")
	fs.StringVar(&insertFuncReceiver, "receiver", "", "Method receiver (e.g., 'u *User')")
	fs.StringVar(&insertFuncDocstring, "docstring", "", "Function documentation")
	fs.StringVar(&insertFuncDocstring, "doc", "", "Function documentation")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if insertFuncName == "" {
		return fmt.Errorf("function name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	// Parse the function body
	body := insertFuncBody
	if body == "" {
		body = "// TODO: implement"
	}

	// Build function declaration
	funcDecl := buildFunctionDecl(insertFuncName, insertFuncReceiver, insertFuncParams, insertFuncReturn, body, insertFuncDocstring)

	// Add to file
	file.Decls = append(file.Decls, funcDecl)

	// Format and write back
	err = writeFile(fset, modulePath, file)
	checkError(err)

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "insert_function",
			"name":      insertFuncName,
			"line":      fset.Position(funcDecl.Pos()).Line,
		},
	})
	return nil
}

func buildFunctionDecl(name, receiver, params, results, body, docstring string) *ast.FuncDecl {
	// Parse parameters
	var paramList *ast.FieldList
	if params != "" {
		paramList = parseFieldList(params)
	} else {
		paramList = &ast.FieldList{List: []*ast.Field{}}
	}

	// Parse results
	var resultList *ast.FieldList
	if results != "" {
		resultList = parseFieldList(results)
	}

	// Parse receiver
	var recvList *ast.FieldList
	if receiver != "" {
		recvList = parseFieldList(receiver)
	}

	// Parse body
	var bodyStmts []ast.Stmt
	if body != "" {
		bodyStmts = parseBody(body)
	}

	funcDecl := &ast.FuncDecl{
		Recv: recvList,
		Name: ast.NewIdent(name),
		Type: &ast.FuncType{
			Params:  paramList,
			Results: resultList,
		},
		Body: &ast.BlockStmt{
			List: bodyStmts,
		},
	}

	// Add docstring
	if docstring != "" {
		funcDecl.Doc = &ast.CommentGroup{
			List: []*ast.Comment{
				{Text: "// " + docstring},
			},
		}
	}

	return funcDecl
}

func parseFieldList(s string) *ast.FieldList {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "(") && strings.HasSuffix(s, ")") {
		s = s[1 : len(s)-1]
	}

	if s == "" {
		return &ast.FieldList{List: []*ast.Field{}}
	}

	var fields []*ast.Field
	parts := splitFields(s)

	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		tokens := strings.Fields(part)
		if len(tokens) >= 2 {
			name := tokens[0]
			typ := strings.Join(tokens[1:], " ")
			fields = append(fields, &ast.Field{
				Names: []*ast.Ident{ast.NewIdent(name)},
				Type:  parseType(typ),
			})
		} else if len(tokens) == 1 {
			fields = append(fields, &ast.Field{
				Type: parseType(tokens[0]),
			})
		}
	}

	return &ast.FieldList{List: fields}
}

func splitFields(s string) []string {
	var result []string
	var current strings.Builder
	depth := 0

	for _, ch := range s {
		switch ch {
		case '(', '[', '{':
			depth++
			current.WriteRune(ch)
		case ')', ']', '}':
			depth--
			current.WriteRune(ch)
		case ',':
			if depth == 0 {
				result = append(result, current.String())
				current.Reset()
			} else {
				current.WriteRune(ch)
			}
		default:
			current.WriteRune(ch)
		}
	}

	if current.Len() > 0 {
		result = append(result, current.String())
	}

	return result
}

func parseType(s string) ast.Expr {
	s = strings.TrimSpace(s)

	if strings.HasPrefix(s, "*") {
		return &ast.StarExpr{
			X: parseType(s[1:]),
		}
	}

	if strings.HasPrefix(s, "[]") {
		return &ast.ArrayType{
			Elt: parseType(s[2:]),
		}
	}

	if strings.HasPrefix(s, "map[") {
		depth := 1
		i := 4
		for i < len(s) && depth > 0 {
			if s[i] == '[' {
				depth++
			} else if s[i] == ']' {
				depth--
			}
			i++
		}
		keyType := s[4 : i-1]
		valueType := s[i:]
		return &ast.MapType{
			Key:   parseType(keyType),
			Value: parseType(valueType),
		}
	}

	return ast.NewIdent(s)
}

func parseBody(body string) []ast.Stmt {
	src := fmt.Sprintf("package temp\nfunc _() {\n%s\n}", body)

	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, "", src, 0)
	if err != nil {
		return []ast.Stmt{
			&ast.ExprStmt{
				X: ast.NewIdent(body),
			},
		}
	}

	for _, decl := range f.Decls {
		if fn, ok := decl.(*ast.FuncDecl); ok {
			return fn.Body.List
		}
	}

	return nil
}

func writeFile(fset *token.FileSet, filename string, file *ast.File) error {
	var buf bytes.Buffer
	if err := format.Node(&buf, fset, file); err != nil {
		return err
	}
	return os.WriteFile(filename, buf.Bytes(), 0644)
}