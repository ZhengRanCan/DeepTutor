/**
 * Test-only resolver for the framework-neutral TypeScript adapter.
 *
 * The adapter deliberately uses extensionless TypeScript imports so it can be
 * consumed by a future OpenMAIC bundler. Node's native TypeScript runner needs
 * this small resolver when executing the files directly without a package
 * build step.
 */
export async function resolve(specifier, context, nextResolve) {
  try {
    return await nextResolve(specifier, context);
  } catch (error) {
    const hasFileExtension = /\.[a-zA-Z0-9]+(?:[?#].*)?$/.test(specifier);
    if (specifier.startsWith('.') && !hasFileExtension) {
      return nextResolve(`${specifier}.ts`, context);
    }
    throw error;
  }
}
