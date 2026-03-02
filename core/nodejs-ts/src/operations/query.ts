import { Project, SyntaxKind, FunctionDeclaration, ClassDeclaration, MethodDeclaration } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface QueryOptions {
  module: string;
  className?: string;
  includePrivate?: boolean;
}

interface FindSymbolOptions {
  module: string;
  name: string;
  symbolType?: string;
}

function getProject(filePath: string): Project {
  // Try to find tsconfig.json in parent directories
  let tsConfigPath: string | undefined;
  let dir = path.dirname(path.resolve(filePath));
  
  while (dir !== path.dirname(dir)) {
    const candidate = path.join(dir, 'tsconfig.json');
    if (fs.existsSync(candidate)) {
      tsConfigPath = candidate;
      break;
    }
    dir = path.dirname(dir);
  }

  const projectOptions: ConstructorParameters<typeof Project>[0] = {
    skipAddingFilesFromTsConfig: true,
    skipFileDependencyResolution: true,
  };

  if (tsConfigPath) {
    projectOptions.tsConfigFilePath = tsConfigPath;
  }

  const project = new Project(projectOptions);
  project.addSourceFileAtPath(filePath);
  return project;
}

export async function listFunctions(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_functions',
    target: { module: options.module },
    functions: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const functions: Array<Record<string, unknown>> = [];

    if (options.className) {
      const classDecl = sourceFile.getClass(options.className);
      if (!classDecl) {
        result.error = `Class '${options.className}' not found`;
        return result;
      }

      classDecl.getMethods().forEach(method => {
        if (!options.includePrivate && method.hasModifier(SyntaxKind.PrivateKeyword)) {
          return;
        }

        functions.push({
          name: method.getName(),
          parameters: method.getParameters().map(p => ({
            name: p.getName(),
            type: p.getType().getText(),
          })),
          returnType: method.getReturnType().getText(),
          isStatic: method.isStatic(),
          isAsync: method.isAsync(),
          isPrivate: method.hasModifier(SyntaxKind.PrivateKeyword),
        });
      });
    } else {
      sourceFile.getFunctions().forEach(func => {
        functions.push({
          name: func.getName() || '<anonymous>',
          parameters: func.getParameters().map(p => ({
            name: p.getName(),
            type: p.getType().getText(),
          })),
          returnType: func.getReturnType().getText(),
          isAsync: func.isAsync(),
          isExported: func.isExported(),
        });
      });
    }

    result.functions = functions;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function listClasses(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_classes',
    target: { module: options.module },
    classes: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const classes: Array<Record<string, unknown>> = [];

    sourceFile.getClasses().forEach(classDecl => {
      if (!options.includePrivate && classDecl.hasModifier(SyntaxKind.PrivateKeyword)) {
        return;
      }

      classes.push({
        name: classDecl.getName(),
        extends: classDecl.getExtends()?.getText(),
        implements: classDecl.getImplements().map(i => i.getText()),
        isAbstract: classDecl.isAbstract(),
        isExported: classDecl.isExported(),
        methods: classDecl.getMethods().map(m => m.getName()),
      });
    });

    result.classes = classes;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function listImports(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_imports',
    target: { module: options.module },
    imports: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const imports: Array<Record<string, unknown>> = [];

    sourceFile.getImportDeclarations().forEach(importDecl => {
      const namedImports = importDecl.getNamedImports().map(ni => ({
        name: ni.getName(),
        alias: ni.getAliasNode()?.getText(),
      }));

      imports.push({
        module: importDecl.getModuleSpecifierValue(),
        defaultImport: importDecl.getDefaultImport()?.getText(),
        namedImports,
        isTypeOnly: importDecl.isTypeOnly(),
      });
    });

    result.imports = imports;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function findSymbol(options: FindSymbolOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'find_symbol',
    target: { module: options.module, name: options.name },
    found: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    // Parse scoped name (e.g., "ClassName.methodName")
    const parts = options.name.split('.');
    let found = false;
    let symbolInfo: Record<string, unknown> = {};

    if (parts.length === 1) {
      // Simple name - search at module level
      const func = sourceFile.getFunction(options.name);
      if (func) {
        found = true;
        symbolInfo = {
          type: 'function',
          name: func.getName(),
          line: func.getStartLineNumber(),
        };
      }

      if (!found) {
        const classDecl = sourceFile.getClass(options.name);
        if (classDecl) {
          found = true;
          symbolInfo = {
            type: 'class',
            name: classDecl.getName(),
            line: classDecl.getStartLineNumber(),
          };
        }
      }
    } else if (parts.length === 2) {
      // Scoped name - ClassName.methodName
      const [className, memberName] = parts;
      const classDecl = sourceFile.getClass(className);
      if (classDecl) {
        const method = classDecl.getMethod(memberName);
        if (method) {
          found = true;
          symbolInfo = {
            type: 'method',
            name: memberName,
            className,
            line: method.getStartLineNumber(),
          };
        }
      }
    }

    result.found = found;
    if (found) {
      result.symbol = symbolInfo;
    }
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function showSymbol(options: FindSymbolOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'show_symbol',
    target: { module: options.module, name: options.name },
    found: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    // Parse scoped name
    const parts = options.name.split('.');
    let targetNode: FunctionDeclaration | MethodDeclaration | ClassDeclaration | undefined;

    if (parts.length === 1) {
      const func = sourceFile.getFunction(options.name);
      const classDecl = sourceFile.getClass(options.name);

      targetNode = func || classDecl;
    } else if (parts.length === 2) {
      const [className, memberName] = parts;
      const classDecl = sourceFile.getClass(className);
      if (classDecl) {
        targetNode = classDecl.getMethod(memberName);
      }
    }

    if (targetNode) {
      const startLine = Math.max(1, targetNode.getStartLineNumber() - 4);
      const endLine = targetNode.getEndLineNumber() + 3;
      const fullText = sourceFile.getFullText();
      const lines = fullText.split('\n');

      result.found = true;
      result.line = targetNode.getStartLineNumber();
      result.endLine = targetNode.getEndLineNumber();
      result.code = lines.slice(startLine - 1, endLine).join('\n');
      result.success = true;
    } else {
      result.message = `Symbol '${options.name}' not found`;
    }
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}