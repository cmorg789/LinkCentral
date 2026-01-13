import { useState } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Trash2,
  Play,
  Clock,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Spinner } from '@/components/ui/Spinner';
import { JsonViewer } from '@/features/requests/components/JsonViewer';
import { useTestFixtures, useTestFixtureMutations } from '../hooks/useTestFixtures';
import type { SimulationResponse } from '@/api/types';

interface SimulationPanelProps {
  workflowId: string | undefined;
  selectedFixtureId: string | null;
  onSelectFixture: (fixtureId: string | null) => void;
  simulationResult: SimulationResponse | null;
  isSimulating: boolean;
  error: string | null;
  onRunSimulation: () => void;
}

type SectionName = 'input' | 'output' | 'variables' | 'trace';

export function SimulationPanel({
  workflowId,
  selectedFixtureId,
  onSelectFixture,
  simulationResult,
  isSimulating,
  error,
  onRunSimulation,
}: SimulationPanelProps) {
  const [expandedSection, setExpandedSection] = useState<SectionName | null>('variables');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFixtureName, setNewFixtureName] = useState('');
  const [newFixtureJson, setNewFixtureJson] = useState('{\n  "EntityID": "",\n  "Forms": []\n}');

  const { data: fixtures, isLoading: isLoadingFixtures } = useTestFixtures(workflowId);
  const { createFixture, deleteFixture } = useTestFixtureMutations(workflowId);

  const toggleSection = (section: SectionName) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const handleCreateFixture = async () => {
    if (!newFixtureName.trim()) return;

    try {
      const optionObject = JSON.parse(newFixtureJson);
      await createFixture.mutateAsync({
        name: newFixtureName,
        option_object: optionObject,
      });
      setShowCreateModal(false);
      setNewFixtureName('');
      setNewFixtureJson('{\n  "EntityID": "",\n  "Forms": []\n}');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create fixture');
    }
  };

  const handleDeleteFixture = async (fixtureId: string) => {
    if (!confirm('Delete this test fixture?')) return;
    try {
      await deleteFixture.mutateAsync(fixtureId);
      if (selectedFixtureId === fixtureId) {
        onSelectFixture(null);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete fixture');
    }
  };

  const selectedFixture = fixtures?.find((f) => f.id === selectedFixtureId);

  return (
    <div className="w-96 bg-gray-50 border-l flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b bg-white">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-800">Simulation</h3>
          {isSimulating && <Spinner size="sm" />}
        </div>

        {/* Fixture Selector */}
        <div className="flex gap-2">
          <div className="flex-1">
            <Select
              value={selectedFixtureId || ''}
              onChange={(e) => onSelectFixture(e.target.value || null)}
              options={
                fixtures?.map((f) => ({
                  value: f.id,
                  label: f.name,
                })) || []
              }
              disabled={isLoadingFixtures}
            />
          </div>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setShowCreateModal(true)}
            title="Create new fixture"
          >
            <Plus size={16} />
          </Button>
        </div>

        {/* Fixture Actions */}
        {selectedFixture && (
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <span>
              Source: {selectedFixture.source === 'request_log' ? 'Request Log' : 'Manual'}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => onRunSimulation()}
                className="text-blue-600 hover:text-blue-800"
                title="Run simulation"
              >
                <Play size={14} />
              </button>
              <button
                onClick={() => handleDeleteFixture(selectedFixture.id)}
                className="text-red-600 hover:text-red-800"
                title="Delete fixture"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Status Indicators */}
        {simulationResult && (
          <div className="mt-3 flex items-center gap-2 text-sm">
            {simulationResult.success ? (
              <span className="flex items-center gap-1 text-green-600">
                <CheckCircle size={14} />
                Success
              </span>
            ) : (
              <span className="flex items-center gap-1 text-red-600">
                <AlertCircle size={14} />
                Failed
              </span>
            )}
            <span className="flex items-center gap-1 text-gray-500">
              <Clock size={14} />
              {simulationResult.execution_time_ms}ms
            </span>
          </div>
        )}

        {error && (
          <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
            {error}
          </div>
        )}
      </div>

      {/* Collapsible Sections */}
      <div className="flex-1 overflow-y-auto">
        {!selectedFixtureId ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            Select a test fixture to start simulation
          </div>
        ) : !simulationResult ? (
          <div className="p-4 text-center text-gray-500 text-sm">
            {isSimulating ? 'Running simulation...' : 'Waiting for simulation results...'}
          </div>
        ) : (
          <>
            {/* Variables Section */}
            <CollapsibleSection
              title="Variables"
              count={Object.keys(simulationResult.variables).length}
              expanded={expandedSection === 'variables'}
              onToggle={() => toggleSection('variables')}
            >
              {Object.keys(simulationResult.variables).length === 0 ? (
                <p className="text-gray-500 text-sm italic">No variables set</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(simulationResult.variables).map(([key, value]) => (
                    <div key={key} className="bg-white p-2 rounded border">
                      <span className="font-mono text-blue-600 text-sm">{key}</span>
                      <span className="text-gray-500 mx-1">=</span>
                      <span className="font-mono text-sm text-gray-700">
                        {typeof value === 'object'
                          ? JSON.stringify(value)
                          : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CollapsibleSection>

            {/* Execution Trace Section */}
            <CollapsibleSection
              title="Execution Trace"
              count={simulationResult.execution_trace.filter((n) => n.executed).length}
              expanded={expandedSection === 'trace'}
              onToggle={() => toggleSection('trace')}
            >
              <div className="space-y-1">
                {simulationResult.execution_trace
                  .filter((n) => n.executed)
                  .sort((a, b) => (a.execution_order || 0) - (b.execution_order || 0))
                  .map((node) => (
                    <div
                      key={node.node_id}
                      className={`p-2 rounded text-sm ${
                        node.error
                          ? 'bg-red-50 border-l-4 border-red-500'
                          : 'bg-white border-l-4 border-green-500'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 bg-green-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                          {node.execution_order}
                        </span>
                        <span className="font-medium">{node.node_type}</span>
                        {node.output_port && (
                          <span className="text-xs text-gray-500">→ {node.output_port}</span>
                        )}
                      </div>
                      {node.error && (
                        <p className="text-red-600 text-xs mt-1">{node.error}</p>
                      )}
                      {Object.keys(node.output_values).length > 0 && (
                        <div className="mt-1 text-xs text-gray-600">
                          Set: {Object.keys(node.output_values).join(', ')}
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </CollapsibleSection>

            {/* Input Section */}
            <CollapsibleSection
              title="Input (OptionObject)"
              expanded={expandedSection === 'input'}
              onToggle={() => toggleSection('input')}
            >
              <div className="max-h-64 overflow-auto bg-white p-2 rounded border">
                <JsonViewer data={simulationResult.input_option_object} initialExpanded={false} />
              </div>
            </CollapsibleSection>

            {/* Output Section */}
            <CollapsibleSection
              title="Output (Modified)"
              expanded={expandedSection === 'output'}
              onToggle={() => toggleSection('output')}
            >
              <div className="max-h-64 overflow-auto bg-white p-2 rounded border">
                <JsonViewer data={simulationResult.output_option_object} initialExpanded={false} />
              </div>
            </CollapsibleSection>
          </>
        )}
      </div>

      {/* Create Fixture Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
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
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
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

interface CollapsibleSectionProps {
  title: string;
  count?: number;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

function CollapsibleSection({
  title,
  count,
  expanded,
  onToggle,
  children,
}: CollapsibleSectionProps) {
  return (
    <div className="border-b">
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-100 transition-colors"
      >
        <span className="font-medium text-sm text-gray-700">{title}</span>
        <div className="flex items-center gap-2">
          {count !== undefined && (
            <span className="text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
              {count}
            </span>
          )}
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </div>
      </button>
      {expanded && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}
