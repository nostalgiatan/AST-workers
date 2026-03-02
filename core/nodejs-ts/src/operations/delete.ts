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
