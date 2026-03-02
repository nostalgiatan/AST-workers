import { Project } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface DeleteFunctionOptions {
  module: string;
  name: string;
  className?: string;
}

interface DeleteClassOptions {
  module: string;
  name: string;
}

interface DeleteInterfaceOptions {
  module: string;
  name: string;
}

interface DeleteEnumOptions {
  module: string;
  name: string;
}

interface DeleteVariableOptions {
  module: string;
  name: string;
}

interface DeleteTypeAliasOptions {
  module: string;
  name: string;
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

export async function deleteFunction(options: DeleteFunctionOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'delete_function',
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

    if (options.className) {
      const classDecl = sourceFile.getClass(options.className);
      if (!classDecl) {
        result.error = `Class '${options.className}' not found`;
        return result;
      }

      const method = classDecl.getMethod(options.name);
      if (!method) {
        result.error = `Method '${options.name}' not found in class '${options.className}'`;
        return result;
      }

      method.remove();
    } else {
      const func = sourceFile.getFunction(options.name);
      if (!func) {
        result.error = `Function '${options.name}' not found`;
        return result;
      }

      func.remove();
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Function '${options.name}' deleted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function deleteClass(options: DeleteClassOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'delete_class',
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

    const classDecl = sourceFile.getClass(options.name);
    if (!classDecl) {
      result.error = `Class '${options.name}' not found`;
      return result;
    }

    classDecl.remove();

    await sourceFile.save();
    result.success = true;
    result.message = `Class '${options.name}' deleted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function deleteInterface(options: DeleteInterfaceOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'delete_interface',
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

    const interfaceDecl = sourceFile.getInterface(options.name);
    if (!interfaceDecl) {
      result.error = `Interface '${options.name}' not found`;
      return result;
    }

    interfaceDecl.remove();

    await sourceFile.save();
    result.success = true;
    result.message = `Interface '${options.name}' deleted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function deleteEnum(options: DeleteEnumOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'delete_enum',
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

    const enumDecl = sourceFile.getEnum(options.name);
    if (!enumDecl) {
      result.error = `Enum '${options.name}' not found`;
      return result;
    }

    enumDecl.remove();

    await sourceFile.save();
    result.success = true;
    result.message = `Enum '${options.name}' deleted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function deleteVariable(options: DeleteVariableOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'delete_variable',
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

    // Find variable in variable statements
    let found = false;
    for (const varStmt of sourceFile.getVariableStatements()) {
      for (const decl of varStmt.getDeclarations()) {
        if (decl.getName() === options.name) {
          if (varStmt.getDeclarations().length === 1) {
            varStmt.remove();
          } else {
            decl.remove();
          }
          found = true;
          break;
        }
      }
      if (found) break;
    }

    if (!found) {
      result.error = `Variable '${options.name}' not found`;
      return result;
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Variable '${options.name}' deleted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function deleteTypeAlias(options: DeleteTypeAliasOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'delete_type_alias',
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

    const typeAlias = sourceFile.getTypeAlias(options.name);
    if (!typeAlias) {
      result.error = `Type alias '${options.name}' not found`;
      return result;
    }

    typeAlias.remove();

    await sourceFile.save();
    result.success = true;
    result.message = `Type alias '${options.name}' deleted successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}