import { useState, useEffect } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import type { CaseItem, CaseListConfig } from '../utils/nodeDefinitions';

interface CaseListEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  cases: CaseItem[];
  onChange: (cases: CaseItem[]) => void;
  config: CaseListConfig;
}

function generateId(): string {
  return `case_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function generatePortName(cases: CaseItem[]): string {
  const existingPorts = new Set(cases.map((c) => c.port));
  let index = cases.length + 1;
  while (existingPorts.has(`case_${index}`)) {
    index++;
  }
  return `case_${index}`;
}

export function CaseListEditorModal({
  isOpen,
  onClose,
  cases,
  onChange,
  config,
}: CaseListEditorModalProps) {
  const [localCases, setLocalCases] = useState<CaseItem[]>(cases);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Sync local state when modal opens (only on open, not when cases prop changes)
  useEffect(() => {
    if (isOpen) {
      setLocalCases(cases.length > 0 ? cases : []);
      setErrors({});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const validateCases = (casesToValidate: CaseItem[]): Record<string, string> => {
    const newErrors: Record<string, string> = {};
    const seenPorts = new Set<string>();

    casesToValidate.forEach((caseItem) => {
      // Check for empty port
      if (!caseItem.port.trim()) {
        newErrors[caseItem.id] = 'Port name is required';
      }
      // Check for invalid port name (must be alphanumeric + underscore)
      else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(caseItem.port)) {
        newErrors[caseItem.id] = 'Port must start with letter/underscore, contain only letters, numbers, underscores';
      }
      // Check for duplicate ports
      else if (seenPorts.has(caseItem.port)) {
        newErrors[caseItem.id] = 'Duplicate port name';
      } else {
        seenPorts.add(caseItem.port);
      }
    });

    return newErrors;
  };

  const handleAddCase = () => {
    const newCase: CaseItem = {
      id: generateId(),
      value: '',
      port: generatePortName(localCases),
    };
    setLocalCases([...localCases, newCase]);
  };

  const handleRemoveCase = (id: string) => {
    setLocalCases(localCases.filter((c) => c.id !== id));
    setErrors((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const handleCaseChange = (id: string, field: 'value' | 'port', value: string) => {
    const updated = localCases.map((c) =>
      c.id === id ? { ...c, [field]: value } : c
    );
    setLocalCases(updated);

    // Clear error for this case when editing
    if (errors[id]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    }
  };

  const handleSave = () => {
    const validationErrors = validateCases(localCases);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }
    onChange(localCases);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Configure Switch Cases"
      className="max-w-2xl w-full"
    >
      <div>
        <p className="text-sm text-gray-500 mb-4">
          Define the cases for this switch node. Each case matches a value and routes to a specific output port.
        </p>

        {/* Case list */}
        <div className="space-y-3 mb-4 max-h-[400px] overflow-y-auto">
          {localCases.length === 0 ? (
            <div className="text-center py-8 text-gray-400 bg-gray-50 rounded-lg border-2 border-dashed">
              <p className="mb-2">No cases defined</p>
              <p className="text-sm">Click "Add Case" to create your first case</p>
            </div>
          ) : (
            localCases.map((caseItem, index) => (
              <div
                key={caseItem.id}
                className={`p-3 bg-gray-50 rounded-lg border ${
                  errors[caseItem.id] ? 'border-red-300' : 'border-gray-200'
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-gray-500 bg-gray-200 px-2 py-0.5 rounded">
                    Case {index + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveCase(caseItem.id)}
                    className="ml-auto p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
                    title="Remove case"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      {config.valueLabel}
                    </label>
                    <Input
                      type="text"
                      placeholder={config.valuePlaceholder}
                      value={caseItem.value}
                      onChange={(e) => handleCaseChange(caseItem.id, 'value', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">
                      {config.portLabel}
                    </label>
                    <Input
                      type="text"
                      placeholder={config.portPlaceholder}
                      value={caseItem.port}
                      onChange={(e) => handleCaseChange(caseItem.id, 'port', e.target.value)}
                      className={errors[caseItem.id] ? 'border-red-300' : ''}
                    />
                  </div>
                </div>

                {errors[caseItem.id] && (
                  <p className="mt-2 text-xs text-red-500">{errors[caseItem.id]}</p>
                )}
              </div>
            ))
          )}
        </div>

        {/* Add button */}
        <Button
          type="button"
          variant="secondary"
          onClick={handleAddCase}
          className="w-full mb-4"
        >
          <Plus size={16} />
          Add Case
        </Button>

        {/* Preview of output ports */}
        {localCases.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
            <p className="text-xs font-medium text-amber-800 mb-2">Output ports that will appear:</p>
            <div className="flex flex-wrap gap-2">
              {localCases.map((c) => (
                <span
                  key={c.id}
                  className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-xs font-mono"
                >
                  {c.port || '(empty)'}
                </span>
              ))}
              <span className="px-2 py-1 bg-gray-200 text-gray-600 rounded text-xs font-mono">
                default
              </span>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Cases</Button>
        </div>
      </div>
    </Modal>
  );
}
