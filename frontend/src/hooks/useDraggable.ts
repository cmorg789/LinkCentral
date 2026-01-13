import { useState, useCallback, useRef, useEffect } from 'react';

interface Position {
  x: number;
  y: number;
}

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

interface UseDraggableOptions {
  defaultPosition: Position;
  bounds?: Bounds;
  onDragEnd?: (position: Position) => void;
}

interface UseDraggableResult {
  position: Position;
  setPosition: (pos: Position) => void;
  handleMouseDown: (e: React.MouseEvent) => void;
  isDragging: boolean;
}

/**
 * Hook for creating draggable elements.
 * Uses document-level mouse events for smooth dragging.
 */
export function useDraggable({
  defaultPosition,
  bounds,
  onDragEnd,
}: UseDraggableOptions): UseDraggableResult {
  const [position, setPosition] = useState<Position>(defaultPosition);
  const [isDragging, setIsDragging] = useState(false);
  const startMouseRef = useRef<Position>({ x: 0, y: 0 });
  const startPosRef = useRef<Position>({ x: 0, y: 0 });

  const constrainPosition = useCallback(
    (pos: Position): Position => {
      if (!bounds) return pos;
      return {
        x: Math.max(bounds.minX, Math.min(bounds.maxX, pos.x)),
        y: Math.max(bounds.minY, Math.min(bounds.maxY, pos.y)),
      };
    },
    [bounds]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();

      setIsDragging(true);
      startMouseRef.current = { x: e.clientX, y: e.clientY };
      startPosRef.current = position;
    },
    [position]
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = e.clientX - startMouseRef.current.x;
      const deltaY = e.clientY - startMouseRef.current.y;

      const newPosition = constrainPosition({
        x: startPosRef.current.x + deltaX,
        y: startPosRef.current.y + deltaY,
      });

      setPosition(newPosition);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      onDragEnd?.(position);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    document.body.style.cursor = 'grabbing';
    document.body.style.userSelect = 'none';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isDragging, constrainPosition, onDragEnd, position]);

  return {
    position,
    setPosition,
    handleMouseDown,
    isDragging,
  };
}
