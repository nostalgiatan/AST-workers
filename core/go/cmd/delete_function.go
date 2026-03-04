package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"os"
)

var deleteFuncName string

func deleteFunction() error {
	fs := flag.NewFlagSet("delete-function", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&deleteFuncName, "name", "", "Function name (required)")
	fs.StringVar(&deleteFuncName, "n", "", "Function name (required)")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if deleteFuncName == "" {
		return fmt.Errorf("function name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	receiver, method := ParseMethodReceiver(deleteFuncName)
	targetName := deleteFuncName
	if receiver != "" {
		targetName = method
	}

	var newDecls []ast.Decl
	found := false

	for _, decl := range file.Decls {
		if fn, ok := decl.(*ast.FuncDecl); ok {
			if fn.Name.Name == targetName {
				if receiver != "" {
					if fn.Recv != nil && len(fn.Recv.List) > 0 {
						recvType := getReceiverType(fn.Recv.List[0])
						if recvType == receiver || recvType == "*"+receiver {
							found = true
							continue
						}
					}
				} else if fn.Recv == nil {
					found = true
					continue
				}
			}
		}
		newDecls = append(newDecls, decl)
	}

	if !found {
		printJSON(Response{
			Success: false,
			Error:   fmt.Sprintf("function '%s' not found", deleteFuncName),
		})
		return nil
	}

	file.Decls = newDecls

	err = writeFile(fset, modulePath, file)
	checkError(err)

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "delete_function",
			"name":      deleteFuncName,
		},
	})
	return nil
}