import { BaseNode } from './BaseNode';
import { NODE_DEFINITIONS } from '../utils/nodeDefinitions';

// Create node types mapping - all use the same BaseNode component
// which renders differently based on the node type
export const nodeTypes = Object.keys(NODE_DEFINITIONS).reduce(
  (acc, type) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    acc[type] = BaseNode as any;
    return acc;
  },
  {} as Record<string, typeof BaseNode>
);
