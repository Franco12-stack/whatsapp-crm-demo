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
