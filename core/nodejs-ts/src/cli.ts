#!/usr/bin/env node

import { program } from 'commander';
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
} from './operations/insert.js';
import { updateFunction } from './operations/update.js';
import { deleteFunction, deleteClass, deleteInterface, deleteVariable, deleteEnum, deleteTypeAlias } from './operations/delete.js';
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
} from './operations/query.js';
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
  .option('-p, --params <params>', 'Parameters (e.g., "x: number, y?: string = \'hello\'")')
  .option('-r, --return-type <type>', 'Return type')
  .option('-t, --type-params <params>', 'Type parameters (e.g., "T, U extends string")')
  .option('-b, --body <body>', 'Function body')
  .option('-c, --class <className>', 'Class name (for methods)')
  .option('--is-async', 'Mark as async function')
  .option('--is-static', 'Mark as static method')
  .option('--is-private', 'Mark as private method')
  .option('--is-protected', 'Mark as protected method')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertFunction({
      module: options.module,
      name: options.name,
      params: options.params,
      returnType: options.returnType,
      typeParams: options.typeParams,
      body: options.body,
      className: options.class,
      isAsync: options.isAsync,
      isStatic: options.isStatic,
      isPrivate: options.isPrivate,
      isProtected: options.isProtected,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-class')
  .alias('ic')
  .description('Insert a class')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Class name')
  .option('-e, --extends <bases>', 'Base class to extend')
  .option('-i, --implements <implements>', 'Implements interfaces (comma-separated)')
  .option('-t, --type-params <params>', 'Type parameters (e.g., "T, U")')
  .option('--is-abstract', 'Mark as abstract class')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertClass({
      module: options.module,
      name: options.name,
      bases: options.extends,
      implements: options.implements,
      typeParams: options.typeParams,
      isAbstract: options.isAbstract,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-interface')
  .alias('ii')
  .description('Insert an interface')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Interface name')
  .option('-e, --extends <extends>', 'Extends interfaces (comma-separated)')
  .option('--properties <properties>', 'Property definitions (e.g., "id:string, name?:string")')
  .option('-t, --type-params <params>', 'Type parameters (e.g., "T, U")')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertInterface({
      module: options.module,
      name: options.name,
      extends: options.extends,
      properties: options.properties,
      typeParams: options.typeParams,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-type-alias')
  .alias('ita')
  .description('Insert a type alias')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Type alias name')
  .requiredOption('--type <type>', 'Type definition')
  .option('-t, --type-params <params>', 'Type parameters (e.g., "T, U")')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertTypeAlias({
      module: options.module,
      name: options.name,
      type: options.type,
      typeParams: options.typeParams,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-enum')
  .alias('ie')
  .description('Insert an enum')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Enum name')
  .option('--members <members>', 'Enum members (e.g., "RED=0,GREEN=1,BLUE=2")')
  .option('--is-const', 'Mark as const enum')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertEnum({
      module: options.module,
      name: options.name,
      members: options.members,
      isConst: options.isConst,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-variable')
  .alias('iv')
  .description('Insert a variable declaration')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Variable name')
  .option('--type <type>', 'Variable type')
  .option('--initializer <value>', 'Initial value')
  .option('--is-const', 'Declare as const')
  .option('--is-let', 'Declare as let')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertVariable({
      module: options.module,
      name: options.name,
      type: options.type,
      initializer: options.initializer,
      isConst: options.isConst,
      isLet: options.isLet,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-property')
  .alias('ip')
  .description('Insert a class property')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Property name')
  .requiredOption('-c, --class <className>', 'Class name')
  .option('--type <type>', 'Property type')
  .option('--initializer <value>', 'Initial value')
  .option('--is-static', 'Mark as static')
  .option('--is-readonly', 'Mark as readonly')
  .option('--is-private', 'Mark as private')
  .option('--is-protected', 'Mark as protected')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertProperty({
      module: options.module,
      name: options.name,
      className: options.class,
      type: options.type,
      initializer: options.initializer,
      isStatic: options.isStatic,
      isReadonly: options.isReadonly,
      isPrivate: options.isPrivate,
      isProtected: options.isProtected,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-accessor')
  .alias('ia')
  .description('Insert a getter or setter')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Accessor name')
  .requiredOption('-c, --class <className>', 'Class name')
  .requiredOption('--kind <kind>', 'Accessor kind (get or set)')
  .option('--type <type>', 'Property type')
  .option('-b, --body <body>', 'Accessor body')
  .option('--is-static', 'Mark as static')
  .option('--is-private', 'Mark as private')
  .option('--is-protected', 'Mark as protected')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertAccessor({
      module: options.module,
      name: options.name,
      className: options.class,
      kind: options.kind,
      type: options.type,
      body: options.body,
      isStatic: options.isStatic,
      isPrivate: options.isPrivate,
      isProtected: options.isProtected,
      docstring: options.docstring,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-import')
  .alias('im')
  .description('Insert an import statement')
  .requiredOption('-m, --module <path>', 'Target module path')
  .option('-n, --name <name>', 'Import name(s)')
  .option('-f, --from <module>', 'Module to import from')
  .option('-a, --alias <alias>', 'Import alias')
  .option('--default', 'Import as default')
  .option('--type-only', 'Import as type only')
  .option('--namespace', 'Import as namespace (* as alias)')
  .action(async (options) => {
    const result = await insertImport({
      module: options.module,
      name: options.name,
      fromModule: options.from,
      alias: options.alias,
      isDefault: options.default,
      isTypeOnly: options.typeOnly,
      isNamespace: options.namespace,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('insert-namespace')
  .alias('ins')
  .description('Insert a namespace')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Namespace name')
  .option('-b, --body <body>', 'Namespace body')
  .option('--docstring <doc>', 'JSDoc comment')
  .action(async (options) => {
    const result = await insertNamespace({
      module: options.module,
      name: options.name,
      body: options.body,
      docstring: options.docstring,
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
  .option('-r, --return-type <type>', 'New return type')
  .option('--docstring <doc>', 'New JSDoc comment')
  .action(async (options) => {
    const result = await updateFunction({
      module: options.module,
      name: options.name,
      className: options.class,
      body: options.body,
      params: options.params,
      returnType: options.returnType,
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

program
  .command('delete-interface')
  .alias('di')
  .description('Delete an interface')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Interface name')
  .action(async (options) => {
    const result = await deleteInterface({
      module: options.module,
      name: options.name,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('delete-enum')
  .alias('de')
  .description('Delete an enum')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Enum name')
  .action(async (options) => {
    const result = await deleteEnum({
      module: options.module,
      name: options.name,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('delete-variable')
  .alias('dv')
  .description('Delete a variable')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Variable name')
  .action(async (options) => {
    const result = await deleteVariable({
      module: options.module,
      name: options.name,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('delete-type-alias')
  .alias('dta')
  .description('Delete a type alias')
  .requiredOption('-m, --module <path>', 'Target module path')
  .requiredOption('-n, --name <name>', 'Type alias name')
  .action(async (options) => {
    const result = await deleteTypeAlias({
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
  .command('list-interfaces')
  .alias('li')
  .description('List interfaces in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await listInterfaces({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('list-enums')
  .alias('le')
  .description('List enums in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await listEnums({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('list-variables')
  .alias('lv')
  .description('List variables in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await listVariables({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('list-type-aliases')
  .alias('lta')
  .description('List type aliases in a module')
  .requiredOption('-m, --module <path>', 'Target module path')
  .action(async (options) => {
    const result = await listTypeAliases({
      module: options.module,
    });
    console.log(JSON.stringify(result, null, 2));
  });

program
  .command('list-imports')
  .alias('lim')
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
  .option('-t, --type <type>', 'Symbol type (function, class, variable, interface, enum)')
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
  .option('-t, --type <type>', 'Symbol type (function, class, variable, interface, enum)')
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