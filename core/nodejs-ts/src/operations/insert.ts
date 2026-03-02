import { Project, SourceFile, FunctionDeclaration, ClassDeclaration, ImportDeclaration, SyntaxKind } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface InsertFunctionOptions {
  module: string;
  name: string;
  params?: string;
  returnType?: string;
  body?: string;
  className?: string;
  decorators?: string;
  isAsync?: boolean;
  isStatic?: boolean;
  isPrivate?: boolean;
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
  docstring?: string;
  isAbstract?: boolean;
  after?: string;
  before?: string;
}

interface InsertImportOptions {
  module: string;
  name?: string;
  fromModule?: string;
  alias?: string;
  isDefault?: boolean;
  isTypeOnly?: boolean;
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

    // Parse parameters
    const params = options.params ? parseParams(options.params) : [];

    if (options.className) {
      // Insert method into class
      const classDecl = sourceFile.getClass(options.className);
      if (!classDecl) {
        result.error = `Class '${options.className}' not found`;
        return result;
      }

      const method = classDecl.addMethod({
        name: options.name,
        parameters: params,
        returnType: options.returnType,
        isAsync: options.isAsync,
        isStatic: options.isStatic,
        isAbstract: options.isPrivate ? false : undefined,
        docs: options.docstring ? [{ description: options.docstring }] : undefined,
      });

      if (options.body) {
        method.setBodyText(options.body);
      }

      if (options.isPrivate) {
        method.toggleModifier('private', true);
      }
    } else {
      // Insert function at module level
      const func = sourceFile.addFunction({
        name: options.name,
        parameters: params,
        returnType: options.returnType,
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

function parseParams(paramsStr: string): Array<{ name: string; type?: string; initializer?: string }> {
  const params: Array<{ name: string; type?: string; initializer?: string }> = [];

  // Simple parsing - split by comma, handle type and default
  const parts = paramsStr.split(',');
  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    // Match: name[:type][=default]
    const match = trimmed.match(/^(\w+)(?::\s*([^=]+))?(?:=\s*(.+))?$/);
    if (match) {
      params.push({
        name: match[1],
        type: match[2]?.trim(),
        initializer: match[3]?.trim(),
      });
    }
  }

  return params;
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

    const classDecl = sourceFile.addClass({
      name: options.name,
      isAbstract: options.isAbstract,
      isExported: true,
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

    if (options.fromModule) {
      // from X import Y
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
      // import X
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
