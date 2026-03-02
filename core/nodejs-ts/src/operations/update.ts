import { Project, FunctionDeclaration, MethodDeclaration } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface UpdateFunctionOptions {
  module: string;
  name: string;
  className?: string;
  body?: string;
  params?: string;
  addParams?: string;
  removeParams?: string[];
  returnType?: string;
  addDecorators?: string[];
  removeDecorators?: string[];
  docstring?: string;
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

export async function updateFunction(options: UpdateFunctionOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'update_function',
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

    let func: FunctionDeclaration | MethodDeclaration | undefined;

    if (options.className) {
      const classDecl = sourceFile.getClass(options.className);
      if (!classDecl) {
        result.error = `Class '${options.className}' not found`;
        return result;
      }
      func = classDecl.getMethod(options.name);
    } else {
      func = sourceFile.getFunction(options.name);
    }

    if (!func) {
      result.error = `Function '${options.name}' not found`;
      return result;
    }

    // Update body
    if (options.body !== undefined) {
      func.setBodyText(options.body);
    }

    // Update return type
    if (options.returnType !== undefined) {
      func.setReturnType(options.returnType || 'void');
    }

    // Update parameters
    if (options.params) {
      const params = parseParams(options.params);
      func.getParameters().forEach(p => p.remove());
      params.forEach(p => {
        func!.addParameter(p);
      });
    }

    // Remove parameters
    if (options.removeParams && options.removeParams.length > 0) {
      options.removeParams.forEach(paramName => {
        const param = func!.getParameter(paramName);
        if (param) param.remove();
      });
    }

    // Update docstring
    if (options.docstring !== undefined) {
      if (options.docstring) {
        func.addJsDocs([{ description: options.docstring }]);
      } else {
        func.getJsDocs().forEach((doc: any) => doc.remove());
      }
    }

    await sourceFile.save();
    result.success = true;
    result.message = `Function '${options.name}' updated successfully`;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

function parseParams(paramsStr: string): Array<{ name: string; type?: string; initializer?: string }> {
  const params: Array<{ name: string; type?: string; initializer?: string }> = [];
  const parts = paramsStr.split(',');

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

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
