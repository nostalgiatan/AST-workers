import { Project, SyntaxKind } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface RenameSymbolOptions {
  module: string;
  oldName: string;
  newName: string;
  symbolType?: string;
  className?: string;
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

export async function renameSymbol(options: RenameSymbolOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'rename_symbol',
    target: { module: options.module, oldName: options.oldName, newName: options.newName },
    success: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    // Parse scoped name for oldName
    const parts = options.oldName.split('.');
    let renamed = false;

    if (parts.length === 1) {
      // Simple name
      const func = sourceFile.getFunction(options.oldName);
      if (func) {
        func.rename(options.newName);
        renamed = true;
      }

      const classDecl = sourceFile.getClass(options.oldName);
      if (!renamed && classDecl) {
        classDecl.rename(options.newName);
        renamed = true;
      }

      // Also rename variable declarations
      if (!renamed) {
        sourceFile.getVariableDeclarations().forEach(varDecl => {
          if (varDecl.getName() === options.oldName) {
            varDecl.rename(options.newName);
            renamed = true;
          }
        });
      }
    } else if (parts.length === 2) {
      // Scoped name: ClassName.methodName
      const [className, memberName] = parts;
      const classDecl = sourceFile.getClass(className);
      if (classDecl) {
        const method = classDecl.getMethod(memberName);
        if (method) {
          method.rename(options.newName);
          renamed = true;
        }

        const property = classDecl.getProperty(memberName);
        if (!renamed && property) {
          property.rename(options.newName);
          renamed = true;
        }
      }
    }

    if (renamed) {
      await sourceFile.save();
      result.success = true;
      result.message = `Symbol '${options.oldName}' renamed to '${options.newName}'`;
    } else {
      result.error = `Symbol '${options.oldName}' not found`;
    }
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}
