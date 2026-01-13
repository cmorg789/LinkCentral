import { memo, useMemo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { cn } from '@/lib/cn';
import { NODE_DEFINITIONS, type CaseItem } from '../utils/nodeDefinitions';

interface ExecutionStatus {
  executed: boolean;
  execution_order: number | null;
  output_port: string | null;
  error: string | null;
}

interface BaseNodeProps {
  id: string;
  type?: string;
  data: Record<string, unknown> & {
    executionStatus?: ExecutionStatus;
  };
  selected?: boolean;
}

// Compute dynamic outputs for nodes that support them (e.g., Switch)
function getDynamicOutputs(
  type: string,
  data: Record<string, unknown> | undefined,
  staticOutputs: string[]
): string[] {
  // Switch node: build outputs from cases + default
  if (type === 'switch') {
    // Handle null/undefined data during initialization
    if (!data) {
      return ['default'];
    }

    const cases = data.cases as CaseItem[] | undefined;
    const defaultPort = (data.default_port as string) || 'default';

    if (cases && Array.isArray(cases) && cases.length > 0) {
      const casePorts = cases.map((c) => c.port).filter(Boolean);
      // Remove default port from cases (if present) and add it at the end
      // This ensures default is always last for consistency
      const filteredPorts = casePorts.filter((port) => port !== defaultPort);
      return [...filteredPorts, defaultPort];
    }
    // No cases configured - show just default
    return [defaultPort];
  }

  // Other nodes: use static outputs from definition
  return staticOutputs;
}

// Compute dynamic inputs for nodes that support them (e.g., Merge)
function getDynamicInputs(
  type: string,
  data: Record<string, unknown> | undefined,
  staticInputs: string[]
): string[] {
  // Merge node: build inputs based on input_count
  if (type === 'merge') {
    // Handle null/undefined data during initialization - default to 2 inputs
    const inputCount = data?.input_count ? Number(data.input_count) : 2;
    const count = Math.max(2, inputCount); // Minimum 2 inputs

    const inputs: string[] = [];
    for (let i = 1; i <= count; i++) {
      inputs.push(`in_${i}`);
    }
    return inputs;
  }

  // Other nodes: use static inputs from definition
  return staticInputs;
}

function BaseNodeComponent({ type, data, selected }: BaseNodeProps) {
  const definition = NODE_DEFINITIONS[type || ''];
  if (!definition) {
    return (
      <div className="px-3 py-2 bg-gray-100 border border-gray-300 rounded">
        Unknown: {type}
      </div>
    );
  }

  const { label, color } = definition;

  // Compute inputs dynamically for nodes like Merge
  const inputs = useMemo(
    () => getDynamicInputs(type || '', data, definition.inputs),
    [type, data, definition.inputs]
  );

  // Compute outputs dynamically for nodes like Switch
  const outputs = useMemo(
    () => getDynamicOutputs(type || '', data, definition.outputs),
    [type, data, definition.outputs]
  );

  // Determine if node should be taller (e.g., Merge with multiple inputs)
  const isMergeNode = type === 'merge';
  const minHeight = isMergeNode ? Math.max(60, inputs.length * 24) : undefined;

  const executionStatus = data?.executionStatus;

  // Determine visual state based on execution status
  const isSkipped = executionStatus && !executionStatus.executed;
  const hasError = executionStatus?.error != null;
  const executionOrder = executionStatus?.execution_order;
  const activePort = executionStatus?.output_port;

  // Calculate handle positions based on number of handles
  const getHandleStyle = (index: number, total: number): React.CSSProperties => {
    if (total === 1) return { top: '50%' };
    const spacing = 100 / (total + 1);
    return { top: `${spacing * (index + 1)}%` };
  };

  // Determine border color
  const getBorderColor = () => {
    if (hasError) return '#ef4444'; // red
    if (selected) return '#3b82f6'; // blue
    if (isSkipped) return '#9ca3af'; // gray
    return color;
  };

  // Determine background color
  const getBackgroundColor = () => {
    if (hasError) return '#fef2f2'; // red-50
    if (isSkipped) return '#f3f4f6'; // gray-100
    return `${color}15`;
  };

  return (
    <div
      className={cn(
        'relative px-4 py-2 rounded-lg border-2 min-w-[140px] shadow-sm transition-all',
        selected && 'shadow-lg ring-2 ring-blue-400',
        isSkipped && 'opacity-50'
      )}
      style={{
        backgroundColor: getBackgroundColor(),
        borderColor: getBorderColor(),
        minHeight: minHeight,
      }}
    >
      {/* Execution order badge */}
      {executionOrder != null && (
        <div
          className={cn(
            'absolute -top-2 -left-2 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white',
            hasError ? 'bg-red-500' : 'bg-green-500'
          )}
        >
          {executionOrder}
        </div>
      )}

      {/* Input handles */}
      {inputs.map((input: string, idx: number) => (
        <Handle
          key={input}
          type="target"
          position={Position.Left}
          id={input}
          style={{
            ...getHandleStyle(idx, inputs.length),
            backgroundColor: isSkipped ? '#9ca3af' : color,
            width: 10,
            height: 10,
          }}
        />
      ))}

      {/* Node content */}
      <div className="flex items-center gap-2">
        <div
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: hasError ? '#ef4444' : isSkipped ? '#9ca3af' : color }}
        />
        <span className="font-medium text-sm text-gray-800">{label}</span>
      </div>

      {/* Error message (if any) */}
      {hasError && executionStatus?.error && (
        <div className="mt-1 text-xs text-red-600 max-w-[160px] truncate" title={executionStatus.error}>
          Error: {executionStatus.error}
        </div>
      )}

      {/* Show key data preview (only when no error) */}
      {!hasError && definition.properties.length > 0 && (
        <div className="mt-1 text-xs text-gray-500 max-w-[160px] truncate">
          {definition.properties
            .slice(0, 2)
            .map((prop) => {
              const val = data?.[prop.key];
              return val ? `${prop.label}: ${val}` : null;
            })
            .filter(Boolean)
            .join(', ') || 'Click to configure'}
        </div>
      )}

      {/* Output handles */}
      {outputs.map((output: string, idx: number) => (
        <Handle
          key={output}
          type="source"
          position={Position.Right}
          id={output}
          style={{
            ...getHandleStyle(idx, outputs.length),
            backgroundColor: isSkipped ? '#9ca3af' : (output === 'true' ? '#22c55e' : output === 'false' ? '#ef4444' : color),
            width: 10,
            height: 10,
          }}
        />
      ))}

      {/* Output port labels (for nodes with multiple outputs like if/else, switch) */}
      {outputs.length > 1 &&
        outputs.map((output: string, idx: number) => {
          const isActivePort = activePort === output;
          const handleStyle = getHandleStyle(idx, outputs.length);

          // Color-code labels based on semantic meaning
          const getLabelColor = () => {
            if (isSkipped) return '#9ca3af';
            if (output === 'true' || output === 'each') return '#22c55e'; // green for positive/continue
            if (output === 'false' || output === 'done') return '#ef4444'; // red for negative/exit
            if (output === 'default') return '#6b7280'; // gray for default
            return color; // use node color for custom ports (switch cases)
          };

          return (
            <span
              key={`label-${output}`}
              className="absolute text-[10px] font-medium whitespace-nowrap"
              style={{
                right: 14,
                top: handleStyle.top,
                transform: 'translateY(-50%)',
                color: getLabelColor(),
                opacity: executionStatus && !isActivePort ? 0.4 : 1,
              }}
            >
              {output}
            </span>
          );
        })}
    </div>
  );
}

export const BaseNode = memo(BaseNodeComponent);
