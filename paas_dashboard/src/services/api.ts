import type { CheatSheetResponse } from "../types/cheatSheet";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchCheatSheet(): Promise<CheatSheetResponse> {
  const response = await fetch(`${BASE_URL}/admin/kernel/cheat-sheet`, {
    method: "GET",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<CheatSheetResponse>;
}

export interface DirectoryEntry {
  name: string;
  type: "file" | "directory";
  path: string;
  size?: number;
}

export async function fetchFinderList(path: string = ""): Promise<DirectoryEntry[]> {
  const response = await fetch(
    `${BASE_URL}/admin/finder/list?path=${encodeURIComponent(path)}`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<DirectoryEntry[]>;
}

export async function fetchFinderRead(path: string): Promise<string> {
  const response = await fetch(
    `${BASE_URL}/admin/finder/read?path=${encodeURIComponent(path)}`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  const data = await response.json();
  return data.content as string;
}

export async function fetchFinderWrite(
  path: string,
  content: string,
  encoding: string = "utf-8",
  overwrite: boolean = true
): Promise<{ path: string; message: string }> {
  const response = await fetch(`${BASE_URL}/admin/finder/write`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content, encoding, overwrite }),
  });
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<{ path: string; message: string }>;
}

export async function fetchModuleFiles(plugin: string): Promise<string[]> {
  const response = await fetch(
    `${BASE_URL}/admin/kernel/modules/${encodeURIComponent(plugin)}/files`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  const data = await response.json();
  return data.files as string[];
}

export async function fetchModuleFile(
  plugin: string,
  file: string
): Promise<string> {
  const response = await fetch(
    `${BASE_URL}/admin/kernel/modules/${encodeURIComponent(
      plugin
    )}/files/${encodeURIComponent(file)}`,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  const data = await response.json();
  return data.content as string;
}

export async function updateModuleFile(
  plugin: string,
  file: string,
  content: string
): Promise<{ check: Record<string, any>; reload_report: Record<string, any> }> {
  const response = await fetch(
    `${BASE_URL}/admin/kernel/modules/${encodeURIComponent(
      plugin
    )}/files/${encodeURIComponent(file)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function deleteModule(plugin: string): Promise<void> {
  const response = await fetch(
    `${BASE_URL}/admin/kernel/modules/${encodeURIComponent(plugin)}`,
    {
      method: "DELETE",
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
}

export async function reloadModule(plugin: string): Promise<void> {
  const response = await fetch(
    `${BASE_URL}/admin/kernel/reload/${encodeURIComponent(plugin)}`,
    {
      method: "POST",
    }
  );
  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }
}
