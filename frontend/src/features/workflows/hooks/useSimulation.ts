import { useState, useEffect, useCallback } from 'react';
import type { Node, Edge } from '@xyflow/react';
import { api } from '@/api/client';
import type { SimulationResponse } from '@/api/types';
import { useDebounce } from '@/hooks/useDebounce';

const DEBOUNCE_DELAY = 800; // ms

interface UseSimulationOptions {
  workflowId: string | undefined;
  fixtureId: string | null;
  nodes: Node[];
  edges: Edge[];
  enabled: boolean;
}

interface UseSimulationResult {
  result: SimulationResponse | null;
  isSimulating: boolean;
  error: string | null;
  runSimulation: () => Promise<void>;
}

/**
 * Hook to manage workflow simulation with debounced auto-execution.
 *
 * When enabled and a fixture is selected, the simulation will automatically
 * re-run 800ms after the last change to nodes or edges.
 */
export function useSimulation({
  workflowId,
  fixtureId,
  nodes,
  edges,
  enabled,
}: UseSimulationOptions): UseSimulationResult {
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce the nodes and edges to prevent excessive API calls
  const debouncedNodes = useDebounce(nodes, DEBOUNCE_DELAY);
  const debouncedEdges = useDebounce(edges, DEBOUNCE_DELAY);

  // Serialize nodes/edges for comparison (only essential fields)
  const nodesJson = JSON.stringify(
    debouncedNodes.map((n) => ({
      id: n.id,
      type: n.type,
      position: n.position,
      data: n.data || {},
    }))
  );

  const edgesJson = JSON.stringify(debouncedEdges);

  const runSimulation = useCallback(async () => {
    if (!workflowId || workflowId === 'new' || !fixtureId) {
      return;
    }

    setIsSimulating(true);
    setError(null);

    try {
      const response = await api.simulateWorkflow(workflowId, {
        fixture_id: fixtureId,
        nodes: nodesJson,
        edges: edgesJson,
      });
      setResult(response);
      if (!response.success && response.error) {
        setError(response.error);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Simulation failed';
      setError(errorMessage);
      setResult(null);
    } finally {
      setIsSimulating(false);
    }
  }, [workflowId, fixtureId, nodesJson, edgesJson]);

  // Auto-run simulation when enabled and all conditions are met
  useEffect(() => {
    if (enabled && fixtureId && workflowId && workflowId !== 'new') {
      runSimulation();
    }
  }, [enabled, fixtureId, workflowId, nodesJson, edgesJson, runSimulation]);

  // Clear results when simulation is disabled or fixture is deselected
  useEffect(() => {
    if (!enabled || !fixtureId) {
      setResult(null);
      setError(null);
    }
  }, [enabled, fixtureId]);

  return {
    result,
    isSimulating,
    error,
    runSimulation,
  };
}
