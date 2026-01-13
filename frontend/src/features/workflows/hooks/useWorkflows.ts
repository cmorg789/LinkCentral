import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { WorkflowCreate, WorkflowUpdate } from '@/api/types';

export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: api.getWorkflows,
  });
}

export function useWorkflow(id: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['workflow', id],
    queryFn: () => api.getWorkflow(id!),
    enabled: !!id && options?.enabled !== false,
  });
}

export function useWorkflowMutations() {
  const queryClient = useQueryClient();

  const createWorkflow = useMutation({
    mutationFn: (data: WorkflowCreate) => api.createWorkflow(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  const updateWorkflow = useMutation({
    mutationFn: ({ id, ...data }: WorkflowUpdate & { id: string }) =>
      api.updateWorkflow(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow', variables.id] });
    },
  });

  const deleteWorkflow = useMutation({
    mutationFn: (id: string) => api.deleteWorkflow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
    },
  });

  return { createWorkflow, updateWorkflow, deleteWorkflow };
}
