export type TabType = "architecture" | "empty";

export interface TabItem {
  id: string;
  type: TabType;
  title: string;
  icon: string;
  closable: boolean;
}
