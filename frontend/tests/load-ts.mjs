import { readFile } from 'node:fs/promises';
import ts from 'typescript';
// Use the installed TypeScript compiler and Node's test runner; no test dependency required.
export async function loadTs(relativePath) {
  let source = await readFile(new URL(relativePath, import.meta.url), 'utf8');
  source = source.replaceAll('import.meta.env.VITE_API_BASE_URL', "'http://127.0.0.1:8000'");
  const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext } });
  return import(`data:text/javascript;base64,${Buffer.from(outputText).toString('base64')}`);
}
