import type { CheatSheetResponse } from "../types/cheatSheet";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchCheatSheet(): Promise<CheatSheetResponse> {
  const response = await fetch(`${BASE_URL}/admin/kernel/cheat-sheet`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`请求失败：${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<CheatSheetResponse>;
}
