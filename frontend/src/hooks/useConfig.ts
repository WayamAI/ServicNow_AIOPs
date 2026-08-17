import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConfig, updateConfig } from '@/api/client';
import type { ConfigUpdateRequest } from '@/types/api';
import { toast } from 'sonner';

export const CONFIG_KEYS = {
  all: ['config'] as const,
};

export function useConfigQuery() {
  return useQuery({
    queryKey: CONFIG_KEYS.all,
    queryFn: getConfig,
  });
}

export function useUpdateConfigMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ConfigUpdateRequest) => updateConfig(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CONFIG_KEYS.all });
      toast.success('Configuration saved');
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}
