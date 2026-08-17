import type {
  IncidentResponse,
  IncidentWithRunsResponse,
  RunResponse,
  SessionResponse,
  ConfigResponse,
  ConfigUpdateRequest,
  MonitorContainerResponse,
  MonitorStatusResponse,
  CreateIncidentRequest,
  CreateSessionRequest,
  AddContainerRequest,
  ApiError,
} from '@/types/api';

const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    let errorBody: ApiError = {};
    try {
      errorBody = (await res.json()) as ApiError;
    } catch {
      // ignore parse error
    }
    const message = errorBody.message ?? errorBody.detail ?? `HTTP ${res.status}`;
    throw new Error(message);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// Sessions
export const getSessions = () => request<SessionResponse[]>('/sessions');
export const getSession = (id: string) =>
  request<SessionResponse>(`/sessions/${id}`);
export const createSession = (body?: CreateSessionRequest) =>
  request<SessionResponse>('/sessions', {
    method: 'POST',
    body: JSON.stringify(body ?? {}),
  });
export const updateSession = (
  id: string,
  body: Partial<Pick<SessionResponse, 'status' | 'config'>>
) =>
  request<SessionResponse>(`/sessions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
export const deleteSession = (id: string) =>
  request<void>(`/sessions/${id}`, { method: 'DELETE' });

// Incidents
export const getIncidents = (sessionId: string, status?: string) =>
  request<IncidentResponse[]>(
    `/sessions/${sessionId}/incidents${status ? `?status=${status}` : ''}`
  );
export const getIncident = (id: string) =>
  request<IncidentWithRunsResponse>(`/incidents/${id}`);
export const createIncident = (sessionId: string, body: CreateIncidentRequest) =>
  request<IncidentResponse>(`/sessions/${sessionId}/incidents`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
export const getIncidentReport = (id: string) =>
  request<{ report: string; incident_id: string }>(`/incidents/${id}/report`);

// Runs
export const cancelRun = (runId: string) =>
  request<RunResponse>(`/runs/${runId}/cancel`, { method: 'POST' });

// Config
export const getConfig = () => request<ConfigResponse>('/config');
export const updateConfig = (body: ConfigUpdateRequest) =>
  request<ConfigResponse>('/config', {
    method: 'PATCH',
    body: JSON.stringify(body),
  });

// Monitor
export const getMonitorContainers = () =>
  request<MonitorContainerResponse[]>('/monitor/containers');
export const getMonitorStatus = () =>
  request<MonitorStatusResponse>('/monitor/status');
export const addMonitorContainer = (body: AddContainerRequest) =>
  request<MonitorContainerResponse>('/monitor/containers', {
    method: 'POST',
    body: JSON.stringify(body),
  });
export const removeMonitorContainer = (name: string) =>
  request<void>(`/monitor/containers/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });

// Health
export const getHealth = () =>
  request<{ status: string; version: string }>('/health');
