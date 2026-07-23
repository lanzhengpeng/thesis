const SQLITE_EXTENSIONS = new Set([
  "sqlite",
  "sqlite3",
  "db",
  "db3",
  "s3db",
  "sl3",
]);

export function isSqliteFile(path: string): boolean {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return SQLITE_EXTENSIONS.has(ext);
}

export function getFileExtension(path: string): string {
  return path.split(".").pop()?.toLowerCase() ?? "";
}
