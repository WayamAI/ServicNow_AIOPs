import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getMonitorContainers,
  getMonitorStatus,
  addMonitorContainer,
  removeMonitorContainer,
} from '@/api/client';
import type { AddContainerRequest } from '@/types/api';
import { toast } from 'sonner';

export const MONITOR_KEYS = {
  containers: ['monitor', 'containers'] as const,
  status: ['monitor', 'status'] as const,
};

export function useMonitorContainersQuery() {
  return useQuery({
    queryKey: MONITOR_KEYS.containers,
    queryFn: getMonitorContainers,
  });
}

export function useMonitorStatusQuery() {
  return useQuery({
    queryKey: MONITOR_KEYS.status,
    queryFn: getMonitorStatus,
    refetchInterval: 10_000,
  });
}

export function useAddContainerMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AddContainerRequest) => addMonitorContainer(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MONITOR_KEYS.containers });
      toast.success('Container added to monitoring');
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}

export function useRemoveContainerMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => removeMonitorContainer(name),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: MONITOR_KEYS.containers });
      toast.success('Container removed from monitoring');
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}
