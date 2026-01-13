import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { ConnectionCreate, ConnectionUpdate } from '@/api/types';

export function useConnections() {
  return useQuery({
    queryKey: ['connections'],
    queryFn: api.getConnections,
  });
}

export function useConnection(id: string | undefined, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['connection', id],
    queryFn: () => api.getConnection(id!),
    enabled: !!id && options?.enabled !== false,
  });
}

export function useConnectionMutations() {
  const queryClient = useQueryClient();

  const createConnection = useMutation({
    mutationFn: (data: ConnectionCreate) => api.createConnection(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
    },
  });

  const updateConnection = useMutation({
    mutationFn: ({ id, ...data }: ConnectionUpdate & { id: string }) =>
      api.updateConnection(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
      queryClient.invalidateQueries({ queryKey: ['connection', variables.id] });
    },
  });

  const deleteConnection = useMutation({
    mutationFn: (id: string) => api.deleteConnection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
    },
  });

  const testConnection = useMutation({
    mutationFn: (id: string) => api.testConnection(id),
  });

  return { createConnection, updateConnection, deleteConnection, testConnection };
}
