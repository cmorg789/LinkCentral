import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';

interface ConditionBuilderProps {
  leftValue: string;
  operator: string;
  rightValue: string;
  onChange: (field: 'left_value' | 'operator' | 'right_value', value: string) => void;
}

const OPERATORS = [
  { value: '==', label: 'equals' },
  { value: '!=', label: 'does not equal' },
  { value: '>', label: 'is greater than' },
  { value: '<', label: 'is less than' },
  { value: '>=', label: 'is greater or equal to' },
  { value: '<=', label: 'is less or equal to' },
  { value: 'contains', label: 'contains' },
  { value: 'startswith', label: 'starts with' },
  { value: 'endswith', label: 'ends with' },
  { value: 'matches', label: 'matches regex' },
  { value: 'is_empty', label: 'is empty' },
  { value: 'is_not_empty', label: 'is not empty' },
];

// Operators that don't need a right value
const UNARY_OPERATORS = ['is_empty', 'is_not_empty'];

export function ConditionBuilder({
  leftValue,
  operator,
  rightValue,
  onChange,
}: ConditionBuilderProps) {
  const isUnary = UNARY_OPERATORS.includes(operator);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="text-xs font-medium text-gray-600 uppercase tracking-wide">
        Check if...
      </div>

      {/* Left value */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">Value</label>
        <Input
          type="text"
          value={leftValue}
          placeholder="@var.myVar or @field.123"
          onChange={(e) => onChange('left_value', e.target.value)}
        />
      </div>

      {/* Operator */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">Condition</label>
        <Select
          value={operator}
          onChange={(e) => onChange('operator', e.target.value)}
          options={OPERATORS}
        />
      </div>

      {/* Right value - hidden for unary operators */}
      {!isUnary && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">Compare to</label>
          <Input
            type="text"
            value={rightValue}
            placeholder="value or @var.other"
            onChange={(e) => onChange('right_value', e.target.value)}
          />
        </div>
      )}

      {/* Preview */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 mt-3">
        <p className="text-xs text-amber-800">
          <span className="font-medium">Preview: </span>
          <span className="font-mono">
            {leftValue || '?'}
            {' '}
            <span className="text-amber-600 font-semibold">
              {OPERATORS.find((o) => o.value === operator)?.label || operator}
            </span>
            {!isUnary && (
              <>
                {' '}
                {rightValue || '?'}
              </>
            )}
          </span>
        </p>
      </div>
    </div>
  );
}
