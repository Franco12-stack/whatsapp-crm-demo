import { api } from "./client";
import type {
  AgentStatusOut, AlertOut, ConversationOut, LineOut, MessageOut, UserOut,
} from "../types";

export const auth = {
  login: (email: string, password: string) => api.login(email, password),
};

export const conversations = {
  list: () => api.get<ConversationOut[]>("/conversations"),
  messages: (id: string) => api.get<MessageOut[]>(`/conversations/${id}/messages`),
  send: (id: string, body: string) =>
    api.post<MessageOut>(`/conversations/${id}/messages`, { body }),
};

export const broadcasts = {
  send: (conversation_ids: string[], body: string, force = false) =>
    api.post<{ sent_to: string[]; skipped_cold: { contact_name: string; phone_number: string }[] }>(
      "/broadcasts",
      { conversation_ids, body, force },
    ),
};

export const dashboard = {
  agents: () => api.get<AgentStatusOut[]>("/dashboard/agents"),
  alerts: () => api.get<AlertOut[]>("/dashboard/alerts"),
  ackAlert: (id: string) => api.post<AlertOut>(`/dashboard/alerts/${id}/ack`),
};

export const admin = {
  lines: () => api.get<LineOut[]>("/admin/lines"),
  updatePolicy: (id: string, policy: { policy_daily: number; policy_hourly: number; policy_new_chats_daily: number }) =>
    api.patch<LineOut>(`/admin/lines/${id}/policy`, policy),
  resetWarmup: (id: string) => api.post<LineOut>(`/admin/lines/${id}/reset-warmup`),
};

export type { UserOut };
