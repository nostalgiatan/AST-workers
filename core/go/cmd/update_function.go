package cmd

import (
	"flag"
	"fmt"
	"go/ast"
	"os"
)

var (
	updateFuncName    string
	updateFuncParams  string
	updateFuncReturn  string
	updateFuncBody    string
)

func updateFunction() error {
	fs := flag.NewFlagSet("update-function", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&updateFuncName, "name", "", "Function name (required)")
	fs.StringVar(&updateFuncName, "n", "", "Function name (required)")
	fs.StringVar(&updateFuncParams, "params", "", "New parameters")
	fs.StringVar(&updateFuncParams, "p", "", "New parameters")
	fs.StringVar(&updateFuncReturn, "return-type", "", "New return type")
	fs.StringVar(&updateFuncReturn, "r", "", "New return type")
	fs.StringVar(&updateFuncBody, "body", "", "New body")
	fs.StringVar(&updateFuncBody, "b", "", "New body")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if updateFuncName == "" {
		return fmt.Errorf("function name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	receiver, method := ParseMethodReceiver(updateFuncName)
	targetName := updateFuncName
	if receiver != "" {
		targetName = method
	}

	var foundFunc *ast.FuncDecl
	for _, decl := range file.Decls {
		if fn, ok := decl.(*ast.FuncDecl); ok {
			if fn.Name.Name == targetName {
				if receiver != "" {
					if fn.Recv != nil && len(fn.Recv.List) > 0 {
						recvType := getReceiverType(fn.Recv.List[0])
						if recvType == receiver || recvType == "*"+receiver {
							foundFunc = fn
							break
						}
					}
				} else if fn.Recv == nil {
					foundFunc = fn
					break
				}
			}
		}
	}

	if foundFunc == nil {
		printJSON(Response{
			Success: false,
			Error:   fmt.Sprintf("function '%s' not found", updateFuncName),
		})
		return nil
	}

	if updateFuncParams != "" {
		foundFunc.Type.Params = parseFieldList(updateFuncParams)
	}
	if updateFuncReturn != "" {
		foundFunc.Type.Results = parseFieldList(updateFuncReturn)
	}
	if updateFuncBody != "" {
		foundFunc.Body.List = parseBody(updateFuncBody)
	}

	err = writeFile(fset, modulePath, file)
	checkError(err)

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"operation": "update_function",
			"name":      updateFuncName,
		},
	})
	return nil
}

func getReceiverType(field *ast.Field) string {
	switch t := field.Type.(type) {
	case *ast.StarExpr:
		if ident, ok := t.X.(*ast.Ident); ok {
			return "*" + ident.Name
		}
	case *ast.Ident:
		return t.Name
	}
	return ""
}
