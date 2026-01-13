import { NODE_DEFINITIONS, NODE_CATEGORIES } from '../utils/nodeDefinitions';

interface NodePaletteProps {
  onDragStart: (event: React.DragEvent, nodeType: string) => void;
}

export function NodePalette({ onDragStart }: NodePaletteProps) {
  return (
    <div className="w-48 bg-gray-50 border-r p-3 overflow-y-auto">
      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
        Add Nodes
      </h3>

      {Object.entries(NODE_CATEGORIES).map(([category, { label, nodes }]) => (
        <div key={category} className="mb-4">
          <h4 className="text-xs font-medium text-gray-400 mb-2">{label}</h4>
          <div className="space-y-1">
            {nodes.map((nodeType) => {
              const def = NODE_DEFINITIONS[nodeType];
              if (!def) return null;

              return (
                <div
                  key={nodeType}
                  draggable
                  onDragStart={(e) => onDragStart(e, nodeType)}
                  className="flex items-center gap-2 px-2 py-1.5 rounded cursor-grab hover:bg-gray-100 transition-colors"
                  style={{ backgroundColor: `${def.color}10` }}
                >
                  <div
                    className="w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: def.color }}
                  />
                  <span className="text-sm text-gray-700">{def.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <div className="mt-4 pt-4 border-t">
        <p className="text-xs text-gray-400">
          Drag nodes to the canvas to add them to your workflow.
        </p>
      </div>
    </div>
  );
}
