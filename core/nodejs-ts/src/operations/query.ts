import { Project, SyntaxKind, FunctionDeclaration, ClassDeclaration, MethodDeclaration, InterfaceDeclaration, EnumDeclaration, TypeAliasDeclaration, VariableStatement, MethodSignature } from 'ts-morph';
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
          typeParameters: method.getTypeParameters().map(tp => tp.getName()),
          isStatic: method.isStatic(),
          isAsync: method.isAsync(),
          isPrivate: method.hasModifier(SyntaxKind.PrivateKeyword),
          isProtected: method.hasModifier(SyntaxKind.ProtectedKeyword),
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
          typeParameters: func.getTypeParameters().map(tp => tp.getName()),
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
        typeParameters: classDecl.getTypeParameters().map(tp => tp.getName()),
        isAbstract: classDecl.isAbstract(),
        isExported: classDecl.isExported(),
        methods: classDecl.getMethods().map(m => m.getName()),
        properties: classDecl.getProperties().map(p => p.getName()),
      });
    });

    result.classes = classes;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function listInterfaces(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_interfaces',
    target: { module: options.module },
    interfaces: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const interfaces: Array<Record<string, unknown>> = [];

    sourceFile.getInterfaces().forEach(interfaceDecl => {
      interfaces.push({
        name: interfaceDecl.getName(),
        extends: interfaceDecl.getExtends().map(e => e.getText()),
        typeParameters: interfaceDecl.getTypeParameters().map(tp => tp.getName()),
        isExported: interfaceDecl.isExported(),
        properties: interfaceDecl.getProperties().map(p => p.getName()),
        methods: interfaceDecl.getMethods().map(m => m.getName()),
      });
    });

    result.interfaces = interfaces;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function listEnums(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_enums',
    target: { module: options.module },
    enums: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const enums: Array<Record<string, unknown>> = [];

    sourceFile.getEnums().forEach(enumDecl => {
      enums.push({
        name: enumDecl.getName(),
        isConst: enumDecl.isConstEnum(),
        isExported: enumDecl.isExported(),
        members: enumDecl.getMembers().map(m => ({
          name: m.getName(),
          value: m.getValue(),
        })),
      });
    });

    result.enums = enums;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function listVariables(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_variables',
    target: { module: options.module },
    variables: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const variables: Array<Record<string, unknown>> = [];

    sourceFile.getVariableStatements().forEach(varStmt => {
      const declarationKind = varStmt.getDeclarationKind();
      varStmt.getDeclarations().forEach(decl => {
        variables.push({
          name: decl.getName(),
          type: decl.getType().getText(),
          initializer: decl.getInitializer()?.getText(),
          kind: declarationKind,
          isExported: varStmt.isExported(),
        });
      });
    });

    result.variables = variables;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function listTypeAliases(options: QueryOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'list_type_aliases',
    target: { module: options.module },
    typeAliases: [],
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const typeAliases: Array<Record<string, unknown>> = [];

    sourceFile.getTypeAliases().forEach(typeAlias => {
      typeAliases.push({
        name: typeAlias.getName(),
        type: typeAlias.getTypeNode()?.getText(),
        typeParameters: typeAlias.getTypeParameters().map(tp => tp.getName()),
        isExported: typeAlias.isExported(),
      });
    });

    result.typeAliases = typeAliases;
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
        namespaceImport: importDecl.getNamespaceImport()?.getText(),
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

    const parts = options.name.split('.');
    let found = false;
    let symbolInfo: Record<string, unknown> = {};

    if (parts.length === 1) {
      const func = sourceFile.getFunction(options.name);
      if (func) {
        found = true;
        symbolInfo = { type: 'function', name: func.getName(), line: func.getStartLineNumber() };
      }

      if (!found) {
        const classDecl = sourceFile.getClass(options.name);
        if (classDecl) {
          found = true;
          symbolInfo = { type: 'class', name: classDecl.getName(), line: classDecl.getStartLineNumber() };
        }
      }

      if (!found) {
        const interfaceDecl = sourceFile.getInterface(options.name);
        if (interfaceDecl) {
          found = true;
          symbolInfo = { type: 'interface', name: interfaceDecl.getName(), line: interfaceDecl.getStartLineNumber() };
        }
      }

      if (!found) {
        const enumDecl = sourceFile.getEnum(options.name);
        if (enumDecl) {
          found = true;
          symbolInfo = { type: 'enum', name: enumDecl.getName(), line: enumDecl.getStartLineNumber() };
        }
      }

      if (!found) {
        const typeAlias = sourceFile.getTypeAlias(options.name);
        if (typeAlias) {
          found = true;
          symbolInfo = { type: 'typeAlias', name: typeAlias.getName(), line: typeAlias.getStartLineNumber() };
        }
      }
    } else if (parts.length === 2) {
      const [className, memberName] = parts;
      const classDecl = sourceFile.getClass(className);
      if (classDecl) {
        const method = classDecl.getMethod(memberName);
        if (method) {
          found = true;
          symbolInfo = { type: 'method', name: memberName, className, line: method.getStartLineNumber() };
        }

        if (!found) {
          const property = classDecl.getProperty(memberName);
          if (property) {
            found = true;
            symbolInfo = { type: 'property', name: memberName, className, line: property.getStartLineNumber() };
          }
        }
      }

      if (!found) {
        const interfaceDecl = sourceFile.getInterface(className);
        if (interfaceDecl) {
          const method = interfaceDecl.getMethod(memberName);
          if (method) {
            found = true;
            symbolInfo = { type: 'interfaceMethod', name: memberName, interfaceName: className, line: method.getStartLineNumber() };
          }
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

    const parts = options.name.split('.');
    let targetNode: FunctionDeclaration | MethodDeclaration | ClassDeclaration | InterfaceDeclaration | EnumDeclaration | TypeAliasDeclaration | MethodSignature | undefined;

    if (parts.length === 1) {
      targetNode = sourceFile.getFunction(options.name) ||
                   sourceFile.getClass(options.name) ||
                   sourceFile.getInterface(options.name) ||
                   sourceFile.getEnum(options.name) ||
                   sourceFile.getTypeAlias(options.name);
    } else if (parts.length === 2) {
      const [className, memberName] = parts;
      const classDecl = sourceFile.getClass(className);
      if (classDecl) {
        targetNode = classDecl.getMethod(memberName);
      }
      if (!targetNode) {
        const interfaceDecl = sourceFile.getInterface(className);
        if (interfaceDecl) {
          const method = interfaceDecl.getMethod(memberName);
          if (method) {
            // Handle MethodSignature separately
            const startLine = Math.max(1, method.getStartLineNumber() - 4);
            const endLine = method.getEndLineNumber() + 3;
            const fullText = sourceFile.getFullText();
            const lines = fullText.split('\n');

            result.found = true;
            result.line = method.getStartLineNumber();
            result.endLine = method.getEndLineNumber();
            result.code = lines.slice(startLine - 1, endLine).join('\n');
            result.success = true;
            return result;
          }
        }
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
