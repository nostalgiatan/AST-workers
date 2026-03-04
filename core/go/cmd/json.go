package cmd

// JSON response structures
type Response struct {
	Success bool        `json:"success"`
	Error   string      `json:"error,omitempty"`
	Result  interface{} `json:"result,omitempty"`
}

type FunctionInfo struct {
	Name      string  `json:"name"`
	Line      int     `json:"line"`
	EndLine   int     `json:"end_line"`
	Params    []Param `json:"params,omitempty"`
	Results   []Param `json:"results,omitempty"`
	Docstring string  `json:"docstring,omitempty"`
	IsMethod  bool    `json:"is_method,omitempty"`
	Receiver  string  `json:"receiver,omitempty"`
	Exported  bool    `json:"exported"`
}

type Param struct {
	Name string `json:"name,omitempty"`
	Type string `json:"type,omitempty"`
}

type StructInfo struct {
	Name      string       `json:"name"`
	Line      int          `json:"line"`
	EndLine   int          `json:"end_line"`
	Fields    []FieldInfo  `json:"fields,omitempty"`
	Methods   []MethodInfo `json:"methods,omitempty"`
	Docstring string       `json:"docstring,omitempty"`
	Exported  bool         `json:"exported"`
}

type FieldInfo struct {
	Name     string `json:"name"`
	Type     string `json:"type"`
	Tag      string `json:"tag,omitempty"`
	Exported bool   `json:"exported"`
}

type MethodInfo struct {
	Name string `json:"name"`
	Line int    `json:"line"`
}

type ImportInfo struct {
	Path  string `json:"path"`
	Alias string `json:"alias,omitempty"`
	Line  int    `json:"line"`
}

type SymbolInfo struct {
	Name      string `json:"name"`
	Type      string `json:"type"`
	Line      int    `json:"line"`
	EndLine   int    `json:"end_line"`
	Code      string `json:"code,omitempty"`
	Docstring string `json:"docstring,omitempty"`
}
