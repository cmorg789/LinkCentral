import { useState, useCallback, useRef, useEffect } from 'react';
import { useLocalStorage } from '@/hooks/useLocalStorage';

interface Column {
  id: string;
  header: React.ReactNode;
  content: React.ReactNode;
  minWidth?: number;
}

interface HorizontalResizableColumnsProps {
  columns: Column[];
  storageKey?: string;
  defaultRatios?: number[];
}

/**
 * Horizontally resizable columns with drag handles between them.
 * Ratios persist to localStorage.
 */
export function HorizontalResizableColumns({
  columns,
  storageKey = 'column-ratios',
  defaultRatios,
}: HorizontalResizableColumnsProps) {
  const defaultColumnRatios = defaultRatios || columns.map(() => 1 / columns.length);
  const [savedRatios, setSavedRatios] = useLocalStorage<number[]>(storageKey, defaultColumnRatios);
  const [ratios, setRatios] = useState<number[]>(savedRatios);
  const [resizingIndex, setResizingIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startRatiosRef = useRef<number[]>([]);

  // Ensure ratios array matches columns length
  useEffect(() => {
    if (ratios.length !== columns.length) {
      const newRatios = columns.map(() => 1 / columns.length);
      setRatios(newRatios);
      setSavedRatios(newRatios);
    }
  }, [columns.length, ratios.length, setSavedRatios]);

  const handleMouseDown = useCallback(
    (index: number, e: React.MouseEvent) => {
      e.preventDefault();
      setResizingIndex(index);
      startXRef.current = e.clientX;
      startRatiosRef.current = [...ratios];
    },
    [ratios]
  );

  useEffect(() => {
    if (resizingIndex === null) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const containerWidth = containerRef.current.offsetWidth;
      const deltaX = e.clientX - startXRef.current;
      const deltaRatio = deltaX / containerWidth;

      const newRatios = [...startRatiosRef.current];

      // Get min widths as ratios
      const minRatios = columns.map((col) => {
        const minWidth = col.minWidth || 120;
        return minWidth / containerWidth;
      });

      // Adjust the column being resized and the next one
      const leftIndex = resizingIndex;
      const rightIndex = resizingIndex + 1;

      let newLeftRatio = startRatiosRef.current[leftIndex] + deltaRatio;
      let newRightRatio = startRatiosRef.current[rightIndex] - deltaRatio;

      // Enforce minimums
      if (newLeftRatio < minRatios[leftIndex]) {
        newLeftRatio = minRatios[leftIndex];
        newRightRatio = startRatiosRef.current[leftIndex] + startRatiosRef.current[rightIndex] - newLeftRatio;
      }
      if (newRightRatio < minRatios[rightIndex]) {
        newRightRatio = minRatios[rightIndex];
        newLeftRatio = startRatiosRef.current[leftIndex] + startRatiosRef.current[rightIndex] - newRightRatio;
      }

      newRatios[leftIndex] = newLeftRatio;
      newRatios[rightIndex] = newRightRatio;

      setRatios(newRatios);
    };

    const handleMouseUp = () => {
      setResizingIndex(null);
      setSavedRatios(ratios);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [resizingIndex, columns, ratios, setSavedRatios]);

  return (
    <div ref={containerRef} className="flex h-full">
      {columns.map((column, index) => (
        <div key={column.id} className="flex" style={{ flex: `${ratios[index]} 1 0%` }}>
          {/* Column content */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {/* Header */}
            <div className="px-3 py-2 border-b bg-white font-medium text-sm text-gray-700 flex-shrink-0">
              {column.header}
            </div>
            {/* Content */}
            <div className="flex-1 overflow-auto p-3">
              {column.content}
            </div>
          </div>

          {/* Resize handle (not after last column) */}
          {index < columns.length - 1 && (
            <div
              onMouseDown={(e) => handleMouseDown(index, e)}
              className={`
                w-1 cursor-ew-resize flex-shrink-0
                transition-colors
                ${resizingIndex === index ? 'bg-blue-400' : 'bg-gray-300 hover:bg-gray-400'}
              `}
            />
          )}
        </div>
      ))}
    </div>
  );
}
