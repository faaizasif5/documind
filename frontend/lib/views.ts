import { FileText, MessageSquare, type LucideIcon } from "lucide-react";

export type AppView = "chat" | "documents";

export interface AppViewItem {
  id: AppView;
  label: string;
  icon: LucideIcon;
}

export const APP_VIEWS: readonly AppViewItem[] = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "documents", label: "Documents", icon: FileText },
];
