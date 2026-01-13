import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

export function useRequests(params?: {
  workflow_id?: string;
  parameter?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['requests', params],
    queryFn: () => api.getRequests(params),
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

export function useRequest(id: string | null) {
  return useQuery({
    queryKey: ['request', id],
    queryFn: () => api.getRequest(id!),
    enabled: !!id,
  });
}

export function useUnconfiguredParams() {
  return useQuery({
    queryKey: ['unconfigured-params'],
    queryFn: api.getUnconfiguredParams,
    refetchInterval: 10000,
  });
}

export function useUnconfiguredParamsMutations() {
  const queryClient = useQueryClient();

  const deleteParam = useMutation({
    mutationFn: (parameter: string) => api.deleteUnconfiguredParam(parameter),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['unconfigured-params'] });
    },
  });

  return { deleteParam };
}
