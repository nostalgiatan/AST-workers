package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"os"
	"strings"
)

var (
	listFunctionsClass          string
	listFunctionsIncludePrivate bool
	listFunctionsUseTypeInfo    bool
)

func listFunctions() error {
	fs := flag.NewFlagSet("list-functions", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&listFunctionsClass, "class", "", "Filter by receiver type (e.g., 'User')")
	fs.StringVar(&listFunctionsClass, "c", "", "Filter by receiver type")
	fs.BoolVar(&listFunctionsIncludePrivate, "include-private", false, "Include private functions (lowercase)")
	fs.BoolVar(&listFunctionsIncludePrivate, "p", false, "Include private functions")
	fs.BoolVar(&listFunctionsUseTypeInfo, "type-info", true, "Use type checker for detailed type information")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	// Create type checker if requested
	var tc *TypeChecker
	if listFunctionsUseTypeInfo {
		tc = NewTypeChecker(fset, file, modulePath)
	}

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

			// Get parameters and results using type checker or AST
			if tc != nil {
				info.Params, info.Results = tc.GetFunctionType(fn)
			} else {
				info.Params, info.Results = extractParamsFromAST(fn.Type)
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