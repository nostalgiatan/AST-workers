// Insert operations
export {
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
} from './operations/insert.js';

// Update operations
export { updateFunction } from './operations/update.js';

// Delete operations
export {
  deleteFunction,
  deleteClass,
  deleteInterface,
  deleteEnum,
  deleteVariable,
  deleteTypeAlias,
} from './operations/delete.js';

// Query operations
export {
  listFunctions,
  listClasses,
  listInterfaces,
  listEnums,
  listVariables,
  listTypeAliases,
  listImports,
  findSymbol,
  showSymbol,
} from './operations/query.js';

// Rename operations
export { renameSymbol } from './operations/rename.js';

// Batch operations
export { batchOperations } from './operations/batch.js';

// Utility operations
export { validateSyntax, formatCode } from './utils/format.js';
