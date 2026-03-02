import { Project, SourceFile, FunctionDeclaration, ClassDeclaration, ImportDeclaration, SyntaxKind, InterfaceDeclaration, TypeAliasDeclaration, EnumDeclaration, VariableStatement, GetAccessorDeclaration, SetAccessorDeclaration, PropertyDeclaration, VariableDeclarationKind } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface InsertFunctionOptions {
  module: string;
  name: string;
  params?: string;
  returnType?: string;
  body?: string;
  typeParams?: string;
  className?: string;
  decorators?: string;
  isAsync?: boolean;
  isStatic?: boolean;
  isPrivate?: boolean;
  isProtected?: boolean;
  isReadonly?: boolean;
  docstring?: string;
  after?: string;
  before?: string;
}

interface InsertClassOptions {
  module: string;
  name: string;
  bases?: string;
  implements?: string;
  decorators?: string;
  typeParams?: string;
  docstring?: string;
  isAbstract?: boolean;
  isExported?: boolean;
  after?: string;
  before?: string;
}

interface InsertInterfaceOptions {
  module: string;
  name: string;
  extends?: string;
  properties?: string;  // Format: "prop1:Type1, prop2?:Type2, readonly prop3:Type3"
  typeParams?: string;
  docstring?: string;
  isExported?: boolean;
}

interface InsertTypeAliasOptions {
  module: string;
  name: string;
  type: string;
  typeParams?: string;
  docstring?: string;
  isExported?: boolean;
}

interface InsertEnumOptions {
  module: string;
  name: string;
  members?: string;
  docstring?: string;
  isConst?: boolean;
  isExported?: boolean;
}

interface InsertVariableOptions {
  module: string;
  name: string;
  type?: string;
  initializer?: string;
  isConst?: boolean;
  isLet?: boolean;
  isExported?: boolean;
  docstring?: string;
}

interface InsertPropertyOptions {
  module: string;
  name: string;
  type?: string;
  initializer?: string;
  className: string;
  isStatic?: boolean;
  isReadonly?: boolean;
  isPrivate?: boolean;
  isProtected?: boolean;
  docstring?: string;
}

interface InsertAccessorOptions {
  module: string;
  name: string;
  className: string;
  type?: string;
  body?: string;
  isStatic?: boolean;
  isPrivate?: boolean;
  isProtected?: boolean;
  kind: 'get' | 'set';
  docstring?: string;
}

interface InsertImportOptions {
  module: string;
  name?: string;
  fromModule?: string;
  alias?: string;
  isDefault?: boolean;
  isTypeOnly?: boolean;
  isNamespace?: boolean;
}

interface InsertNamespaceOptions {
  module: string;
  name: string;
  body?: string;
  isExported?: boolean;
  docstring?: string;
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

function parseParams(paramsStr: string): Array<{ name: string; type?: string; initializer?: string; isRest?: boolean; isOptional?: boolean }> {
  const params: Array<{ name: string; type?: string; initializer?: string; isRest?: boolean; isOptional?: boolean }> = [];

  const parts = paramsStr.split(',');
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    // Match: [..]name[?][:type][=default]
    const match = trimmed.match(/^(\.\.\.)?(\w+)(\?)?(?::\s*([^=]+))?(?:=\s*(.+))?$/);
    if (match) {
      params.push({
        isRest: !!match[1],
        name: match[2],
        isOptional: !!match[3],
        type: match[4]?.trim(),
        initializer: match[5]?.trim(),
      });
    }
  }

  return params;
}

function parseTypeParams(typeParamsStr: string): Array<{ name: string; constraint?: string; default?: string }> {
  const params: Array<{ name: string; constraint?: string; default?: string }> = [];
  
  // Split by comma, but respect nested brackets
  const parts: string[] = [];
  let current = '';
  let depth = 0;
  
  for (const char of typeParamsStr) {
    if (char === '<' || char === '{' || char === '[') depth++;
    if (char === '>' || char === '}' || char === ']') depth--;
    if (char === ',' && depth === 0) {
      parts.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  if (current.trim()) parts.push(current.trim());

  for (const part of parts) {
    // Match: name[extends constraint][= default]
    const match = part.match(/^(\w+)(?:\s+extends\s+([^=]+))?(?:=\s*(.+))?$/);
    if (match) {
      params.push({
        name: match[1],
        constraint: match[2]?.trim(),
        default: match[3]?.trim(),
      });
    }
  }

  return params;
}

interface PropertyDefinition {
  name: string;
  type?: string;
  isOptional?: boolean;
  isReadonly?: boolean;
}

function parseProperties(propertiesStr: string): PropertyDefinition[] {
  const properties: PropertyDefinition[] = [];

  const parts = propertiesStr.split(',');
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    // Match: [readonly]name[?][:type]
    // Examples: "name:string", "name?:string", "readonly name:string", "readonly name?:string"
    const match = trimmed.match(/^(readonly\s+)?(\w+)(\?)?(?::\s*(.+))?$/);
    if (match) {
      properties.push({
        isReadonly: !!match[1],
        name: match[2],
        isOptional: !!match[3],
        type: match[4]?.trim(),
      });
    }
  }

  return properties;
}

export async function insertFunction(options: InsertFunctionOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_function',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const params = options.params ? parseParams(options.params) : [];
    const typeParams = options.typeParams ? parseTypeParams(options.typeParams) : undefined;

    if (options.className) {
      const classDecl = sourceFile.getClass(options.className);
      if (!classDecl) {
        result.error = `Class '${options.className}' not found`;
        return result;
      }

      const method = classDecl.addMethod({
        name: options.name,
        parameters: params.map(p => ({
          name: p.name,
          type: p.type,
          initializer: p.initializer,
          isRestParameter: p.isRest,
          hasQuestionToken: p.isOptional,
        })),
        returnType: options.returnType,
        typeParameters: typeParams?.map(t => ({
          name: t.name,
          constraint: t.constraint,
          default: t.default,
        })),
        isAsync: options.isAsync,
        isStatic: options.isStatic,
        docs: options.docstring ? [{ description: options.docstring }] : undefined,
      });

      if (options.body) {
        method.setBodyText(options.body);
      }

      if (options.isPrivate) {
        method.toggleModifier('private', true);
      }
      if (options.isProtected) {
        method.toggleModifier('protected', true);
      }
    } else {
      const func = sourceFile.addFunction({
        name: options.name,
        parameters: params.map(p => ({
          name: p.name,
          type: p.type,
          initializer: p.initializer,
          isRestParameter: p.isRest,
          hasQuestionToken: p.isOptional,
        })),
        returnType: options.returnType,
        typeParameters: typeParams?.map(t => ({
          name: t.name,
          constraint: t.constraint,
          default: t.default,
        })),
        isAsync: options.isAsync,
        isExported: true,
        docs: options.docstring ? [{ description: options.docstring }] : undefined,
      });

      if (options.body) {
        func.setBodyText(options.body);
      }
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Function '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertClass(options: InsertClassOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_class',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const typeParams = options.typeParams ? parseTypeParams(options.typeParams) : undefined;

    const classDecl = sourceFile.addClass({
      name: options.name,
      isAbstract: options.isAbstract,
      isExported: options.isExported !== false,
      typeParameters: typeParams?.map(t => ({
        name: t.name,
        constraint: t.constraint,
        default: t.default,
      })),
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    if (options.bases) {
      classDecl.setExtends(options.bases);
    }

    if (options.implements) {
      const impls = options.implements.split(',').map(s => s.trim());
      classDecl.addImplements(impls);
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Class '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertInterface(options: InsertInterfaceOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_interface',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const typeParams = options.typeParams ? parseTypeParams(options.typeParams) : undefined;

    const interfaceDecl = sourceFile.addInterface({
      name: options.name,
      isExported: options.isExported !== false,
      typeParameters: typeParams?.map(t => ({
        name: t.name,
        constraint: t.constraint,
        default: t.default,
      })),
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    if (options.extends) {
      const extendsList = options.extends.split(',').map(s => s.trim());
      interfaceDecl.addExtends(extendsList);
    }

    if (options.properties) {
      const properties = parseProperties(options.properties);
      for (const prop of properties) {
        interfaceDecl.addProperty({
          name: prop.name,
          type: prop.type,
          hasQuestionToken: prop.isOptional,
          isReadonly: prop.isReadonly,
        });
      }
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Interface '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertTypeAlias(options: InsertTypeAliasOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_type_alias',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const typeParams = options.typeParams ? parseTypeParams(options.typeParams) : undefined;

    sourceFile.addTypeAlias({
      name: options.name,
      type: options.type,
      isExported: options.isExported !== false,
      typeParameters: typeParams?.map(t => ({
        name: t.name,
        constraint: t.constraint,
        default: t.default,
      })),
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    await sourceFile.save();
    result.success = true;
    result.message = `Type alias '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertEnum(options: InsertEnumOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_enum',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const members = options.members ? options.members.split(',').map(m => {
      const [name, value] = m.trim().split('=').map(s => s.trim());
      return { name, value };
    }) : [];

    sourceFile.addEnum({
      name: options.name,
      isConst: options.isConst,
      isExported: options.isExported !== false,
      members: members.map(m => ({
        name: m.name,
        initializer: m.value,
      })),
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    await sourceFile.save();
    result.success = true;
    result.message = `Enum '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertVariable(options: InsertVariableOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_variable',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    sourceFile.addVariableStatement({
      isExported: options.isExported !== false,
      declarationKind: options.isConst ? VariableDeclarationKind.Const : options.isLet ? VariableDeclarationKind.Let : VariableDeclarationKind.Var,
      declarations: [{
        name: options.name,
        type: options.type,
        initializer: options.initializer,
      }],
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    await sourceFile.save();
    result.success = true;
    result.message = `Variable '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertProperty(options: InsertPropertyOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_property',
    target: { module: options.module, name: options.name, className: options.className },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const classDecl = sourceFile.getClass(options.className);
    if (!classDecl) {
      result.error = `Class '${options.className}' not found`;
      return result;
    }

    classDecl.addProperty({
      name: options.name,
      type: options.type,
      initializer: options.initializer,
      isStatic: options.isStatic,
      isReadonly: options.isReadonly,
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    if (options.isPrivate) {
      const prop = classDecl.getProperty(options.name);
      prop?.toggleModifier('private', true);
    }
    if (options.isProtected) {
      const prop = classDecl.getProperty(options.name);
      prop?.toggleModifier('protected', true);
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Property '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertAccessor(options: InsertAccessorOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_accessor',
    target: { module: options.module, name: options.name, className: options.className, kind: options.kind },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const classDecl = sourceFile.getClass(options.className);
    if (!classDecl) {
      result.error = `Class '${options.className}' not found`;
      return result;
    }

    if (options.kind === 'get') {
      const accessor = classDecl.addGetAccessor({
        name: options.name,
        returnType: options.type,
        isStatic: options.isStatic,
        docs: options.docstring ? [{ description: options.docstring }] : undefined,
      });
      if (options.body) {
        accessor.setBodyText(options.body);
      }
      if (options.isPrivate) accessor.toggleModifier('private', true);
      if (options.isProtected) accessor.toggleModifier('protected', true);
    } else {
      const accessor = classDecl.addSetAccessor({
        name: options.name,
        parameters: [{ name: 'value', type: options.type }],
        isStatic: options.isStatic,
        docs: options.docstring ? [{ description: options.docstring }] : undefined,
      });
      if (options.body) {
        accessor.setBodyText(options.body);
      }
      if (options.isPrivate) accessor.toggleModifier('private', true);
      if (options.isProtected) accessor.toggleModifier('protected', true);
    }

    await sourceFile.save();
    result.success = true;
    result.message = `${options.kind === 'get' ? 'Getter' : 'Setter'} '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertImport(options: InsertImportOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_import',
    target: { module: options.module },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    if (options.isNamespace && options.fromModule) {
      // import * as alias from 'module'
      sourceFile.addImportDeclaration({
        moduleSpecifier: options.fromModule,
        namespaceImport: options.alias || 'ns',
        isTypeOnly: options.isTypeOnly,
      });
    } else if (options.fromModule) {
      const namedImports = options.name?.split(',').map(s => s.trim()) || [];
      sourceFile.addImportDeclaration({
        moduleSpecifier: options.fromModule,
        namedImports: namedImports.map(name => ({
          name,
          alias: options.alias,
        })),
        isTypeOnly: options.isTypeOnly,
      });
    } else if (options.name) {
      if (options.isDefault) {
        sourceFile.addImportDeclaration({
          moduleSpecifier: options.name,
          defaultImport: options.alias || options.name,
        });
      } else {
        sourceFile.addImportDeclaration({
          moduleSpecifier: options.name,
        });
      }
    }

    await sourceFile.save();
    result.success = true;
    result.message = 'Import inserted successfully';
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function insertNamespace(options: InsertNamespaceOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'insert_namespace',
    target: { module: options.module, name: options.name },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    const ns = sourceFile.addModule({
      name: options.name,
      isExported: options.isExported !== false,
      docs: options.docstring ? [{ description: options.docstring }] : undefined,
    });

    if (options.body) {
      // Parse and add statements to namespace
      ns.addStatements(options.body);
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Namespace '${options.name}' inserted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}