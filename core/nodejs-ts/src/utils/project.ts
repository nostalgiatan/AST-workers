import { Project } from 'ts-morph';
import path from 'path';
import fs from 'fs';

export function getProject(filePath: string): Project {
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
