export type Role = "admin" | "supervisor" | "agent";

export interface UserOut {
  id: string;
  full_name: string;
  email: string;
  role: Role;
}

export interface ContactOut {
  id: string;
  name: string;
  phone_number: string;
  crm_account: string | null;
  lifetime_value: number;
  last_order_at: string | null;
}

export interface ConversationOut {
  id: string;
  contact: ContactOut;
  line_id: string;
  is_warm: boolean;
  last_message_at: string;
}

export interface MessageOut {
  id: string;
  direction: "inbound" | "outbound";
  body: string;
  sent_by_user_id: string | null;
  sent_at: string;
}

export interface LineOut {
  id: string;
  phone_number: string;
  label: string;
  status: string;
  agent_id: string | null;
  policy_daily: number;
  policy_hourly: number;
  policy_new_chats_daily: number;
  warmup_started_at: string;
  usage_percent: number;
  effective_daily_limit: number;
  days_connected: number;
}

export interface AlertOut {
  id: string;
  kind: string;
  title: string;
  detail: string | null;
  acknowledged: boolean;
  created_at: string;
}

export interface AgentStatusOut {
  user: UserOut;
  line: LineOut | null;
  open_conversations: number;
  messages_today: number;
}

export interface BroadcastSkipped {
  conversation_id: string;
  contact_name: string;
  phone_number: string;
}

export interface BroadcastRunOut {
  id: string;
  body: string;
  sent_by: UserOut;
  sent_count: number;
  skipped_cold_count: number;
  forced: boolean;
  created_at: string;
}

export interface CallLogOut {
  id: string;
  duration_seconds: number;
  created_at: string;
}

export type EstadoTicket = "open" | "in_progress" | "resolved";
export type PrioridadTicket = "low" | "medium" | "high" | "urgent";

export interface SupportTicketOut {
  id: string;
  title: string;
  description: string;
  priority: PrioridadTicket;
  state: EstadoTicket;
  reported_by: UserOut;
  admin_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppointmentOut {
  id: string;
  contact: ContactOut;
  title: string;
  scheduled_at: string;
  done: boolean;
}

export interface GoalOut {
  id: string;
  agent_id: string;
  target_messages_month: number;
  target_conversations_month: number;
  progress_messages: number;
  progress_conversations: number;
}

export interface PromotionOut {
  id: string;
  title: string;
  body: string;
  active: boolean;
}

export interface ProductOut {
  id: string;
  name: string;
  price_cents: number;
  stock: number;
}

export interface MetricsOut {
  messages_today: number;
  messages_this_week: number;
  messages_this_month: number;
  conversations_total: number;
  conversations_warm: number;
  conversations_cold: number;
  calls_logged: number;
  broadcasts_sent: number;
  tickets_open: number;
}

export interface AiSuggestOut {
  suggestion: string;
  note: string;
}
