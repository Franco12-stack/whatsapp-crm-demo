import { api } from "./client";
import type {
  AgentStatusOut, AiSuggestOut, AlertOut, AppointmentOut, BroadcastRunOut, CallLogOut,
  ConversationOut, EstadoTicket, GoalOut, LineOut, MessageOut, MetricsOut, ProductOut,
  PromotionOut, SupportTicketOut, UserOut,
} from "../types";

export const auth = {
  login: (email: string, password: string) => api.login(email, password),
};

export const conversations = {
  list: () => api.get<ConversationOut[]>("/conversations"),
  followUps: () => api.get<ConversationOut[]>("/conversations/follow-ups"),
  messages: (id: string) => api.get<MessageOut[]>(`/conversations/${id}/messages`),
  send: (id: string, body: string) =>
    api.post<MessageOut>(`/conversations/${id}/messages`, { body }),
  calls: (id: string) => api.get<CallLogOut[]>(`/conversations/${id}/calls`),
  logCall: (id: string) => api.post<CallLogOut>(`/conversations/${id}/calls`),
  reassign: (id: string, lineId: string) =>
    api.patch<ConversationOut>(`/conversations/${id}/reassign`, { line_id: lineId }),
};

export const broadcasts = {
  send: (conversation_ids: string[], body: string, force = false) =>
    api.post<{ sent_to: string[]; skipped_cold: { contact_name: string; phone_number: string }[] }>(
      "/broadcasts",
      { conversation_ids, body, force },
    ),
  history: () => api.get<BroadcastRunOut[]>("/broadcasts"),
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

export const support = {
  list: () => api.get<SupportTicketOut[]>("/support"),
  create: (title: string, description: string, priority: string) =>
    api.post<SupportTicketOut>("/support", { title, description, priority }),
  update: (id: string, state: EstadoTicket, admin_note?: string) =>
    api.patch<SupportTicketOut>(`/support/${id}`, { state, admin_note }),
};

export const metrics = {
  mine: () => api.get<MetricsOut>("/metrics/me"),
  team: () => api.get<MetricsOut>("/metrics/team"),
};

export const appointments = {
  list: () => api.get<AppointmentOut[]>("/appointments"),
  create: (contact_id: string, title: string, scheduled_at: string) =>
    api.post<AppointmentOut>("/appointments", { contact_id, title, scheduled_at }),
  markDone: (id: string) => api.post<AppointmentOut>(`/appointments/${id}/done`),
};

export const goals = {
  list: () => api.get<GoalOut[]>("/goals"),
  set: (agentId: string, target_messages_month: number, target_conversations_month: number) =>
    api.put<GoalOut>(`/goals/${agentId}`, { target_messages_month, target_conversations_month }),
};

export const promotions = {
  list: () => api.get<PromotionOut[]>("/promotions"),
  create: (title: string, body: string) => api.post<PromotionOut>("/promotions", { title, body, active: true }),
};

export const products = {
  list: () => api.get<ProductOut[]>("/products"),
  create: (name: string, price_cents: number, stock: number) =>
    api.post<ProductOut>("/products", { name, price_cents, stock }),
};

export const ai = {
  suggest: (conversation_id: string) =>
    api.post<AiSuggestOut>("/ai/suggest", { conversation_id }),
};

export type { UserOut };
