// Response types matching backend Pydantic models

export type IncidentStatus =
  | 'new'
  | 'rca'
  | 'planned'
  | 'executing'
  | 'validating'
  | 'resolved'
  | 'failed'
  | 'cancelled';

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';

export type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled';

export type SessionStatus = 'active' | 'completed' | 'cancelled';

export type AgentEventType =
  | 'agent_start'
  | 'tool_call'
  | 'tool_result'
  | 'agent_response'
  | 'error';

export type SSEEventType = AgentEventType | 'connected' | 'heartbeat';

export interface SSEEvent {
  agent_name: string;
  event_type: AgentEventType;
  timestamp: string;
  event_id?: string;
  data: Record<string, unknown>;
}

export interface IncidentResponse {
  id: string;
  session_id: string;
  title: string;
  description: string;
  container_id: string | null;
  container_name: string | null;
  status: IncidentStatus;
  severity: IncidentSeverity;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface RunResponse {
  id: string;
  incident_id: string;
  run_number: number;
  status: RunStatus;
  rca_result: Record<string, unknown> | null;
  plan_result: Record<string, unknown> | null;
  execution_result: Record<string, unknown> | null;
  validation_result: Record<string, unknown> | null;
  started_at: string;
  completed_at: string | null;
}

export interface IncidentWithRunsResponse extends IncidentResponse {
  runs: RunResponse[];
}

export interface SessionResponse {
  id: string;
  project_id: string;
  status: SessionStatus;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ConfigResponse {
  monitor_poll_interval: number;
  orchestrator_poll_interval: number;
  max_incident_retries: number;
  max_tool_iterations: number;
  codestral_deployment: string;
  gpt4o_mini_deployment: string;
  host: string;
  port: number;
}

export interface ConfigUpdateRequest {
  monitor_poll_interval?: number;
  orchestrator_poll_interval?: number;
  max_incident_retries?: number;
  max_tool_iterations?: number;
}

export interface MonitorContainerResponse {
  container_name: string;
  image: string;
  expected_status: string;
}

export interface MonitorStatusResponse {
  status: string;
  monitored_containers: number;
  active_incidents: number;
  last_check: string | null;
}

export interface CreateIncidentRequest {
  title: string;
  description: string;
  container_name?: string;
  severity?: IncidentSeverity;
}

export interface CreateSessionRequest {
  project_id?: string;
  config?: Record<string, unknown>;
}

export interface AddContainerRequest {
  container_name: string;
  image: string;
  expected_status: string;
}

export interface ApiError {
  error?: string;
  message?: string;
  details?: Record<string, unknown>;
  detail?: string;
}
