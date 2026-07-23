import { useCallback, useState } from "react";
import { fetchFinderList, type DirectoryEntry } from "../../../services/api";

export interface ProjectFileNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: ProjectFileNode[];
  loaded?: boolean;
  loading?: boolean;
}

function toNodes(entries: DirectoryEntry[]): ProjectFileNode[] {
  return entries.map((entry) => ({
    name: entry.name,
    path: entry.path,
    type: entry.type,
    loaded: entry.type === "directory" ? false : undefined,
  }));
}

export function useProjectFiles(rootPath: string = "") {
  const [tree, setTree] = useState<ProjectFileNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const entries = await fetchFinderList(rootPath);
      setTree(toNodes(entries));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [rootPath]);

  const expand = useCallback(async (path: string) => {
    setError(null);
    setTree((prev) => markLoading(prev, path, true));

    try {
      const entries = await fetchFinderList(path);
      setTree((prev) => setChildren(prev, path, toNodes(entries)));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setTree((prev) => markLoading(prev, path, false));
    }
  }, []);

  return { tree, loading, error, load, expand };
}

function markLoading(
  nodes: ProjectFileNode[],
  path: string,
  loading: boolean
): ProjectFileNode[] {
  return nodes.map((node) => {
    if (node.path === path) {
      return { ...node, loading };
    }
    if (node.children) {
      return { ...node, children: markLoading(node.children, path, loading) };
    }
    return node;
  });
}

function setChildren(
  nodes: ProjectFileNode[],
  path: string,
  children: ProjectFileNode[]
): ProjectFileNode[] {
  return nodes.map((node) => {
    if (node.path === path) {
      return { ...node, children, loaded: true, loading: false };
    }
    if (node.children) {
      return { ...node, children: setChildren(node.children, path, children) };
    }
    return node;
  });
}
