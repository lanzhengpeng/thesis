import type { Sqlite3Static } from "@sqlite.org/sqlite-wasm";

let sqlitePromise: Promise<Sqlite3Static> | null = null;

export async function getSqlite(): Promise<Sqlite3Static> {
  if (!sqlitePromise) {
    const { default: sqlite3InitModule } = await import("@sqlite.org/sqlite-wasm");
    sqlitePromise = sqlite3InitModule();
  }
  return sqlitePromise;
}
