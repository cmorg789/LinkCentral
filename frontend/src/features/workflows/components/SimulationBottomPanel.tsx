import { useState } from 'react';
import { CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { ResizableBottomPanel } from './ResizableBottomPanel';
import { HorizontalResizableColumns } from './HorizontalResizableColumns';
import { JsonViewer, ViewModeToggle } from '@/features/requests/components/JsonViewer';
import type { SimulationResponse } from '@/api/types';

type ViewMode = 'json' | 'table';

interface SimulationBottomPanelProps {
  workflowId: string | undefined;
  simulationResult: SimulationResponse | null;
  isSimulating: boolean;
  error: string | null;
}

/**
 * Bottom panel showing simulation results with Trace, Input, and Output columns.
 * Variables are shown in a separate floating widget.
 */
export function SimulationBottomPanel({
  workflowId,
  simulationResult,
  isSimulating,
  error,
}: SimulationBottomPanelProps) {
  const [inputViewMode, setInputViewMode] = useState<ViewMode>('json');
  const [outputViewMode, setOutputViewMode] = useState<ViewMode>('json');

  const storageKey = workflowId ? `workflow-${workflowId}-bottom-panel-height` : 'simulation-panel-height';
  const columnsStorageKey = workflowId ? `workflow-${workflowId}-column-ratios` : 'simulation-column-ratios';

  // Show placeholder when no simulation
  if (!simulationResult && !isSimulating && !error) {
    return (
      <ResizableBottomPanel isVisible storageKey={storageKey}>
        <div className="h-full flex items-center justify-center text-gray-500">
          Select a test fixture in the toolbar to start simulation
        </div>
      </ResizableBottomPanel>
    );
  }

  // Show loading state
  if (isSimulating && !simulationResult) {
    return (
      <ResizableBottomPanel isVisible storageKey={storageKey}>
        <div className="h-full flex items-center justify-center text-gray-500">
          <div className="flex items-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full" />
            Running simulation...
          </div>
        </div>
      </ResizableBottomPanel>
    );
  }

  // Show error state
  if (error && !simulationResult) {
    return (
      <ResizableBottomPanel isVisible storageKey={storageKey}>
        <div className="h-full flex items-center justify-center">
          <div className="p-4 bg-red-50 border border-red-200 rounded text-red-700 max-w-lg">
            <div className="flex items-center gap-2 font-medium mb-1">
              <AlertCircle size={16} />
              Simulation Error
            </div>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      </ResizableBottomPanel>
    );
  }

  const columns = [
    {
      id: 'trace',
      header: (
        <div className="flex items-center justify-between">
          <span>Execution Trace</span>
          {simulationResult && (
            <div className="flex items-center gap-2 text-xs">
              {simulationResult.success ? (
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle size={12} />
                </span>
              ) : (
                <span className="flex items-center gap-1 text-red-600">
                  <AlertCircle size={12} />
                </span>
              )}
              <span className="flex items-center gap-1 text-gray-500">
                <Clock size={12} />
                {simulationResult.execution_time_ms}ms
              </span>
            </div>
          )}
        </div>
      ),
      content: simulationResult ? (
        <TraceView trace={simulationResult.execution_trace} />
      ) : null,
      minWidth: 200,
    },
    {
      id: 'input',
      header: (
        <div className="flex items-center justify-between">
          <span>Input (OptionObject)</span>
          <ViewModeToggle viewMode={inputViewMode} onToggle={setInputViewMode} />
        </div>
      ),
      content: simulationResult ? (
        <div className="bg-white rounded border p-2 overflow-auto h-full">
          <JsonViewer
            data={simulationResult.input_option_object}
            initialExpanded
            initialExpandDepth={2}
            viewMode={inputViewMode}
          />
        </div>
      ) : null,
      minWidth: 200,
    },
    {
      id: 'output',
      header: (
        <div className="flex items-center justify-between">
          <span>Output (Delta)</span>
          <ViewModeToggle viewMode={outputViewMode} onToggle={setOutputViewMode} />
        </div>
      ),
      content: simulationResult ? (
        <div className="bg-white rounded border p-2 overflow-auto h-full">
          {Object.keys(simulationResult.output_delta || {}).length === 0 ? (
            <p className="text-gray-500 text-sm italic">No modifications</p>
          ) : (
            <JsonViewer
              data={simulationResult.output_delta}
              initialExpanded
              initialExpandDepth={3}
              viewMode={outputViewMode}
            />
          )}
        </div>
      ) : null,
      minWidth: 200,
    },
  ];

  return (
    <ResizableBottomPanel isVisible storageKey={storageKey}>
      <HorizontalResizableColumns columns={columns} storageKey={columnsStorageKey} />
    </ResizableBottomPanel>
  );
}

interface TraceViewProps {
  trace: SimulationResponse['execution_trace'];
}

function TraceView({ trace }: TraceViewProps) {
  const executedNodes = trace
    .filter((n) => n.executed)
    .sort((a, b) => (a.execution_order || 0) - (b.execution_order || 0));

  if (executedNodes.length === 0) {
    return <p className="text-gray-500 text-sm italic">No nodes executed</p>;
  }

  return (
    <div className="space-y-1">
      {executedNodes.map((node) => (
        <div
          key={node.node_id}
          className={`p-2 rounded text-sm ${
            node.error
              ? 'bg-red-50 border-l-4 border-red-500'
              : 'bg-white border-l-4 border-green-500'
          }`}
        >
          <div className="flex items-center gap-2">
            <span
              className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                node.error ? 'bg-red-500' : 'bg-green-500'
              }`}
            >
              {node.execution_order}
            </span>
            <span className="font-medium">{node.node_type}</span>
            {node.output_port && (
              <span className="text-xs text-gray-500">→ {node.output_port}</span>
            )}
          </div>
          {node.error && (
            <p className="text-red-600 text-xs mt-1 ml-7">{node.error}</p>
          )}
          {Object.keys(node.output_values).length > 0 && (
            <div className="mt-1 ml-7 text-xs text-gray-600">
              Set: {Object.keys(node.output_values).join(', ')}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
