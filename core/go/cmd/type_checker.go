package cmd

import (
	"fmt"
	"go/ast"
	"go/importer"
	"go/token"
	"go/types"
	"path/filepath"
	"strings"
)

// TypeChecker provides type information for Go source files
type TypeChecker struct {
	fset   *token.FileSet
	file   *ast.File
	info   *types.Info
	pkg    *types.Package
	errors []types.Error
}

// NewTypeChecker creates a new TypeChecker for the given file
func NewTypeChecker(fset *token.FileSet, file *ast.File, filename string) *TypeChecker {
	tc := &TypeChecker{
		fset: fset,
		file: file,
		info: &types.Info{
			Types:      make(map[ast.Expr]types.TypeAndValue),
			Defs:       make(map[*ast.Ident]types.Object),
			Uses:       make(map[*ast.Ident]types.Object),
			Selections: make(map[*ast.SelectorExpr]*types.Selection),
			Scopes:     make(map[ast.Node]*types.Scope),
		},
	}

	// Get package name from file
	pkgName := "main"
	if file.Name != nil {
		pkgName = file.Name.Name
	}

	// Create type checker configuration
	conf := types.Config{
		Importer: importer.ForCompiler(fset, "source", nil),
		Error: func(err error) {
			if typeErr, ok := err.(types.Error); ok {
				tc.errors = append(tc.errors, typeErr)
			}
		},
	}

	// Perform type checking
	// Note: We use an empty file list for dependencies
	// This means we can only get partial type info for external packages
	pkg, _ := conf.Check(pkgName, fset, []*ast.File{file}, tc.info)
	tc.pkg = pkg

	return tc
}

// GetType returns the type string for an expression
func (tc *TypeChecker) GetType(expr ast.Expr) string {
	if tc.info == nil {
		return exprToString(expr)
	}

	tv, ok := tc.info.Types[expr]
	if !ok {
		return exprToString(expr)
	}

	return tc.typeToString(tv.Type)
}

// typeToString converts a types.Type to string representation
func (tc *TypeChecker) typeToString(t types.Type) string {
	if t == nil {
		return "unknown"
	}

	switch typ := t.(type) {
	case *types.Basic:
		return typ.Name()

	case *types.Pointer:
		return "*" + tc.typeToString(typ.Elem())

	case *types.Slice:
		return "[]" + tc.typeToString(typ.Elem())

	case *types.Array:
		return fmt.Sprintf("[%d]%s", typ.Len(), tc.typeToString(typ.Elem()))

	case *types.Map:
		return "map[" + tc.typeToString(typ.Key()) + "]" + tc.typeToString(typ.Elem())

	case *types.Chan:
		var dir string
		switch typ.Dir() {
		case types.SendOnly:
			dir = "chan<- "
		case types.RecvOnly:
			dir = "<-chan "
		default:
			dir = "chan "
		}
		return dir + tc.typeToString(typ.Elem())

	case *types.Signature:
		return tc.signatureToString(typ)

	case *types.Interface:
		if typ.Empty() {
			return "interface{}"
		}
		return "interface{...}"

	case *types.Struct:
		return "struct{...}"

	case *types.Named:
		return tc.namedTypeToString(typ)

	case *types.TypeParam:
		return typ.Obj().Name()

	default:
		return t.String()
	}
}

// signatureToString converts a function signature to string
func (tc *TypeChecker) signatureToString(sig *types.Signature) string {
	var b strings.Builder
	b.WriteString("func(")

	// Type parameters (generics)
	if tparams := sig.TypeParams(); tparams.Len() > 0 {
		b.WriteString("[")
		for i := 0; i < tparams.Len(); i++ {
			if i > 0 {
				b.WriteString(", ")
			}
			b.WriteString(tparams.At(i).Obj().Name())
		}
		b.WriteString("](")
	}

	// Parameters
	params := sig.Params()
	for i := 0; i < params.Len(); i++ {
		if i > 0 {
			b.WriteString(", ")
		}
		param := params.At(i)
		if param.Name() != "" && !isBlankIdentifier(param.Name()) {
			b.WriteString(param.Name())
			b.WriteString(" ")
		}
		b.WriteString(tc.typeToString(param.Type()))
	}
	b.WriteString(")")

	// Results
	results := sig.Results()
	if results.Len() > 0 {
		b.WriteString(" ")
		if results.Len() > 1 {
			b.WriteString("(")
		}
		for i := 0; i < results.Len(); i++ {
			if i > 0 {
				b.WriteString(", ")
			}
			b.WriteString(tc.typeToString(results.At(i).Type()))
		}
		if results.Len() > 1 {
			b.WriteString(")")
		}
	}

	return b.String()
}

// namedTypeToString converts a named type to string
func (tc *TypeChecker) namedTypeToString(named *types.Named) string {
	var b strings.Builder

	// Get the package name if it's from another package
	obj := named.Obj()
	if obj != nil && obj.Pkg() != nil {
		// Check if this is not the current package
		if tc.pkg == nil || obj.Pkg() != tc.pkg {
			b.WriteString(obj.Pkg().Name())
			b.WriteString(".")
		}
	}

	if obj != nil {
		b.WriteString(obj.Name())
	} else {
		b.WriteString(named.String())
	}

	// Type arguments (instantiated generic)
	if targs := named.TypeArgs(); targs.Len() > 0 {
		b.WriteString("[")
		for i := 0; i < targs.Len(); i++ {
			if i > 0 {
				b.WriteString(", ")
			}
			b.WriteString(tc.typeToString(targs.At(i)))
		}
		b.WriteString("]")
	}

	return b.String()
}

// GetObjectType returns the type of an object (variable, function, etc.)
func (tc *TypeChecker) GetObjectType(ident *ast.Ident) string {
	if tc.info == nil {
		return ""
	}

	obj := tc.info.ObjectOf(ident)
	if obj == nil {
		return ""
	}

	return tc.typeToString(obj.Type())
}

// GetFunctionType returns detailed type info for a function
func (tc *TypeChecker) GetFunctionType(fn *ast.FuncDecl) (params, results []Param) {
	if fn.Type == nil {
		return
	}

	// Use type checker if available
	if tc.info != nil {
		if sig, ok := tc.info.TypeOf(fn.Name).(*types.Signature); ok {
			// Get parameters
			if sig.Params() != nil {
				for i := 0; i < sig.Params().Len(); i++ {
					param := sig.Params().At(i)
					name := param.Name()
					if name == "" || isBlankIdentifier(name) {
						name = fmt.Sprintf("_%d", i)
					}
					params = append(params, Param{
						Name: name,
						Type: tc.typeToString(param.Type()),
					})
				}
			}

			// Get results
			if sig.Results() != nil {
				for i := 0; i < sig.Results().Len(); i++ {
					result := sig.Results().At(i)
					name := result.Name()
					if name == "" || isBlankIdentifier(name) {
						name = ""
					}
					results = append(results, Param{
						Name: name,
						Type: tc.typeToString(result.Type()),
					})
				}
			}

			return params, results
		}
	}

	// Fallback to AST-based extraction
	return extractParamsFromAST(fn.Type)
}

// GetStructFields returns typed fields for a struct
func (tc *TypeChecker) GetStructFields(spec *ast.TypeSpec) []FieldInfo {
	if tc.info == nil {
		return nil
	}

	// Get the named type
	named, ok := tc.info.ObjectOf(spec.Name).Type().(*types.Named)
	if !ok {
		return nil
	}

	// Get the underlying struct
	st, ok := named.Underlying().(*types.Struct)
	if !ok {
		return nil
	}

	var fields []FieldInfo
	for i := 0; i < st.NumFields(); i++ {
		field := st.Field(i)
		tag := st.Tag(i)

		fields = append(fields, FieldInfo{
			Name:     field.Name(),
			Type:     tc.typeToString(field.Type()),
			Exported: field.Exported(),
			Tag:      tag,
			Embedded: field.Embedded(),
		})
	}

	return fields
}

// GetStructMethods returns methods for a named type
func (tc *TypeChecker) GetStructMethods(typeName string) []FunctionInfo {
	if tc.pkg == nil {
		return nil
	}

	// Find the type in the package scope
	obj := tc.pkg.Scope().Lookup(typeName)
	if obj == nil {
		return nil
	}

	named, ok := obj.Type().(*types.Named)
	if !ok {
		return nil
	}

	var methods []FunctionInfo
	for i := 0; i < named.NumMethods(); i++ {
		method := named.Method(i)
		sig := method.Type().(*types.Signature)

		var params, results []Param
		if sig.Params() != nil {
			for j := 0; j < sig.Params().Len(); j++ {
				p := sig.Params().At(j)
				name := p.Name()
				if name == "" {
					name = fmt.Sprintf("_%d", j)
				}
				params = append(params, Param{
					Name: name,
					Type: tc.typeToString(p.Type()),
				})
			}
		}

		if sig.Results() != nil {
			for j := 0; j < sig.Results().Len(); j++ {
				r := sig.Results().At(j)
				results = append(results, Param{
					Name: r.Name(),
					Type: tc.typeToString(r.Type()),
				})
			}
		}

		methods = append(methods, FunctionInfo{
			Name:      method.Name(),
			Params:    params,
			Results:   results,
			IsMethod:  true,
			Receiver:  typeName,
			Exported:  method.Exported(),
		})
	}

	return methods
}

// Helper functions

func isBlankIdentifier(name string) bool {
	return name == "_"
}

func extractParamsFromAST(ft *ast.FuncType) (params, results []Param) {
	// Get parameters from AST
	if ft.Params != nil {
		for i, field := range ft.Params.List {
			for _, name := range field.Names {
				params = append(params, Param{
					Name: name.Name,
					Type: exprToString(field.Type),
				})
			}
			if len(field.Names) == 0 {
				params = append(params, Param{
					Name: fmt.Sprintf("_%d", i),
					Type: exprToString(field.Type),
				})
			}
		}
	}

	// Get results from AST
	if ft.Results != nil {
		for _, field := range ft.Results.List {
			for _, name := range field.Names {
				results = append(results, Param{
					Name: name.Name,
					Type: exprToString(field.Type),
				})
			}
			if len(field.Names) == 0 {
				results = append(results, Param{
					Name: "",
					Type: exprToString(field.Type),
				})
			}
		}
	}

	return params, results
}

// ResolveImportPath resolves an import path to its actual package path
func ResolveImportPath(importPath string, currentDir string) string {
	// Check if it's a relative import
	if strings.HasPrefix(importPath, "./") || strings.HasPrefix(importPath, "../") {
		absPath := filepath.Join(currentDir, importPath)
		return absPath
	}
	return importPath
}
