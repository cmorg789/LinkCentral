import { useEffect } from 'react';
import { useResizable } from '@/hooks/useResizable';
import { useLocalStorage } from '@/hooks/useLocalStorage';

interface ResizableBottomPanelProps {
  isVisible: boolean;
  children: React.ReactNode;
  minHeight?: number;
  maxHeightPercent?: number;
  defaultHeight?: number;
  storageKey?: string;
}

/**
 * Bottom panel with vertical resize handle.
 * Height persists to localStorage.
 */
export function ResizableBottomPanel({
  isVisible,
  children,
  minHeight = 200,
  maxHeightPercent = 60,
  defaultHeight = 300,
  storageKey = 'bottom-panel-height',
}: ResizableBottomPanelProps) {
  const [savedHeight, setSavedHeight] = useLocalStorage(storageKey, defaultHeight);

  const maxHeight = Math.floor((window.innerHeight * maxHeightPercent) / 100);

  const { size: height, setSize: setHeight, handleMouseDown, isResizing } = useResizable({
    defaultSize: savedHeight,
    minSize: minHeight,
    maxSize: maxHeight,
    direction: 'vertical',
    onResize: setSavedHeight,
  });

  // Sync with saved height on mount
  useEffect(() => {
    setHeight(savedHeight);
  }, [savedHeight, setHeight]);

  if (!isVisible) return null;

  return (
    <div
      className="flex flex-col border-t bg-gray-50"
      style={{ height: `${height}px`, flexShrink: 0 }}
    >
      {/* Resize handle */}
      <div
        onMouseDown={handleMouseDown}
        className={`
          h-2 cursor-ns-resize flex items-center justify-center
          transition-colors
          ${isResizing ? 'bg-blue-200' : 'bg-gray-200 hover:bg-gray-300'}
        `}
      >
        <div className="w-12 h-1 bg-gray-400 rounded-full" />
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  );
}
