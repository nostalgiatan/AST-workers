package cmd

import (
	"bytes"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"os"
	"strings"
)

var showSymbolName string

func showSymbol() error {
	fs := flag.NewFlagSet("show", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.StringVar(&showSymbolName, "name", "", "Symbol name (required)")
	fs.StringVar(&showSymbolName, "n", "", "Symbol name (required)")
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}
	if showSymbolName == "" {
		return fmt.Errorf("symbol name is required (-n or --name)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	// Parse "Receiver.Method" format
	receiver, method := ParseMethodReceiver(showSymbolName)
	targetName := showSymbolName
	if receiver != "" {
		targetName = method
	}

	var found ast.Node
	var symbolType string

	// Search for function
	for _, decl := range file.Decls {
		switch d := decl.(type) {
		case *ast.FuncDecl:
			if d.Name.Name == targetName {
				if receiver != "" {
					if d.Recv != nil && len(d.Recv.List) > 0 {
						recvType := getReceiverType(d.Recv.List[0])
						if recvType == receiver || recvType == "*"+receiver {
							found = d
							symbolType = "method"
							break
						}
					}
				} else if d.Recv == nil {
					found = d
					symbolType = "function"
					break
				}
			}
		case *ast.GenDecl:
			for _, spec := range d.Specs {
				if typeSpec, ok := spec.(*ast.TypeSpec); ok {
					if typeSpec.Name.Name == targetName {
						found = typeSpec
						if _, isStruct := typeSpec.Type.(*ast.StructType); isStruct {
							symbolType = "struct"
						} else {
							symbolType = "type"
						}
						break
					}
				}
			}
		}
		if found != nil {
			break
		}
	}

	if found == nil {
		printJSON(Response{
			Success: false,
			Error:   fmt.Sprintf("symbol '%s' not found", showSymbolName),
		})
		return nil
	}

	// Get code
	var buf bytes.Buffer
	if err := format.Node(&buf, fset, found); err != nil {
		printJSON(Response{
			Success: false,
			Error:   err.Error(),
		})
		return nil
	}

	info := SymbolInfo{
		Name:    targetName,
		Type:    symbolType,
		Line:    fset.Position(found.Pos()).Line,
		EndLine: fset.Position(found.End()).Line,
		Code:    strings.TrimSpace(buf.String()),
	}

	printJSON(Response{
		Success: true,
		Result:  info,
	})
	return nil
}
