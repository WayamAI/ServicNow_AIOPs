import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getIncidents,
  getIncident,
  getIncidentReport,
  createIncident,
  cancelRun,
} from '@/api/client';
import type { CreateIncidentRequest } from '@/types/api';

export const INCIDENT_KEYS = {
  list: (sessionId: string, status?: string) =>
    ['incidents', sessionId, status] as const,
  detail: (id: string) => ['incident', id] as const,
  report: (id: string) => ['incident', id, 'report'] as const,
};

export function useIncidentsQuery(sessionId: string, status?: string) {
  return useQuery({
    queryKey: INCIDENT_KEYS.list(sessionId, status),
    queryFn: () => getIncidents(sessionId, status),
    enabled: !!sessionId,
  });
}

export function useIncidentQuery(id: string) {
  return useQuery({
    queryKey: INCIDENT_KEYS.detail(id),
    queryFn: () => getIncident(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const active = ['rca', 'planned', 'executing', 'validating'];
      return status && active.includes(status) ? 3000 : false;
    },
  });
}

export function useIncidentReportQuery(id: string) {
  return useQuery({
    queryKey: INCIDENT_KEYS.report(id),
    queryFn: () => getIncidentReport(id),
    enabled: !!id,
  });
}

export function useCreateIncidentMutation(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateIncidentRequest) =>
      createIncident(sessionId, body),
    onSuccess: () => {
      void qc.invalidateQueries({
        queryKey: ['incidents', sessionId],
      });
    },
  });
}

export function useCancelRunMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) => cancelRun(runId),
    onSuccess: (_data, _runId) => {
      void qc.invalidateQueries({ queryKey: ['incident'] });
    },
  });
}
