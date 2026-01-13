import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useNodesState, useEdgesState, type Node, type Edge } from '@xyflow/react';

import { useWorkflow, useWorkflowMutations } from './hooks/useWorkflows';
import { useSimulation } from './hooks/useSimulation';
import { useTestFixtures, useTestFixtureMutations } from './hooks/useTestFixtures';
import { WorkflowCanvas } from './components/WorkflowCanvas';
import { PropertyPanel } from './components/PropertyPanel';
import { SimulationBottomPanel } from './components/SimulationBottomPanel';
import { FloatingVariablesWidget } from './components/FloatingVariablesWidget';
import { NodePalette } from './components/NodePalette';
import { WorkflowToolbar } from './components/WorkflowToolbar';
import { Spinner } from '@/components/ui/Spinner';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

// Default nodes for a new workflow
const DEFAULT_NODES: Node[] = [
  {
    id: 'start-1',
    type: 'start',
    position: { x: 100, y: 200 },
    data: {},
  },
  {
    id: 'end-1',
    type: 'end',
    position: { x: 500, y: 200 },
    data: {},
  },
];

const DEFAULT_EDGES: Edge[] = [];

export function WorkflowEditorPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = id === 'new';

  const { data: workflow, isLoading } = useWorkflow(id, { enabled: !isNew });
  const { createWorkflow, updateWorkflow } = useWorkflowMutations();

  // Local state for canvas - using React Flow's built-in hooks
  const [nodes, setNodes, onNodesChange] = useNodesState(DEFAULT_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(DEFAULT_EDGES);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Simulation state
  const [simulationMode, setSimulationMode] = useState(false);
  const [selectedFixtureId, setSelectedFixtureId] = useState<string | null>(null);
  const [showVariables, setShowVariables] = useState(true);

  // Create fixture modal state
  const [showCreateFixtureModal, setShowCreateFixtureModal] = useState(false);
  const [newFixtureName, setNewFixtureName] = useState('');
  const [newFixtureJson, setNewFixtureJson] = useState('{\n  "EntityID": "",\n  "Forms": []\n}');

  // Fixtures
  const { data: fixtures, isLoading: isLoadingFixtures } = useTestFixtures(id);
  const { createFixture } = useTestFixtureMutations(id);

  // Simulation hook
  const simulation = useSimulation({
    workflowId: id,
    fixtureId: selectedFixtureId,
    nodes,
    edges,
    enabled: simulationMode,
  });

  // Load workflow data when available
  useEffect(() => {
    if (workflow) {
      console.log('Loading workflow from API:', {
        id: workflow.id,
        name: workflow.name,
        nodesRaw: workflow.nodes,
        edgesRaw: workflow.edges
      });
      try {
        const rawNodes = JSON.parse(workflow.nodes || '[]');
        const loadedEdges = JSON.parse(workflow.edges || '[]');

        // Strip internal React Flow properties (measured, selected, dragging, etc.)
        // These are added by React Flow and can cause issues when reloaded
        const loadedNodes = rawNodes.map((node: Node) => ({
          id: node.id,
          type: node.type,
          position: node.position,
          data: node.data || {},
        }));

        console.log('Parsed nodes:', loadedNodes.length, 'Parsed edges:', loadedEdges.length);
        console.log('Loaded nodes with data:', loadedNodes);
        setNodes(loadedNodes.length > 0 ? loadedNodes : DEFAULT_NODES);
        setEdges(loadedEdges);
      } catch (e) {
        console.error('Failed to parse workflow:', e);
        setNodes(DEFAULT_NODES);
        setEdges(DEFAULT_EDGES);
      }
    }
  }, [workflow]);

  const handleDragStart = useCallback(
    (event: React.DragEvent, nodeType: string) => {
      event.dataTransfer.setData('application/reactflow', nodeType);
      event.dataTransfer.effectAllowed = 'move';
    },
    []
  );

  const handleUpdateNodeData = useCallback(
    (nodeId: string, data: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId ? { ...node, data } : node
        )
      );
    },
    []
  );

  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes(nds => nds.filter((node) => node.id !== nodeId));
      // Also remove any edges connected to this node
      setEdges(eds => eds.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      ));
      setSelectedNodeId(null);
    },
    [setNodes, setEdges]
  );

  const handleSave = async (name: string, parameter: string) => {
    // Strip internal React Flow properties before saving
    const cleanNodes = nodes.map((node) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data || {},
    }));

    const nodesJson = JSON.stringify(cleanNodes);
    const edgesJson = JSON.stringify(edges);

    console.log('Saving workflow:', { name, parameter, nodeCount: cleanNodes.length, edgeCount: edges.length });
    console.log('Clean nodes being saved:', cleanNodes);
    console.log('Nodes JSON:', nodesJson);

    try {
      if (isNew) {
        const createPayload = {
          name,
          parameter,
          nodes: nodesJson,
          edges: edgesJson,
        };
        const created = await createWorkflow.mutateAsync(createPayload);
        navigate(`/workflows/${created.id}`, { replace: true });
      } else if (id) {
        const updatePayload = {
          name,
          nodes: nodesJson,
          edges: edgesJson,
        };
        await updateWorkflow.mutateAsync({ id, ...updatePayload });
      }
    } catch (error) {
      console.error('Failed to save workflow:', error);
      alert('Failed to save workflow. Please try again.');
    }
  };

  const handleToggleSimulation = useCallback(() => {
    setSimulationMode((prev) => !prev);
    // Show variables widget when entering simulation mode
    if (!simulationMode) {
      setShowVariables(true);
    }
  }, [simulationMode]);

  const handleCreateFixture = async () => {
    if (!newFixtureName.trim()) return;

    try {
      const optionObject = JSON.parse(newFixtureJson);
      await createFixture.mutateAsync({
        name: newFixtureName,
        option_object: optionObject,
      });
      setShowCreateFixtureModal(false);
      setNewFixtureName('');
      setNewFixtureJson('{\n  "EntityID": "",\n  "Forms": []\n}');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create fixture');
    }
  };

  const selectedNode = nodes.find((n) => n.id === selectedNodeId) ?? null;

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col">
      <WorkflowToolbar
        workflowName={workflow?.name ?? ''}
        parameter={workflow?.parameter ?? ''}
        onSave={handleSave}
        isSaving={createWorkflow.isPending || updateWorkflow.isPending}
        isNew={isNew}
        simulationMode={simulationMode}
        onToggleSimulation={handleToggleSimulation}
        // Simulation controls
        fixtures={fixtures}
        selectedFixtureId={selectedFixtureId}
        onSelectFixture={setSelectedFixtureId}
        onCreateFixture={() => setShowCreateFixtureModal(true)}
        onRunSimulation={simulation.runSimulation}
        simulationResult={simulation.result}
        isSimulating={simulation.isSimulating}
        isLoadingFixtures={isLoadingFixtures}
      />

      {/* Main editor area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top section: palette, canvas, property panel */}
        <div className="flex-1 flex overflow-hidden">
          <NodePalette onDragStart={handleDragStart} />

          {/* Canvas wrapper with floating widget */}
          <div className="flex-1 relative overflow-hidden">
            <WorkflowCanvas
              workflowId={id}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onAddNode={(node) => setNodes((nds) => [...nds, node])}
              onAddEdge={(edge) => setEdges((eds) => [...eds, edge])}
              onNodeSelect={setSelectedNodeId}
              selectedNodeId={selectedNodeId}
              simulationResult={simulationMode ? simulation.result : null}
            />

            {/* Floating Variables Widget */}
            {simulationMode && showVariables && simulation.result && (
              <FloatingVariablesWidget
                variables={simulation.result.variables}
                storageKey={id ? `workflow-${id}-variables` : 'simulation-variables'}
                onClose={() => setShowVariables(false)}
              />
            )}
          </div>

          {/* Property Panel - always visible */}
          <PropertyPanel
            selectedNode={selectedNode}
            onUpdateNode={handleUpdateNodeData}
            onDeleteNode={handleDeleteNode}
          />
        </div>

        {/* Bottom simulation panel */}
        {simulationMode && (
          <SimulationBottomPanel
            workflowId={id}
            simulationResult={simulation.result}
            isSimulating={simulation.isSimulating}
            error={simulation.error}
          />
        )}
      </div>

      {/* Create Fixture Modal */}
      <Modal
        isOpen={showCreateFixtureModal}
        onClose={() => setShowCreateFixtureModal(false)}
        title="Create Test Fixture"
      >
        <div className="space-y-4">
          <Input
            label="Fixture Name"
            value={newFixtureName}
            onChange={(e) => setNewFixtureName(e.target.value)}
            placeholder="e.g., New Patient Admission"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              OptionObject JSON
            </label>
            <textarea
              value={newFixtureJson}
              onChange={(e) => setNewFixtureJson(e.target.value)}
              className="w-full h-48 px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
              placeholder='{"EntityID": "12345", "Forms": []}'
            />
            <p className="mt-1 text-xs text-gray-500">
              Paste or edit the OptionObject JSON for testing
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="secondary" onClick={() => setShowCreateFixtureModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateFixture}
              disabled={!newFixtureName.trim() || createFixture.isPending}
            >
              {createFixture.isPending ? 'Creating...' : 'Create Fixture'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
