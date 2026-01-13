import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type Connection,
  type OnNodesChange,
  type OnEdgesChange,
  type DefaultEdgeOptions,
  type EdgeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { nodeTypes } from '../nodes';
import { NODE_DEFINITIONS } from '../utils/nodeDefinitions';
import { DeletableEdge } from './DeletableEdge';
import type { SimulationResponse } from '@/api/types';

// Custom edge types with delete button
const edgeTypes: EdgeTypes = {
  default: DeletableEdge,
};

// Default edge options for styling and interactivity
const defaultEdgeOptions: DefaultEdgeOptions = {
  style: { strokeWidth: 2 },
  deletable: true,
};

// Check if adding an edge would create a cycle in the graph
function wouldCreateCycle(
  edges: Edge[],
  source: string,
  target: string
): boolean {
  // Build adjacency list from existing edges
  const adjacency = new Map<string, string[]>();
  for (const edge of edges) {
    if (!adjacency.has(edge.source)) {
      adjacency.set(edge.source, []);
    }
    adjacency.get(edge.source)!.push(edge.target);
  }

  // Add the proposed edge temporarily
  if (!adjacency.has(source)) {
    adjacency.set(source, []);
  }
  adjacency.get(source)!.push(target);

  // DFS to detect if there's a path from target back to source (cycle)
  const visited = new Set<string>();
  const stack = [target];

  while (stack.length > 0) {
    const current = stack.pop()!;
    if (current === source) {
      return true; // Found a cycle
    }
    if (visited.has(current)) {
      continue;
    }
    visited.add(current);
    const neighbors = adjacency.get(current) || [];
    for (const neighbor of neighbors) {
      stack.push(neighbor);
    }
  }

  return false;
}

interface WorkflowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onAddNode: (node: Node) => void;
  onAddEdge: (edge: Edge) => void;
  onNodeSelect: (nodeId: string | null) => void;
  selectedNodeId: string | null;
  workflowId?: string;
  simulationResult?: SimulationResponse | null;
}

// Inner component that can use useReactFlow hook
function WorkflowCanvasInner({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onAddNode,
  onAddEdge,
  onNodeSelect,
  selectedNodeId,
  simulationResult,
}: WorkflowCanvasProps) {
  const { screenToFlowPosition } = useReactFlow();

  // Build execution status map from simulation result
  const executionStatusMap = useMemo(() => {
    if (!simulationResult) return {};
    const map: Record<string, {
      executed: boolean;
      execution_order: number | null;
      output_port: string | null;
      error: string | null;
    }> = {};
    for (const record of simulationResult.execution_trace) {
      map[record.node_id] = {
        executed: record.executed,
        execution_order: record.execution_order,
        output_port: record.output_port,
        error: record.error,
      };
    }
    return map;
  }, [simulationResult]);

  // Validate connections: prevent self-loops, multiple connections, and cycles
  const isValidConnection = useCallback(
    (connection: Edge | Connection) => {
      const source = connection.source;
      const target = connection.target;

      // Need both source and target
      if (!source || !target) {
        return false;
      }

      // Prevent self-loops (connecting a node to itself)
      if (source === target) {
        return false;
      }

      // Prevent multiple connections from the same source handle
      const sourceHandle = connection.sourceHandle || 'default';
      const existingFromSource = edges.find(
        (edge) =>
          edge.source === source &&
          (edge.sourceHandle || 'default') === sourceHandle
      );

      if (existingFromSource) {
        return false;
      }

      // Prevent multiple connections to the same input handle
      const targetHandle = connection.targetHandle || 'default';
      const existingToTarget = edges.find(
        (edge) =>
          edge.target === target &&
          (edge.targetHandle || 'default') === targetHandle
      );

      if (existingToTarget) {
        return false;
      }

      // Prevent cycles (A->B->C->A)
      if (wouldCreateCycle(edges, source, target)) {
        return false;
      }

      return true;
    },
    [edges]
  );

  // Handle new connections
  const handleConnect = useCallback(
    (connection: Connection) => {
      const newEdge: Edge = {
        id: `e-${connection.source}-${connection.sourceHandle || 'default'}-${connection.target}`,
        source: connection.source!,
        target: connection.target!,
        sourceHandle: connection.sourceHandle || null,
        targetHandle: connection.targetHandle || null,
      };
      onAddEdge(newEdge);
    },
    [onAddEdge]
  );

  // Handle node selection
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeSelect(node.id);
    },
    [onNodeSelect]
  );

  const handlePaneClick = useCallback(() => {
    onNodeSelect(null);
  }, [onNodeSelect]);

  // Handle drag and drop
  const handleDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type || !NODE_DEFINITIONS[type]) return;

      // Convert screen coordinates to flow coordinates (accounts for pan/zoom)
      // Then offset by half the node size to center it under the cursor
      const flowPosition = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const position = {
        x: flowPosition.x - 70, // Half of min-w-[140px]
        y: flowPosition.y - 25, // Approx half of node height
      };

      const newNode: Node = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: {},
      };

      onAddNode(newNode);
    },
    [onAddNode, screenToFlowPosition]
  );

  // Mark selected node and add execution status to node data
  const nodesWithSelection = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        selected: node.id === selectedNodeId,
        data: {
          ...node.data,
          executionStatus: executionStatusMap[node.id],
        },
      })),
    [nodes, selectedNodeId, executionStatusMap]
  );

  // Add selection state to edges for visual feedback
  const edgesWithDefaults = useMemo(
    () =>
      edges.map((edge) => ({
        ...edge,
        style: { strokeWidth: 2 },
      })),
    [edges]
  );

  return (
    <ReactFlow
      nodes={nodesWithSelection}
      edges={edgesWithDefaults}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={handleConnect}
      onNodeClick={handleNodeClick}
      onPaneClick={handlePaneClick}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      isValidConnection={isValidConnection}
      defaultEdgeOptions={defaultEdgeOptions}
      fitView
      snapToGrid
      snapGrid={[15, 15]}
      deleteKeyCode={['Backspace', 'Delete']}
    >
      <Background gap={15} size={1} />
      <Controls />
      <MiniMap
        nodeColor={(node) => {
          const def = NODE_DEFINITIONS[node.type || ''];
          return def?.color || '#gray';
        }}
      />
    </ReactFlow>
  );
}

// Cache-buster version - increment when node component structure changes
const NODE_VERSION = 'v2';

// Wrapper that provides ReactFlowProvider context
// Key forces re-mount when workflow changes, ensuring clean state
export function WorkflowCanvas({ workflowId, simulationResult, ...props }: WorkflowCanvasProps) {
  return (
    <div className="flex-1 h-full">
      <ReactFlowProvider key={`${NODE_VERSION}-${workflowId || 'new'}`}>
        <WorkflowCanvasInner simulationResult={simulationResult} {...props} />
      </ReactFlowProvider>
    </div>
  );
}
