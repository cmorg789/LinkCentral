import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { TestFixtureCreate } from '@/api/types';

/**
 * Hook to fetch all test fixtures for a workflow.
 */
export function useTestFixtures(workflowId: string | undefined) {
  return useQuery({
    queryKey: ['testFixtures', workflowId],
    queryFn: async () => {
      if (!workflowId || workflowId === 'new') return [];
      return await api.getTestFixtures(workflowId);
    },
    enabled: !!workflowId && workflowId !== 'new',
  });
}

/**
 * Hook to get mutation functions for test fixture CRUD operations.
 */
export function useTestFixtureMutations(workflowId: string | undefined) {
  const queryClient = useQueryClient();

  const invalidateFixtures = () => {
    if (workflowId) {
      queryClient.invalidateQueries({ queryKey: ['testFixtures', workflowId] });
    }
  };

  const createFixture = useMutation({
    mutationFn: async (data: TestFixtureCreate) => {
      if (!workflowId) throw new Error('No workflow ID');
      return await api.createTestFixture(workflowId, data);
    },
    onSuccess: invalidateFixtures,
  });

  const createFromRequest = useMutation({
    mutationFn: async ({ requestId, name }: { requestId: string; name: string }) => {
      if (!workflowId) throw new Error('No workflow ID');
      return await api.createFixtureFromRequest(workflowId, requestId, name);
    },
    onSuccess: invalidateFixtures,
  });

  const updateFixture = useMutation({
    mutationFn: async ({ fixtureId, data }: { fixtureId: string; data: TestFixtureCreate }) => {
      if (!workflowId) throw new Error('No workflow ID');
      return await api.updateTestFixture(workflowId, fixtureId, data);
    },
    onSuccess: invalidateFixtures,
  });

  const deleteFixture = useMutation({
    mutationFn: async (fixtureId: string) => {
      if (!workflowId) throw new Error('No workflow ID');
      return await api.deleteTestFixture(workflowId, fixtureId);
    },
    onSuccess: invalidateFixtures,
  });

  return {
    createFixture,
    createFromRequest,
    updateFixture,
    deleteFixture,
  };
}
