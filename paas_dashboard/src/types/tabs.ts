export type TabType = "architecture" | "empty" | "file";

export interface TabItem {
  id: string;
  type: TabType;
  title: string;
  icon: string;
  closable: boolean;
  path?: string;
}
