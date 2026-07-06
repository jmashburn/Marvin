export type OutputMode = "table" | "json" | "yaml" | "csv";

export type ColumnSpec<T> = Record<string, keyof T | ((row: T) => unknown)>;

function resolveValue<T>(row: T, accessor: keyof T | ((row: T) => unknown)): unknown {
  if (typeof accessor === "function") return accessor(row);
  return row?.[accessor];
}

function displayValue(value: unknown): string | number | boolean {
  if (value === undefined || value === null) return "";
  if (value instanceof Date) return value.toISOString();
  if (Array.isArray(value)) return value.length === 0 ? "" : value.map((v) => String(v)).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string") return value;
  if (typeof value === "number") return value;
  if (typeof value === "boolean") return value;
  return String(value);
}

function projectedRows<T>(rows: T[], columns: ColumnSpec<T>): Record<string, string | number | boolean>[] {
  return rows.map((row) => {
    const out: Record<string, string | number | boolean> = {};
    for (const [label, accessor] of Object.entries(columns)) {
      out[label] = displayValue(resolveValue(row, accessor));
    }
    return out;
  });
}

export function renderTable<T>(rows: T[], columns: ColumnSpec<T>): void {
  if (!rows.length) {
    console.log("No results.");
    return;
  }

  console.table(projectedRows(rows, columns));
}

export function renderJson(data: unknown): void {
  console.log(JSON.stringify(data, null, 2));
}

function yamlScalar(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  const text = String(value);
  if (text === "" || /[:#\n\r\t]|^\s|\s$|^-/.test(text)) return JSON.stringify(text);
  return text;
}

function toYaml(data: unknown, indent = 0): string {
  const pad = " ".repeat(indent);

  if (Array.isArray(data)) {
    if (data.length === 0) return "[]";
    return data
      .map((item) => {
        if (item && typeof item === "object" && !Array.isArray(item)) {
          const body = toYaml(item, indent + 2);
          return `${pad}- ${body.trimStart()}`;
        }
        return `${pad}- ${yamlScalar(item)}`;
      })
      .join("\n");
  }

  if (data && typeof data === "object") {
    const entries = Object.entries(data as Record<string, unknown>);
    if (entries.length === 0) return "{}";
    return entries
      .map(([key, value]) => {
        if (value && typeof value === "object") {
          return `${pad}${key}:\n${toYaml(value, indent + 2)}`;
        }
        return `${pad}${key}: ${yamlScalar(value)}`;
      })
      .join("\n");
  }

  return `${pad}${yamlScalar(data)}`;
}

export function renderYaml(data: unknown): void {
  console.log(toYaml(data));
}

function csvCell(value: unknown): string {
  const text = value === undefined || value === null ? "" : String(value);
  if (/[",\n\r]/.test(text)) return `"${text.replace(/"/g, '""')}"`;
  return text;
}

export function renderCsv<T>(rows: T[], columns: ColumnSpec<T>): void {
  const labels = Object.keys(columns);
  if (labels.length === 0) {
    if (rows.length === 0) return;
    const first = rows[0] as Record<string, unknown>;
    const inferred = Object.keys(first);
    console.log(inferred.map(csvCell).join(","));
    for (const row of rows as Record<string, unknown>[]) {
      console.log(inferred.map((key) => csvCell(row[key])).join(","));
    }
    return;
  }

  console.log(labels.map(csvCell).join(","));
  for (const row of projectedRows(rows, columns)) {
    console.log(labels.map((label) => csvCell(row[label])).join(","));
  }
}

export function renderObject(data: unknown): void {
  console.dir(data, { depth: 10, colors: true });
}

export function renderList<T>(rows: T[], columns: ColumnSpec<T>, mode: OutputMode): void {
  if (mode === "json") return renderJson(rows);
  if (mode === "yaml") return renderYaml(rows);
  if (mode === "csv") return renderCsv(rows, columns);
  return renderTable(rows, columns);
}

export function renderData(data: unknown, mode: OutputMode): void {
  if (mode === "json") return renderJson(data);
  if (mode === "yaml") return renderYaml(data);
  if (mode === "csv") {
    if (Array.isArray(data)) return renderCsv(data, {});
    return renderCsv([data], {});
  }

  if (Array.isArray(data)) {
    renderTable(data, {});
    return;
  }

  renderObject(data);
}
