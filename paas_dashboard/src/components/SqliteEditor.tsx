import { useEffect, useRef, useState } from "react";
import type { BindableValue, Database, Sqlite3Static } from "@sqlite.org/sqlite-wasm";
import { ChevronLeft, ChevronRight, Database as DatabaseIcon, Play, Plus, Save, Trash2 } from "lucide-react";
import { fetchFinderWriteBinary } from "../services/api";
import { getSqlite } from "../services/sqlite";
import "./SqliteEditor.css";

interface SqliteEditorProps {
  path: string;
  buffer: ArrayBuffer;
  readOnly?: boolean;
}

type SaveState = "idle" | "saving" | "saved" | "error";
type ViewMode = "query" | "grid";

interface SchemaItem {
  name: string;
  type: string;
}

interface ColumnInfo {
  cid: number;
  name: string;
  type: string;
  notnull: number;
  dflt_value: unknown;
  pk: number;
}

interface RowData {
  id: string | number;
  isNew: boolean;
  values: Record<string, unknown>;
  original: Record<string, unknown>;
  deleted: boolean;
}

type Identity =
  | { kind: "rowid"; column: "rowid" }
  | { kind: "pk"; columns: string[] }
  | { kind: "none" };

const PAGE_SIZE = 100;

function escapeIdentifier(name: string): string {
  return name.replace(/"/g, '""');
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "NULL";
  if (value instanceof Uint8Array || value instanceof ArrayBuffer) {
    const bytes = value instanceof ArrayBuffer ? new Uint8Array(value) : value;
    return `[BLOB: ${bytes.length} bytes]`;
  }
  if (typeof value === "number" || typeof value === "bigint") return String(value);
  if (typeof value === "boolean") return value ? "1" : "0";
  return String(value);
}

function valuesEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (a === null || a === undefined) return b === null || b === undefined;
  if (b === null || b === undefined) return false;
  if (a instanceof Uint8Array && b instanceof Uint8Array) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i++) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }
  return String(a) === String(b);
}

function cellToDraft(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (value instanceof Uint8Array || value instanceof ArrayBuffer) {
    return formatCell(value);
  }
  return String(value);
}

function draftToValue(draft: string, column: ColumnInfo): unknown {
  if (draft === "") {
    const upperType = column.type.toUpperCase();
    if (upperType.includes("TEXT") || upperType.includes("CHAR") || upperType.includes("CLOB")) {
      return "";
    }
    return null;
  }
  const upperType = column.type.toUpperCase();
  if (upperType.includes("INT")) {
    const n = Number(draft);
    if (Number.isSafeInteger(n)) return n;
    return draft;
  }
  if (
    upperType.includes("REAL") ||
    upperType.includes("FLOA") ||
    upperType.includes("DOUB") ||
    upperType.includes("NUM")
  ) {
    const n = Number(draft);
    return Number.isNaN(n) ? draft : n;
  }
  return draft;
}

function getIdentity(db: Database, tableName: string, columns: ColumnInfo[]): Identity {
  const pkCols = columns.filter((c) => c.pk > 0).sort((a, b) => a.pk - b.pk);
  if (pkCols.length > 0) {
    return { kind: "pk", columns: pkCols.map((c) => c.name) };
  }
  try {
    const probe = db.prepare(
      `SELECT rowid FROM "${escapeIdentifier(tableName)}" LIMIT 0`
    );
    probe.finalize();
    return { kind: "rowid", column: "rowid" };
  } catch {
    return { kind: "none" };
  }
}

function getIdentityValues(row: RowData, identity: Identity): Record<string, unknown> {
  if (identity.kind === "rowid") {
    return { rowid: row.original["rowid"] ?? row.id };
  }
  if (identity.kind === "pk") {
    const vals: Record<string, unknown> = {};
    for (const col of identity.columns) vals[col] = row.original[col];
    return vals;
  }
  return {};
}

function buildWhere(
  identity: Exclude<Identity, { kind: "none" }>,
  values: Record<string, unknown>
): { sql: string; params: BindableValue[] } {
  const params: BindableValue[] = [];
  const parts: string[] = [];
  const cols = identity.kind === "rowid" ? ["rowid"] : identity.columns;
  for (const col of cols) {
    if (values[col] === null || values[col] === undefined) {
      parts.push(`"${escapeIdentifier(col)}" IS NULL`);
    } else {
      parts.push(`"${escapeIdentifier(col)}" = ?`);
      params.push(values[col] as BindableValue);
    }
  }
  return { sql: parts.join(" AND "), params };
}

function isBlob(value: unknown): boolean {
  return value instanceof Uint8Array || value instanceof ArrayBuffer;
}

export function SqliteEditor({ path, buffer, readOnly }: SqliteEditorProps) {
  const [tables, setTables] = useState<SchemaItem[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [columns, setColumns] = useState<string[]>([]);
  const [rows, setRows] = useState<unknown[][]>([]);

  const [currentTable, setCurrentTable] = useState<string | null>(null);
  const [currentTableType, setCurrentTableType] = useState<string>("table");
  const [schema, setSchema] = useState<ColumnInfo[]>([]);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [gridRows, setGridRows] = useState<RowData[]>([]);
  const [page, setPage] = useState(0);
  const [hasChanges, setHasChanges] = useState(false);

  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [loading, setLoading] = useState(true);

  const sqliteRef = useRef<Sqlite3Static | null>(null);
  const dbRef = useRef<Database | null>(null);
  const newRowCounter = useRef(0);

  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const sqlite = await getSqlite();
        if (!mounted) return;
        sqliteRef.current = sqlite;

        const vfsName = `/${path.replace(/\//g, "_")}`;
        sqlite.capi.sqlite3_js_posix_create_file(
          vfsName,
          new Uint8Array(buffer)
        );

        const db = new sqlite.oo1.DB(vfsName);
        dbRef.current = db;
        loadTables(db);
        setLoading(false);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      }
    }

    init();

    return () => {
      mounted = false;
      try {
        dbRef.current?.close();
      } catch {
        // ignore close errors
      }
      dbRef.current = null;
    };
  }, [path, buffer]);

  function loadTables(db: Database) {
    const stmt = db.prepare(
      "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') ORDER BY name"
    );
    const list: SchemaItem[] = [];
    while (stmt.step()) {
      const row = stmt.get([]);
      list.push({ name: String(row[0]), type: String(row[1]) });
    }
    stmt.finalize();
    setTables(list);
  }

  function loadSchema(db: Database, tableName: string): ColumnInfo[] {
    const stmt = db.prepare(
      `PRAGMA table_info("${escapeIdentifier(tableName)}")`
    );
    const cols: ColumnInfo[] = [];
    while (stmt.step()) {
      const row = stmt.get([]);
      cols.push({
        cid: row[0] as number,
        name: row[1] as string,
        type: String(row[2] ?? ""),
        notnull: row[3] as number,
        dflt_value: row[4],
        pk: row[5] as number,
      });
    }
    stmt.finalize();
    return cols;
  }

  function loadGridRows(db: Database, tableName: string, pageNum: number) {
    const cols = loadSchema(db, tableName);
    setSchema(cols);

    const id = getIdentity(db, tableName, cols);
    setIdentity(id);

    const selectCols =
      id.kind === "rowid" ? ["rowid", ...cols.map((c) => `"${escapeIdentifier(c.name)}"`)] : cols.map((c) => `"${escapeIdentifier(c.name)}"`);

    const sql = `SELECT ${selectCols.join(", ")} FROM "${escapeIdentifier(tableName)}" LIMIT ${PAGE_SIZE} OFFSET ${pageNum * PAGE_SIZE}`;
    const stmt = db.prepare(sql);
    const columnNames = stmt.getColumnNames();
    const resultRows: RowData[] = [];
    while (stmt.step()) {
      const raw = stmt.get([]);
      const values: Record<string, unknown> = {};
      const original: Record<string, unknown> = {};
      for (let i = 0; i < columnNames.length; i++) {
        original[columnNames[i]] = raw[i];
        values[columnNames[i]] = raw[i];
      }
      const rowId = id.kind === "rowid" ? (original["rowid"] as number | string) : resultRows.length;
      resultRows.push({
        id: rowId,
        isNew: false,
        values,
        original,
        deleted: false,
      });
    }
    stmt.finalize();
    setGridRows(resultRows);
  }

  function showTable(name: string) {
    if (!dbRef.current) return;
    const item = tables.find((t) => t.name === name);
    setCurrentTableType(item?.type ?? "table");
    setCurrentTable(name);
    setViewMode("grid");
    setPage(0);
    setHasChanges(false);
    setError(null);
    setColumns([]);
    setRows([]);
    setQuery(`SELECT * FROM "${escapeIdentifier(name)}" LIMIT 1000`);
    try {
      loadGridRows(dbRef.current, name, 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function changePage(delta: number) {
    if (!currentTable || !dbRef.current) return;
    const next = Math.max(0, page + delta);
    setPage(next);
    loadGridRows(dbRef.current, currentTable, next);
  }

  function runQuery(sql: string) {
    if (!dbRef.current) return;
    const db = dbRef.current;

    try {
      setError(null);
      const trimmed = sql.trim();
      if (!trimmed) return;

      setViewMode("query");
      if (/^\s*SELECT\s+/i.test(trimmed)) {
        const stmt = db.prepare(trimmed);
        const cols = stmt.getColumnNames();
        const resultRows: unknown[][] = [];
        while (stmt.step()) {
          resultRows.push(stmt.get([]));
        }
        stmt.finalize();
        setColumns(cols);
        setRows(resultRows);
      } else {
        db.exec(trimmed);
        setColumns([]);
        setRows([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function updateCell(rowId: string | number, column: string, value: unknown) {
    setGridRows((prev) =>
      prev.map((row) => {
        if (row.id !== rowId) return row;
        const nextValues = { ...row.values, [column]: value };
        return { ...row, values: nextValues };
      })
    );
    setHasChanges(true);
    setSaveState("idle");
  }

  function addRow() {
    newRowCounter.current += 1;
    const id = `__new_${newRowCounter.current}`;
    const values: Record<string, unknown> = {};
    for (const col of schema) values[col.name] = null;
    setGridRows((prev) => [
      ...prev,
      { id, isNew: true, values, original: {}, deleted: false },
    ]);
    setHasChanges(true);
    setSaveState("idle");
  }

  function deleteRow(rowId: string | number) {
    setGridRows((prev) =>
      prev
        .map((row) => (row.id === rowId ? { ...row, deleted: true } : row))
        .filter((row) => !(row.isNew && row.deleted))
    );
    setHasChanges(true);
    setSaveState("idle");
  }

  function applyChangesToDb(db: Database) {
    if (!currentTable || !identity || identity.kind === "none") return;

    db.exec("BEGIN TRANSACTION");
    try {
      for (const row of gridRows) {
        if (!row.deleted || row.isNew) continue;
        const { sql, params } = buildWhere(identity, getIdentityValues(row, identity));
        const stmt = db.prepare(
          `DELETE FROM "${escapeIdentifier(currentTable)}" WHERE ${sql}`
        );
        stmt.bind(params);
        stmt.step();
        stmt.finalize();
      }

      for (const row of gridRows) {
        if (row.isNew || row.deleted) continue;
        const changedCols = schema.filter(
          (col) => !valuesEqual(row.values[col.name], row.original[col.name])
        );
        if (changedCols.length === 0) continue;
        const setSql = changedCols
          .map((c) => `"${escapeIdentifier(c.name)}" = ?`)
          .join(", ");
        const setParams = changedCols.map((c) => (row.values[c.name] ?? null) as BindableValue);
        const { sql: whereSql, params: whereParams } = buildWhere(
          identity,
          getIdentityValues(row, identity)
        );
        const stmt = db.prepare(
          `UPDATE "${escapeIdentifier(currentTable)}" SET ${setSql} WHERE ${whereSql}`
        );
        stmt.bind([...setParams, ...whereParams]);
        stmt.step();
        stmt.finalize();
      }

      for (const row of gridRows) {
        if (!row.isNew || row.deleted) continue;
        const colsSql = schema.map((c) => `"${escapeIdentifier(c.name)}"`).join(", ");
        const placeholders = schema.map(() => "?").join(", ");
        const params = schema.map((c) => (row.values[c.name] ?? null) as BindableValue);
        const stmt = db.prepare(
          `INSERT INTO "${escapeIdentifier(currentTable)}" (${colsSql}) VALUES (${placeholders})`
        );
        stmt.bind(params);
        stmt.step();
        stmt.finalize();
      }

      db.exec("COMMIT");
    } catch (err) {
      db.exec("ROLLBACK");
      throw err;
    }
  }

  async function handleSave() {
    if (!sqliteRef.current || !dbRef.current || readOnly) return;
    setSaveState("saving");
    try {
      applyChangesToDb(dbRef.current);
      const exported = sqliteRef.current.capi.sqlite3_js_db_export(
        dbRef.current.pointer!
      );
      await fetchFinderWriteBinary(path, exported.buffer);
      setSaveState("saved");
      setHasChanges(false);
      if (currentTable) {
        loadGridRows(dbRef.current, currentTable, page);
      }
    } catch (err) {
      setSaveState("error");
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const fileName = path.split("/").pop() ?? path;
  const saveLabel = {
    idle: "",
    saving: "保存中...",
    saved: "已保存",
    error: "保存失败",
  }[saveState];

  const editable =
    !readOnly && currentTableType === "table" && identity?.kind !== "none";

  return (
    <div className="sqlite-editor">
      <div className="sqlite-editor__header">
        <nav className="sqlite-editor__breadcrumb" aria-label="breadcrumb">
          <ol>
            <li className="sqlite-editor__breadcrumb-item">
              <DatabaseIcon size={18} className="sqlite-editor__breadcrumb-icon" />
              <span className="sqlite-editor__breadcrumb-current">{fileName}</span>
            </li>
          </ol>
        </nav>
        <div className="sqlite-editor__header-actions">
          {readOnly && (
            <span className="sqlite-editor__status sqlite-editor__status--readonly">
              只读
            </span>
          )}
          {saveLabel && (
            <span className={`sqlite-editor__status sqlite-editor__status--${saveState}`}>
              {saveLabel}
            </span>
          )}
          {!readOnly && (
            <button
              type="button"
              className="sqlite-editor__save-btn"
              onClick={handleSave}
              disabled={saveState === "saving" || !hasChanges}
              title="保存"
              aria-label="保存"
            >
              <Save size={14} />
              保存
            </button>
          )}
        </div>
      </div>

      <div className="sqlite-editor__body">
        <aside className="sqlite-editor__sidebar">
          <div className="sqlite-editor__sidebar-title">
            <DatabaseIcon size={14} />
            表 / 视图
          </div>
          {loading ? (
            <div className="sqlite-editor__empty">加载中...</div>
          ) : tables.length === 0 ? (
            <div className="sqlite-editor__empty">无表</div>
          ) : (
            <ul className="sqlite-editor__table-list">
              {tables.map((item) => (
                <li key={item.name}>
                  <button
                    type="button"
                    className={`sqlite-editor__table-item${
                      currentTable === item.name
                        ? " sqlite-editor__table-item--active"
                        : ""
                    }`}
                    onClick={() => showTable(item.name)}
                    title={`${item.type}: ${item.name}`}
                  >
                    <span className="sqlite-editor__table-type">{item.type}</span>
                    <span className="sqlite-editor__table-name">{item.name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <main className="sqlite-editor__main">
          <div className="sqlite-editor__toolbar">
            <textarea
              className="sqlite-editor__query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入 SQL 查询，例如 SELECT * FROM ..."
              rows={3}
              spellCheck={false}
            />
            <button
              type="button"
              className="sqlite-editor__run-btn"
              onClick={() => runQuery(query)}
              disabled={!query.trim()}
              title="运行"
              aria-label="运行"
            >
              <Play size={14} />
              运行
            </button>
          </div>

          {viewMode === "grid" && currentTable && (
            <div className="sqlite-editor__grid-actions">
              <span className="sqlite-editor__grid-title">{currentTable}</span>
              {identity?.kind === "rowid" && (
                <span className="sqlite-editor__grid-meta">rowid</span>
              )}
              {identity?.kind === "pk" && (
                <span className="sqlite-editor__grid-meta">
                  主键: {identity.columns.join(", ")}
                </span>
              )}
              {identity?.kind === "none" && (
                <span className="sqlite-editor__grid-meta sqlite-editor__grid-meta--warning">
                  无主键/rowid，只读
                </span>
              )}
              {editable && (
                <button
                  type="button"
                  className="sqlite-editor__action-btn"
                  onClick={addRow}
                  title="添加行"
                >
                  <Plus size={14} />
                  添加行
                </button>
              )}
              <div className="sqlite-editor__spacer" />
              <button
                type="button"
                className="sqlite-editor__action-btn"
                onClick={() => changePage(-1)}
                disabled={page === 0}
                title="上一页"
              >
                <ChevronLeft size={14} />
              </button>
              <span className="sqlite-editor__grid-meta">第 {page + 1} 页</span>
              <button
                type="button"
                className="sqlite-editor__action-btn"
                onClick={() => changePage(1)}
                disabled={gridRows.length < PAGE_SIZE}
                title="下一页"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}

          {error && <div className="sqlite-editor__error">{error}</div>}

          <div className="sqlite-editor__results">
            {viewMode === "query" && rows.length === 0 && columns.length === 0 && !error && (
              <div className="sqlite-editor__empty">暂无结果</div>
            )}
            {viewMode === "query" && columns.length > 0 && (
              <div className="sqlite-editor__table-wrap">
                <table className="sqlite-editor__data-table">
                  <thead>
                    <tr>
                      {columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, idx) => (
                      <tr key={idx}>
                        {row.map((cell, cidx) => (
                          <td key={cidx} title={formatCell(cell)}>
                            {formatCell(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {viewMode === "grid" && currentTable && (
              <div className="sqlite-editor__table-wrap">
                {gridRows.length === 0 ? (
                  <div className="sqlite-editor__empty">该表暂无数据</div>
                ) : (
                  <table className="sqlite-editor__data-table sqlite-editor__data-table--editable">
                    <thead>
                      <tr>
                        {editable && <th className="sqlite-editor__row-action-col" />}
                        {schema.map((col) => (
                          <th key={col.name}>
                            {col.name}
                            {col.pk > 0 && (
                              <span className="sqlite-editor__pk-badge">PK</span>
                            )}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {gridRows.map((row) => (
                        <tr
                          key={String(row.id)}
                          className={
                            row.isNew
                              ? "sqlite-editor__row--new"
                              : row.deleted
                              ? "sqlite-editor__row--deleted"
                              : ""
                          }
                        >
                          {editable && (
                            <td className="sqlite-editor__row-action-col">
                              <button
                                type="button"
                                className="sqlite-editor__delete-btn"
                                onClick={() => deleteRow(row.id)}
                                title="删除行"
                                aria-label="删除行"
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          )}
                          {schema.map((col) => (
                            <EditableCell
                              key={col.name}
                              column={col}
                              value={row.values[col.name]}
                              readOnly={!editable || row.deleted}
                              onChange={(value) =>
                                updateCell(row.id, col.name, value)
                              }
                            />
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {viewMode === "grid" && !currentTable && !error && (
              <div className="sqlite-editor__empty">请从左侧选择一张表</div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function EditableCell({
  column,
  value,
  readOnly,
  onChange,
}: {
  column: ColumnInfo;
  value: unknown;
  readOnly: boolean;
  onChange: (value: unknown) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");

  if (readOnly || isBlob(value)) {
    return (
      <td
        className={`sqlite-editor__cell sqlite-editor__cell--readonly ${
          value === null ? "sqlite-editor__cell--null" : ""
        }`}
        title={formatCell(value)}
      >
        {formatCell(value)}
      </td>
    );
  }

  if (!editing) {
    return (
      <td
        className={`sqlite-editor__cell ${
          value === null ? "sqlite-editor__cell--null" : ""
        }`}
        onClick={() => {
          setEditing(true);
          setDraft(cellToDraft(value));
        }}
        title="点击编辑"
      >
        {formatCell(value)}
      </td>
    );
  }

  return (
    <td className="sqlite-editor__cell sqlite-editor__cell--editing">
      <input
        className="sqlite-editor__cell-input"
        value={draft}
        autoFocus
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => {
          onChange(draftToValue(draft, column));
          setEditing(false);
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            onChange(draftToValue(draft, column));
            setEditing(false);
          }
          if (e.key === "Escape") {
            setEditing(false);
          }
        }}
      />
    </td>
  );
}
