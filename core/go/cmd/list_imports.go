package cmd

import (
	"flag"
	"fmt"
	"os"
)

func listImports() error {
	fs := flag.NewFlagSet("list-imports", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}

	fset, file, err := ParseFile(modulePath)
	checkError(err)

	var imports []ImportInfo

	for _, imp := range file.Imports {
		info := ImportInfo{
			Path: imp.Path.Value,
			Line: fset.Position(imp.Pos()).Line,
		}
		if imp.Name != nil {
			info.Alias = imp.Name.Name
		}
		imports = append(imports, info)
	}

	printJSON(Response{
		Success: true,
		Result:  imports,
	})
	return nil
}
