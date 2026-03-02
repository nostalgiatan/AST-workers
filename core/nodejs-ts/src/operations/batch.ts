import {
  insertFunction,
  insertClass,
  insertInterface,
  insertTypeAlias,
  insertEnum,
  insertVariable,
  insertProperty,
  insertAccessor,
  insertImport,
  insertNamespace,
} from './insert.js';
import { updateFunction } from './update.js';
import {
  deleteFunction,
  deleteClass,
  deleteInterface,
  deleteEnum,
  deleteVariable,
  deleteTypeAlias,
} from './delete.js';
import { renameSymbol } from './rename.js';
import {
  listFunctions,
  listClasses,
  listImports,
  listInterfaces,
  listEnums,
  listVariables,
  listTypeAliases,
  findSymbol,
  showSymbol,
} from './query.js';
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
  // Insert operations
  insert_function: (p) => insertFunction(p as unknown as Parameters<typeof insertFunction>[0]),
  insert_class: (p) => insertClass(p as unknown as Parameters<typeof insertClass>[0]),
  insert_interface: (p) => insertInterface(p as unknown as Parameters<typeof insertInterface>[0]),
  insert_type_alias: (p) => insertTypeAlias(p as unknown as Parameters<typeof insertTypeAlias>[0]),
  insert_enum: (p) => insertEnum(p as unknown as Parameters<typeof insertEnum>[0]),
  insert_variable: (p) => insertVariable(p as unknown as Parameters<typeof insertVariable>[0]),
  insert_property: (p) => insertProperty(p as unknown as Parameters<typeof insertProperty>[0]),
  insert_accessor: (p) => insertAccessor(p as unknown as Parameters<typeof insertAccessor>[0]),
  insert_import: (p) => insertImport(p as unknown as Parameters<typeof insertImport>[0]),
  insert_namespace: (p) => insertNamespace(p as unknown as Parameters<typeof insertNamespace>[0]),
  // Update operations
  update_function: (p) => updateFunction(p as unknown as Parameters<typeof updateFunction>[0]),
  // Delete operations
  delete_function: (p) => deleteFunction(p as unknown as Parameters<typeof deleteFunction>[0]),
  delete_class: (p) => deleteClass(p as unknown as Parameters<typeof deleteClass>[0]),
  delete_interface: (p) => deleteInterface(p as unknown as Parameters<typeof deleteInterface>[0]),
  delete_enum: (p) => deleteEnum(p as unknown as Parameters<typeof deleteEnum>[0]),
  delete_variable: (p) => deleteVariable(p as unknown as Parameters<typeof deleteVariable>[0]),
  delete_type_alias: (p) => deleteTypeAlias(p as unknown as Parameters<typeof deleteTypeAlias>[0]),
  // Rename operations
  rename_symbol: (p) => renameSymbol(p as unknown as Parameters<typeof renameSymbol>[0]),
  // Query operations
  list_functions: (p) => listFunctions(p as unknown as Parameters<typeof listFunctions>[0]),
  list_classes: (p) => listClasses(p as unknown as Parameters<typeof listClasses>[0]),
  list_imports: (p) => listImports(p as unknown as Parameters<typeof listImports>[0]),
  list_interfaces: (p) => listInterfaces(p as unknown as Parameters<typeof listInterfaces>[0]),
  list_enums: (p) => listEnums(p as unknown as Parameters<typeof listEnums>[0]),
  list_variables: (p) => listVariables(p as unknown as Parameters<typeof listVariables>[0]),
  list_type_aliases: (p) => listTypeAliases(p as unknown as Parameters<typeof listTypeAliases>[0]),
  find_symbol: (p) => findSymbol(p as unknown as Parameters<typeof findSymbol>[0]),
  show_symbol: (p) => showSymbol(p as unknown as Parameters<typeof showSymbol>[0]),
  // Utility operations
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
