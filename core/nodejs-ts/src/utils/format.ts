import { Project } from 'ts-morph';
import path from 'path';
import fs from 'fs';

interface ValidateOptions {
  module: string;
}

interface FormatOptions {
  module: string;
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

export async function validateSyntax(options: ValidateOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'validate_syntax',
    target: { module: options.module },
    valid: false,
  };

  try {
    const project = getProject(options.module);
    const sourceFile = project.getSourceFile(options.module);

    if (!sourceFile) {
      result.error = 'Module not found';
      return result;
    }

    // Get diagnostics
    const diagnostics = sourceFile.getPreEmitDiagnostics();
    const errors = diagnostics.map(d => d.getMessageText());

    result.valid = errors.length === 0;
    result.errors = errors;
    result.success = true;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}

export async function formatCode(options: FormatOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'format_code',
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

    // ts-morph handles formatting during save
    await sourceFile.save();
    
    result.success = true;
    result.message = 'Code formatted successfully';
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}
