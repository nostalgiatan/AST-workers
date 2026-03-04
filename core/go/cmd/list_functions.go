package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"os"
	"strings"
)

var (
	listFunctionsClass         string
	listFunctionsIncludePrivate bool
)

func listFunctions() error {
	fs := flag.NewFlagSet("list-functions", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&listFunctionsClass, "class", "", "Filter by receiver type (e.g., 'User')")
	fs.StringVar(&listFunctionsClass, "c", "", "Filter by receiver type")
	fs.BoolVar(&listFunctionsIncludePrivate, "include-private", false, "Include private functions (lowercase)")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	var functions []FunctionInfo

	for _, decl := range file.Decls {
		if fn, ok := decl.(*ast.FuncDecl); ok {
			info := FunctionInfo{
				Name:     fn.Name.Name,
				Line:     fset.Position(fn.Pos()).Line,
				EndLine:  fset.Position(fn.End()).Line,
				Exported: ast.IsExported(fn.Name.Name),
			}

			// Skip private functions if not included
			if !info.Exported && !listFunctionsIncludePrivate {
				continue
			}

			// Check if it's a method
			if fn.Recv != nil && len(fn.Recv.List) > 0 {
				info.IsMethod = true
				info.Receiver = getReceiverType(fn.Recv.List[0])
				
				// Filter by class if specified
				if listFunctionsClass != "" {
					recvType := info.Receiver
					if recvType != listFunctionsClass && recvType != "*"+listFunctionsClass {
						continue
					}
				}
			} else if listFunctionsClass != "" {
				// If filtering by class, skip non-methods
				continue
			}

			// Get params
			if fn.Type.Params != nil {
				for i, field := range fn.Type.Params.List {
					for _, name := range field.Names {
						info.Params = append(info.Params, Param{
							Name: name.Name,
							Type: exprToString(field.Type),
						})
					}
					if len(field.Names) == 0 {
						info.Params = append(info.Params, Param{
							Name: fmt.Sprintf("_%d", i),
							Type: exprToString(field.Type),
						})
					}
				}
			}

			// Get results
			if fn.Type.Results != nil {
				for i, field := range fn.Type.Results.List {
					for _, name := range field.Names {
						info.Results = append(info.Results, Param{
							Name: name.Name,
							Type: exprToString(field.Type),
						})
					}
					if len(field.Names) == 0 {
						info.Results = append(info.Results, Param{
							Name: fmt.Sprintf("_%d", i),
							Type: exprToString(field.Type),
						})
					}
				}
			}

			// Get docstring
			if fn.Doc != nil {
				info.Docstring = strings.TrimSpace(strings.TrimPrefix(fn.Doc.Text(), "\n"))
			}

			functions = append(functions, info)
		}
	}

	printJSON(Response{
		Success: true,
		Result:  functions,
	})
	return nil
}

func exprToString(expr ast.Expr) string {
	switch t := expr.(type) {
	case *ast.Ident:
		return t.Name
	case *ast.StarExpr:
		return "*" + exprToString(t.X)
	case *ast.ArrayType:
		return "[]" + exprToString(t.Elt)
	case *ast.MapType:
		return "map[" + exprToString(t.Key) + "]" + exprToString(t.Value)
	case *ast.SelectorExpr:
		return exprToString(t.X) + "." + t.Sel.Name
	case *ast.InterfaceType:
		return "interface{}"
	case *ast.FuncType:
		return "func(...)"
	case *ast.ChanType:
		return "chan " + exprToString(t.Value)
	default:
		return "unknown"
	}
}
