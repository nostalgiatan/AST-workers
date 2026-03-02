#!/usr/bin/env node

import { program } from 'commander';
import { insertFunction } from './operations/insert.js';
import { updateFunction } from './operations/update.js';
import { deleteFunction } from './operations/delete.js';
import { insertClass } from './operations/insert.js';
import { deleteClass } from './operations/delete.js';
import { insertImport } from './operations/insert.js';
import { listFunctions, listClasses, listImports } from './operations/query.js';
import { findSymbol, showSymbol } from './operations/query.js';
import { renameSymbol } from './operations/rename.js';
import { validateSyntax, formatCode } from './utils/format.js';
import { batchOperations } from './operations/batch.js';

program
  .name('ast-ts')
  .description('TypeScript AST manipulation CLI tool')
  .version('0.1.0');

// ========== INSERT OPERATIONS ==========

program
  .command('insert-function')
  .alias('if')
  .description('Insert a function')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Function name')
  .option('-p, --params <params>', 'Parameters (e.g., "x: number, y: string = \'hello\'")')
  .option('-r, --return-type <type>', 'Return type')
  .option('-b, --body <body>', 'Function body')
  .option('-c, --class <className>', 'Class name (for methods)')
  .option('-d, --decorators <decorators>', 'Decorators (comma-separated)')
  .option('--is-async', 'Mark as async function')
  .option('--is-static', 'Mark as static method')
  .option('--is-private', 'Mark as private method')
  .option('--docstring <doc>', 'JSDoc comment')
  .option('--after <symbol>', 'Insert after this symbol')
  .option('--before <symbol>', 'Insert before this symbol')
  .action(async (options) => {
    const result = await insertFunction({
      module: options.module,
      name: options.name,
      params: options.params,
      returnType: options.returnType,
      body: options.body,
      className: options.class,
      decorators: options.decorators,
      isAsync: options.isAsync,
      isStatic: options.isStatic,
      isPrivate: options.isPrivate,
      docstring: options.docstring,
      after: options.after,
      before: options.before,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-class')
  .alias('ic')
  .description('Insert a class')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Class name')
  .option('-b, --bases <bases>', 'Base classes/extends (comma-separated)')
  .option('-i, --implements <implements>', 'Implements interfaces (comma-separated)')
  .option('-d, --decorators <decorators>', 'Decorators (comma-separated)')
  .option('--docstring <doc>', 'JSDoc comment')
  .option('--is-abstract', 'Mark as abstract class')
  .option('--after <symbol>', 'Insert after this symbol')
  .option('--before <symbol>', 'Insert before this symbol')
  .action(async (options) => {
    const result = await insertClass({
      module: options.module,
      name: options.name,
      bases: options.bases,
      implements: options.implements,
      decorators: options.decorators,
      docstring: options.docstring,
      isAbstract: options.isAbstract,
      after: options.after,
      before: options.before,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-import')
  .alias('ii')
  .description('Insert an import statement')
  .requiredOption('-m, --module <path>', 'Target module path')
  .option('-n, --name <name>', 'Import name(s)')
  .option('-f, --from <module>', 'Module to import from')
  .option('-a, --alias <alias>', 'Import alias')
  .option('--default', 'Import as default')
  .option('--type-only', 'Import as type only')
  .action(async (options) => {
    const result = await insertImport({
      module: options.module,
      name: options.name,
      fromModule: options.from,
      alias: options.alias,
      isDefault: options.default,
      isTypeOnly: options.typeOnly,
    });
    console.log(JSON.stringify(result, null, 2));
  });

// ========== UPDATE OPERATIONS ==========

program
  .command('update-function')
  .alias('uf')
  .description('Update a function')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Function name')
  .option('-c, --class <className>', 'Class name (for methods)')
  .option('-b, --body <body>', 'New function body')
  .option('-p, --params <params>', 'Replace all parameters')
  .option('--add-params <params>', 'Parameters to add')
  .option('--remove-params <params...>', 'Parameters to remove')
  .option('-r, --return-type <type>', 'New return type')
  .option('--add-decorators <decorators...>', 'Decorators to add')
  .option('--remove-decorators <decorators...>', 'Decorators to remove')
  .option('--docstring <doc>', 'New JSDoc comment')
  .action(async (options) => {
    const result = await updateFunction({
      module: options.module,
      name: options.name,
      className: options.class,
      body: options.body,
      params: options.params,
      addParams: options.addParams,
      removeParams: options.removeParams,
      returnType: options.returnType,
      addDecorators: options.addDecorators,
      removeDecorators: options.removeDecorators,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

// ========== DELETE OPERATIONS ==========

program
  .command('delete-function')
  .alias('df')
  .description('Delete a function')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Function name')
  .option('-c, --class <className>', 'Class name (for methods)')
  .action(async (options) => {
    const result = await deleteFunction({
      module: options.module,
      name: options.name,
      className: options.class,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('delete-class')
  .alias('dc')
  .description('Delete a class')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Class name')
  .action(async (options) => {
    const result = await deleteClass({
      module: options.module,
      name: options.name,
    });
    console.log(JSON.stringify(result, null, 2));
  });

// ========== QUERY OPERATIONS ==========

program
  .command('list-functions')
  .alias('lf')
  .description('List functions in a module or class')
  .requiredOption('-m, --module <path>', 'Target module path')
  .option('-c, --class <className>', 'Class name (list methods)')
  .option('--include-private', 'Include private members')
  .action(async (options) => {
    const result = await listFunctions({
      module: options.module,
      className: options.class,
      includePrivate: options.includePrivate,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('list-classes')
  .alias('lc')
  .description('List classes in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .option('--include-private', 'Include private members')
  .action(async (options) => {
    const result = await listClasses({
      module: options.module,
      includePrivate: options.includePrivate,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('list-imports')
  .alias('li')
  .description('List imports in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await listImports({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('find-symbol')
  .alias('fs')
  .description('Find a symbol in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Symbol name')
  .option('-t, --type <type>', 'Symbol type (function, class, variable)')
  .action(async (options) => {
    const result = await findSymbol({
      module: options.module,
      name: options.name,
      symbolType: options.type,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('show')
  .alias('s')
  .description('Show symbol with surrounding context')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Symbol name (supports scoped naming like "Class.method")')
  .option('-t, --type <type>', 'Symbol type (function, class, variable)')
  .action(async (options) => {
    const result = await showSymbol({
      module: options.module,
      name: options.name,
      symbolType: options.type,
    });
    console.log(JSON.stringify(result, null, 2));
  });

// ========== RENAME OPERATIONS ==========

program
  .command('rename-symbol')
  .alias('rn')
  .description('Rename a symbol')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-o, --old-name <name>', 'Current symbol name')
  .requiredOption('-n, --new-name <name>', 'New symbol name')
  .option('-t, --type <type>', 'Symbol type (function, class, variable)')
  .action(async (options) => {
    const result = await renameSymbol({
      module: options.module,
      oldName: options.oldName,
      newName: options.newName,
      symbolType: options.type,
    });
    console.log(JSON.stringify(result, null, 2));
  });

// ========== UTILITY OPERATIONS ==========

program
  .command('validate')
  .alias('v')
  .description('Validate TypeScript syntax')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await validateSyntax({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('format')
  .alias('fmt')
  .description('Format TypeScript code')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await formatCode({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('batch')
  .alias('b')
  .description('Execute multiple operations from JSON')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-j, --json <json>', 'JSON file path or inline JSON')
  .action(async (options) => {
    const result = await batchOperations({
      module: options.module,
      json: options.json,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program.parse();
