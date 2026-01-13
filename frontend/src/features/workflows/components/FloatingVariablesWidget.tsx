import { useState } from 'react';
import { ChevronUp, ChevronDown, X } from 'lucide-react';
import { useLocalStorage } from '@/hooks/useLocalStorage';

interface FloatingVariablesWidgetProps {
  variables: Record<string, unknown>;
  storageKey?: string;
  onClose?: () => void;
}

/**
 * Floating widget displaying workflow variables.
 * Positioned in top-right corner of parent container.
 * Semi-transparent when unfocused.
 */
export function FloatingVariablesWidget({
  variables,
  storageKey = 'variables-widget',
  onClose,
}: FloatingVariablesWidgetProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [isCollapsed, setIsCollapsed] = useLocalStorage(`${storageKey}-collapsed`, false);

  const variableEntries = Object.entries(variables);

  const getTypeName = (value: unknown): string => {
    if (value === null) return 'null';
    if (Array.isArray(value)) return `array[${value.length}]`;
    return typeof value;
  };

  const formatValue = (value: unknown): string => {
    if (value === null) return 'null';
    if (typeof value === 'object') return JSON.stringify(value);
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    if (typeof value === 'string') return value || '""';
    return String(value);
  };

  return (
    <div
      className={`
        absolute top-4 right-4 w-72 bg-white rounded-lg shadow-lg border
        transition-opacity duration-200
        ${isFocused ? 'opacity-100' : 'opacity-85'}
      `}
      style={{
        zIndex: 40,
        maxHeight: '400px',
      }}
      onMouseEnter={() => setIsFocused(true)}
      onMouseLeave={() => setIsFocused(false)}
      onClick={() => setIsFocused(true)}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b bg-gray-50 rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm text-gray-700">Variables</span>
          <span className="text-xs bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded-full">
            {variableEntries.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsCollapsed(!isCollapsed);
            }}
            className="p-1 hover:bg-gray-200 rounded"
            title={isCollapsed ? 'Expand' : 'Collapse'}
          >
            {isCollapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
          </button>
          {onClose && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClose();
              }}
              className="p-1 hover:bg-gray-200 rounded"
              title="Close"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {!isCollapsed && (
        <div className="max-h-80 overflow-y-auto">
          {variableEntries.length === 0 ? (
            <p className="text-gray-500 text-sm italic p-2">No variables set</p>
          ) : (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="text-left px-2 py-1 font-medium text-gray-600">Name</th>
                  <th className="text-left px-2 py-1 font-medium text-gray-600">Value</th>
                  <th className="text-left px-2 py-1 font-medium text-gray-600 w-16">Type</th>
                </tr>
              </thead>
              <tbody>
                {variableEntries.map(([key, value]) => (
                  <tr key={key} className="border-b hover:bg-gray-50">
                    <td className="px-2 py-1 font-mono text-blue-600">{key}</td>
                    <td className="px-2 py-1 font-mono text-gray-700 max-w-[150px] truncate">
                      {formatValue(value)}
                    </td>
                    <td className="px-2 py-1 text-gray-500 text-xs">{getTypeName(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
