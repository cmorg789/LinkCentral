import { useState, useCallback, useRef, useEffect } from 'react';

interface UseResizableOptions {
  defaultSize: number;
  minSize: number;
  maxSize: number;
  direction: 'horizontal' | 'vertical';
  onResize?: (size: number) => void;
}

interface UseResizableResult {
  size: number;
  setSize: (size: number) => void;
  handleMouseDown: (e: React.MouseEvent) => void;
  isResizing: boolean;
}

/**
 * Hook for creating resizable elements with drag handles.
 * Uses document-level mouse events for smooth dragging outside element bounds.
 */
export function useResizable({
  defaultSize,
  minSize,
  maxSize,
  direction,
  onResize,
}: UseResizableOptions): UseResizableResult {
  const [size, setSize] = useState(defaultSize);
  const [isResizing, setIsResizing] = useState(false);
  const startPosRef = useRef(0);
  const startSizeRef = useRef(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      setIsResizing(true);
      startPosRef.current = direction === 'vertical' ? e.clientY : e.clientX;
      startSizeRef.current = size;
    },
    [direction, size]
  );

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const currentPos = direction === 'vertical' ? e.clientY : e.clientX;
      // For vertical (bottom panel), dragging up increases size
      // For horizontal (columns), dragging right increases size
      const delta = direction === 'vertical'
        ? startPosRef.current - currentPos
        : currentPos - startPosRef.current;

      const newSize = Math.max(minSize, Math.min(maxSize, startSizeRef.current + delta));
      setSize(newSize);
      onResize?.(newSize);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    // Set cursor on body during resize
    document.body.style.cursor = direction === 'vertical' ? 'ns-resize' : 'ew-resize';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, direction, minSize, maxSize, onResize]);

  return {
    size,
    setSize,
    handleMouseDown,
    isResizing,
  };
}
