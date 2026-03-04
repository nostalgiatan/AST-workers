package cmd

import (
	"flag"
	"fmt"
	"os"
)

func validate() error {
	fs := flag.NewFlagSet("validate", flag.ExitOnError)
	parseModuleFlag(fs)
	fs.Parse(os.Args[2:])

	if modulePath == "" {
		return fmt.Errorf("module path is required (-m or --module)")
	}

	_, _, err := ParseFile(modulePath)
	if err != nil {
		printJSON(Response{
			Success: false,
			Error:   err.Error(),
			Result: map[string]interface{}{
				"valid": false,
			},
		})
		return nil
	}

	printJSON(Response{
		Success: true,
		Result: map[string]interface{}{
			"valid":  true,
			"module": modulePath,
		},
	})
	return nil
}
