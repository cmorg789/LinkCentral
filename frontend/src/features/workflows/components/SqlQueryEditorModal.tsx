import { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { SqlEditor } from '@/components/ui/SqlEditor';
import { Button } from '@/components/ui/Button';

interface SqlQueryEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  value: string;
  onChange: (value: string) => void;
}

export function SqlQueryEditorModal({
  isOpen,
  onClose,
  value,
  onChange,
}: SqlQueryEditorModalProps) {
  const [localValue, setLocalValue] = useState(value);

  // Sync local state when modal opens
  useEffect(() => {
    if (isOpen) {
      setLocalValue(value);
    }
  }, [isOpen, value]);

  const handleSave = () => {
    onChange(localValue);
    onClose();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl/Cmd + Enter to save
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="SQL Query Editor"
      className="max-w-4xl w-full"
    >
      <div onKeyDown={handleKeyDown}>
        <div className="mb-4">
          <p className="text-sm text-gray-500 mb-2">
            Write your SQL query below. Use <code className="bg-gray-100 px-1 rounded">:param</code> syntax for parameters.
          </p>
          <SqlEditor
            value={localValue}
            onChange={setLocalValue}
            height="400px"
            placeholder="SELECT * FROM table WHERE id = :id"
          />
        </div>

        <div className="flex items-center justify-between pt-4 border-t">
          <p className="text-xs text-gray-400">
            Press <kbd className="bg-gray-100 px-1.5 py-0.5 rounded text-xs">Ctrl+Enter</kbd> to save
          </p>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleSave}>
              Save Query
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
