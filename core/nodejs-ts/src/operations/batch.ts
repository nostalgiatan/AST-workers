import { insertFunction, insertClass, insertImport } from './insert.js';
import { updateFunction } from './update.js';
import { deleteFunction, deleteClass } from './delete.js';
import { renameSymbol } from './rename.js';
import { listFunctions, listClasses, listImports, findSymbol, showSymbol } from './query.js';
import { validateSyntax, formatCode } from '../utils/format.js';
import fs from 'fs';
import path from 'path';

interface BatchOptions {
  module: string;
  json: string;
}

interface Operation {
  operation: string;
  [key: string]: unknown;
}

const operationHandlers: Record<string, (params: Record<string, unknown>) => Promise<Record<string, unknown>>> = {
  insert_function: (p) => insertFunction(p as unknown as Parameters<typeof insertFunction>[0]),
  insert_class: (p) => insertClass(p as unknown as Parameters<typeof insertClass>[0]),
  insert_import: (p) => insertImport(p as unknown as Parameters<typeof insertImport>[0]),
  update_function: (p) => updateFunction(p as unknown as Parameters<typeof updateFunction>[0]),
  delete_function: (p) => deleteFunction(p as unknown as Parameters<typeof deleteFunction>[0]),
  delete_class: (p) => deleteClass(p as unknown as Parameters<typeof deleteClass>[0]),
  rename_symbol: (p) => renameSymbol(p as unknown as Parameters<typeof renameSymbol>[0]),
  list_functions: (p) => listFunctions(p as unknown as Parameters<typeof listFunctions>[0]),
  list_classes: (p) => listClasses(p as unknown as Parameters<typeof listClasses>[0]),
  list_imports: (p) => listImports(p as unknown as Parameters<typeof listImports>[0]),
  find_symbol: (p) => findSymbol(p as unknown as Parameters<typeof findSymbol>[0]),
  show_symbol: (p) => showSymbol(p as unknown as Parameters<typeof showSymbol>[0]),
  validate_syntax: (p) => validateSyntax(p as unknown as Parameters<typeof validateSyntax>[0]),
  format_code: (p) => formatCode(p as unknown as Parameters<typeof formatCode>[0]),
};

export async function batchOperations(options: BatchOptions): Promise<Record<string, unknown>> {
  const result: Record<string, unknown> = {
    operation: 'batch',
    target: { module: options.module },
    success: false,
    results: [],
  };

  try {
    // Read JSON file or parse inline JSON
    let operations: Operation[];
    
    if (options.json.startsWith('[') || options.json.startsWith('{')) {
      operations = JSON.parse(options.json);
      if (!Array.isArray(operations)) {
        operations = [operations];
      }
    } else {
      const jsonPath = path.resolve(options.json);
      const content = fs.readFileSync(jsonPath, 'utf-8');
      operations = JSON.parse(content);
      if (!Array.isArray(operations)) {
        operations = [operations];
      }
    }

    const results: Record<string, unknown>[] = [];

    for (const op of operations) {
      const opType = op.operation;
      const handler = operationHandlers[opType];

      if (!handler) {
        results.push({
          operation: opType,
          success: false,
          error: `Unknown operation: ${opType}`,
        });
        continue;
      }

      // Add module path if not specified
      const params = { ...op };
      if (!params.module) {
        params.module = options.module;
      }

      try {
        const opResult = await handler(params);
        results.push(opResult);
      } catch (error) {
        results.push({
          operation: opType,
          success: false,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    result.results = results;
    result.success = results.every(r => r.success === true);
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
  }

  return result;
}