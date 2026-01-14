import { useState } from 'react';
import type { Node } from '@xyflow/react';
import { Trash2, Maximize2, Settings2, Plus, Minus } from 'lucide-react';
import { NODE_DEFINITIONS, type PropertyDefinition, type CaseItem } from '../utils/nodeDefinitions';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { ConnectionSelect } from './ConnectionSelect';
import { SqlQueryEditorModal } from './SqlQueryEditorModal';
import { CaseListEditorModal } from './CaseListEditorModal';
import { ConditionBuilder } from './ConditionBuilder';

interface PropertyPanelProps {
  selectedNode: Node | null;
  onUpdateNode: (nodeId: string, data: Record<string, unknown>) => void;
  onDeleteNode?: (nodeId: string) => void;
}

export function PropertyPanel({ selectedNode, onUpdateNode, onDeleteNode }: PropertyPanelProps) {
  const [expandedField, setExpandedField] = useState<string | null>(null);

  if (!selectedNode) {
    return (
      <div className="w-72 bg-gray-50 border-l p-4">
        <div className="text-center text-gray-400 mt-8">
          <p className="text-sm">Select a node to edit its properties</p>
        </div>
      </div>
    );
  }

  const definition = NODE_DEFINITIONS[selectedNode.type || ''];
  if (!definition) {
    return (
      <div className="w-72 bg-gray-50 border-l p-4">
        <p className="text-sm text-gray-500">Unknown node type</p>
      </div>
    );
  }

  const handlePropertyChange = (key: string, value: string | CaseItem[] | Record<string, string>) => {
    onUpdateNode(selectedNode.id, {
      ...selectedNode.data,
      [key]: value,
    });
  };

  const renderProperty = (prop: PropertyDefinition) => {
    const value = (selectedNode.data?.[prop.key] as string) ?? '';

    // Handle case_list type (for Switch node cases)
    if (prop.type === 'case_list' && prop.caseListConfig) {
      const cases = (selectedNode.data?.[prop.key] as CaseItem[]) ?? [];
      return (
        <div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setExpandedField(prop.key)}
            className="w-full justify-start"
          >
            <Settings2 size={14} />
            {cases.length > 0 ? `${cases.length} case${cases.length !== 1 ? 's' : ''} configured` : 'Configure cases'}
          </Button>
          {cases.length > 0 && (
            <div className="mt-2 space-y-1">
              {cases.slice(0, 3).map((c) => (
                <div key={c.id} className="text-xs text-gray-500 truncate bg-gray-50 px-2 py-1 rounded">
                  <span className="font-mono">{c.value || '(empty)'}</span>
                  <span className="text-gray-400 mx-1">&rarr;</span>
                  <span className="font-medium text-amber-600">{c.port}</span>
                </div>
              ))}
              {cases.length > 3 && (
                <div className="text-xs text-gray-400 px-2">
                  +{cases.length - 3} more...
                </div>
              )}
            </div>
          )}
          {expandedField === prop.key && (
            <CaseListEditorModal
              isOpen={true}
              onClose={() => setExpandedField(null)}
              cases={cases}
              onChange={(newCases) => handlePropertyChange(prop.key, newCases)}
              config={prop.caseListConfig}
            />
          )}
        </div>
      );
    }

    // Handle dynamic_select for connections
    if (prop.type === 'dynamic_select' && prop.optionsSource === 'connections') {
      return (
        <ConnectionSelect
          value={value}
          onChange={(v) => handlePropertyChange(prop.key, v)}
        />
      );
    }

    // Handle static select
    if (prop.type === 'select' && prop.options) {
      return (
        <Select
          value={value}
          onChange={(e) => handlePropertyChange(prop.key, e.target.value)}
          options={prop.options}
        />
      );
    }

    // Handle expandable text fields
    if (prop.type === 'text' && prop.expandable) {
      return (
        <div className="relative">
          <Input
            type="text"
            value={value}
            placeholder={prop.placeholder}
            onChange={(e) => handlePropertyChange(prop.key, e.target.value)}
            className="pr-10"
          />
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded"
            onClick={() => setExpandedField(prop.key)}
            title="Expand editor"
          >
            <Maximize2 size={14} className="text-gray-400" />
          </button>
          {prop.expandModalType === 'sql' && expandedField === prop.key && (
            <SqlQueryEditorModal
              isOpen={true}
              onClose={() => setExpandedField(null)}
              value={value}
              onChange={(v) => handlePropertyChange(prop.key, v)}
            />
          )}
        </div>
      );
    }

    // Handle key-value pairs (for SQL parameters, etc.)
    if (prop.type === 'key_value') {
      const kvValue = (selectedNode.data?.[prop.key] as Record<string, string>) ?? {};
      const entries = Object.entries(kvValue);

      const handleKvChange = (oldKey: string, newKey: string, newValue: string) => {
        const newKv = { ...kvValue };
        if (oldKey !== newKey) {
          delete newKv[oldKey];
        }
        if (newKey) {
          newKv[newKey] = newValue;
        }
        handlePropertyChange(prop.key, newKv);
      };

      const handleKvAdd = () => {
        const newKv = { ...kvValue, '': '' };
        handlePropertyChange(prop.key, newKv);
      };

      const handleKvRemove = (key: string) => {
        const newKv = { ...kvValue };
        delete newKv[key];
        handlePropertyChange(prop.key, newKv);
      };

      return (
        <div className="space-y-2">
          {entries.map(([k, v], idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <Input
                type="text"
                value={k}
                placeholder="param"
                className="w-24 text-sm"
                onChange={(e) => handleKvChange(k, e.target.value, v)}
              />
              <span className="text-gray-400">=</span>
              <Input
                type="text"
                value={v}
                placeholder="@var.value"
                className="flex-1 text-sm"
                onChange={(e) => handleKvChange(k, k, e.target.value)}
              />
              <button
                type="button"
                onClick={() => handleKvRemove(k)}
                className="p-1 text-gray-400 hover:text-red-500"
              >
                <Minus size={14} />
              </button>
            </div>
          ))}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={handleKvAdd}
            className="w-full"
          >
            <Plus size={14} />
            Add Parameter
          </Button>
        </div>
      );
    }

    // Default text/number input
    return (
      <Input
        type={prop.type === 'number' ? 'number' : 'text'}
        value={value}
        placeholder={prop.placeholder}
        onChange={(e) => handlePropertyChange(prop.key, e.target.value)}
      />
    );
  };

  return (
    <div className="w-72 bg-white border-l overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b" style={{ backgroundColor: `${definition.color}10` }}>
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: definition.color }}
          />
          <h3 className="font-semibold">{definition.label}</h3>
        </div>
        <p className="text-sm text-gray-500 mt-1">{definition.description}</p>
      </div>

      {/* Properties */}
      <div className="p-4 space-y-4">
        {definition.properties.length === 0 ? (
          <p className="text-sm text-gray-400 italic">
            This node has no configurable properties.
          </p>
        ) : selectedNode.type === 'if_else' ? (
          /* Special rendering for If/Else node using ConditionBuilder */
          <ConditionBuilder
            leftValue={(selectedNode.data?.left_value as string) ?? ''}
            operator={(selectedNode.data?.operator as string) ?? '=='}
            rightValue={(selectedNode.data?.right_value as string) ?? ''}
            onChange={(field, value) => handlePropertyChange(field, value)}
          />
        ) : selectedNode.type === 'merge' ? (
          /* Special rendering for Merge node with +/- buttons */
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Input Ports
              </label>
              <div className="flex items-center gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    const currentCount = Number(selectedNode.data?.input_count) || 2;
                    if (currentCount > 2) {
                      handlePropertyChange('input_count', String(currentCount - 1));
                    }
                  }}
                  disabled={Number(selectedNode.data?.input_count || 2) <= 2}
                  className="px-3"
                >
                  <Minus size={16} />
                </Button>
                <span className="text-lg font-semibold text-gray-700 min-w-[2rem] text-center">
                  {Number(selectedNode.data?.input_count) || 2}
                </span>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    const currentCount = Number(selectedNode.data?.input_count) || 2;
                    handlePropertyChange('input_count', String(currentCount + 1));
                  }}
                  className="px-3"
                >
                  <Plus size={16} />
                </Button>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Minimum: 2 inputs. Add more as needed.
              </p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-xs font-medium text-green-800 mb-2">Current input ports:</p>
              <div className="flex flex-wrap gap-2">
                {Array.from({ length: Number(selectedNode.data?.input_count) || 2 }, (_, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-green-100 text-green-800 rounded text-xs font-mono"
                  >
                    in_{i + 1}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          definition.properties.map((prop) => (
            <div key={prop.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {prop.label}
                {prop.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {renderProperty(prop)}
              {prop.helpText && (
                <p className="text-xs text-gray-400 mt-1">{prop.helpText}</p>
              )}
            </div>
          ))
        )}
      </div>

      {/* Node info & actions */}
      <div className="p-4 border-t bg-gray-50 space-y-3">
        <p className="text-xs text-gray-400">
          Node ID: <code className="bg-gray-200 px-1 rounded">{selectedNode.id}</code>
        </p>

        {/* Delete button - not for start/end nodes */}
        {onDeleteNode && selectedNode.type !== 'start' && selectedNode.type !== 'end' && (
          <Button
            variant="secondary"
            size="sm"
            className="w-full text-red-600 hover:bg-red-50 hover:text-red-700"
            onClick={() => onDeleteNode(selectedNode.id)}
          >
            <Trash2 size={14} />
            Delete Node
          </Button>
        )}
      </div>
    </div>
  );
}
