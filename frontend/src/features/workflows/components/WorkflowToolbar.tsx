import { useState, useEffect } from 'react';
import { Save, ArrowLeft, Settings, Play, Square, Plus, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import type { SimulationResponse } from '@/api/types';

interface TestFixture {
  id: string;
  name: string;
  option_object: Record<string, unknown>;
  created_at: string;
  source?: string;
  request_log_id?: string;
}

interface WorkflowToolbarProps {
  workflowName: string;
  parameter: string;
  onSave: (name: string, parameter: string) => Promise<void>;
  isSaving: boolean;
  isNew: boolean;
  simulationMode?: boolean;
  onToggleSimulation?: () => void;
  // Simulation controls
  fixtures?: TestFixture[];
  selectedFixtureId?: string | null;
  onSelectFixture?: (fixtureId: string | null) => void;
  onCreateFixture?: () => void;
  onRunSimulation?: () => void;
  simulationResult?: SimulationResponse | null;
  isSimulating?: boolean;
  isLoadingFixtures?: boolean;
}

export function WorkflowToolbar({
  workflowName,
  parameter,
  onSave,
  isSaving,
  isNew,
  simulationMode = false,
  onToggleSimulation,
  fixtures = [],
  selectedFixtureId,
  onSelectFixture,
  onCreateFixture,
  onRunSimulation,
  simulationResult,
  isSimulating = false,
  isLoadingFixtures = false,
}: WorkflowToolbarProps) {
  const [showSettings, setShowSettings] = useState(isNew);
  const [name, setName] = useState(workflowName);
  const [param, setParam] = useState(parameter);

  // Sync local state when props change (e.g., after async workflow load)
  useEffect(() => {
    if (workflowName) setName(workflowName);
  }, [workflowName]);

  useEffect(() => {
    if (parameter) setParam(parameter);
  }, [parameter]);

  const handleSave = async () => {
    if (isNew && (!name || !param)) {
      setShowSettings(true);
      return;
    }
    await onSave(name || workflowName, param || parameter);
  };

  const handleSettingsSave = async () => {
    if (!name || !param) return;
    setShowSettings(false);
    await onSave(name, param);
  };

  return (
    <>
      <div className="h-14 bg-white border-b flex items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Link
            to="/workflows"
            className="p-2 rounded hover:bg-gray-100 transition-colors"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="font-semibold text-gray-800">
              {name || workflowName || 'New Workflow'}
            </h1>
            <p className="text-xs text-gray-500">
              Parameter: {param || parameter || '(not set)'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Simulation Controls - shown when in simulation mode */}
          {simulationMode && (
            <div className="flex items-center gap-2 mr-4 pr-4 border-r">
              {/* Fixture Selector */}
              <div className="flex items-center gap-1">
                <Select
                  value={selectedFixtureId || ''}
                  onChange={(e) => onSelectFixture?.(e.target.value || null)}
                  options={fixtures.map((f) => ({
                    value: f.id,
                    label: f.name,
                  }))}
                  disabled={isLoadingFixtures}
                  className="w-48"
                />
                {onCreateFixture && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={onCreateFixture}
                    title="Create new fixture"
                  >
                    <Plus size={14} />
                  </Button>
                )}
              </div>

              {/* Run Button */}
              {onRunSimulation && selectedFixtureId && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={onRunSimulation}
                  disabled={isSimulating}
                  title="Run simulation"
                >
                  {isSimulating ? (
                    <Spinner size="sm" />
                  ) : (
                    <Play size={14} />
                  )}
                  Run
                </Button>
              )}

              {/* Status Indicator */}
              {simulationResult && (
                <div className="flex items-center gap-2 text-sm">
                  {simulationResult.success ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle size={14} />
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-600">
                      <AlertCircle size={14} />
                    </span>
                  )}
                  <span className="flex items-center gap-1 text-gray-500 text-xs">
                    <Clock size={12} />
                    {simulationResult.execution_time_ms}ms
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Simulation Toggle */}
          {!isNew && onToggleSimulation && (
            <Button
              variant={simulationMode ? 'primary' : 'secondary'}
              size="sm"
              onClick={onToggleSimulation}
              title={simulationMode ? 'Exit simulation mode' : 'Enter simulation mode'}
            >
              {simulationMode ? <Square size={16} /> : <Play size={16} />}
              {simulationMode ? 'Stop Sim' : 'Simulate'}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowSettings(true)}
          >
            <Settings size={16} />
            Settings
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            size="sm"
          >
            <Save size={16} />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      {/* Settings Modal */}
      <Modal
        isOpen={showSettings}
        onClose={() => !isNew && setShowSettings(false)}
        title="Workflow Settings"
      >
        <div className="space-y-4">
          <Input
            label="Workflow Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="My Workflow"
          />
          <Input
            label="Parameter"
            value={param}
            onChange={(e) => setParam(e.target.value)}
            placeholder="my_workflow"
            disabled={!isNew}
          />
          {!isNew && (
            <p className="text-xs text-gray-500">
              Parameter cannot be changed after creation.
            </p>
          )}
          <div className="flex justify-end gap-2 pt-4">
            {!isNew && (
              <Button variant="secondary" onClick={() => setShowSettings(false)}>
                Cancel
              </Button>
            )}
            <Button onClick={handleSettingsSave} disabled={!name || !param}>
              {isNew ? 'Create Workflow' : 'Save Settings'}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
}
