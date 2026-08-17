import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSessions, getSession, createSession } from '@/api/client';
import type { CreateSessionRequest } from '@/types/api';

export const SESSION_KEYS = {
  all: ['sessions'] as const,
  detail: (id: string) => ['sessions', id] as const,
};

export function useSessionsQuery() {
  return useQuery({
    queryKey: SESSION_KEYS.all,
    queryFn: getSessions,
  });
}

export function useSessionQuery(id: string) {
  return useQuery({
    queryKey: SESSION_KEYS.detail(id),
    queryFn: () => getSession(id),
    enabled: !!id,
  });
}

export function useActiveSession() {
  const { data: sessions } = useSessionsQuery();
  return sessions?.find((s) => s.status === 'active') ?? null;
}

export function useCreateSessionMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body?: CreateSessionRequest) => createSession(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SESSION_KEYS.all });
    },
  });
}
