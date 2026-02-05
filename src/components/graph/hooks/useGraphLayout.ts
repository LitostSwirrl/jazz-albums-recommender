import { useMemo } from 'react';
import dagre from 'dagre';
import type { Node, Edge } from '@xyflow/react';
import type { GraphNode } from './useInfluenceGraph';

interface LayoutOptions {
  direction?: 'TB' | 'BT' | 'LR' | 'RL';
  nodeSpacing?: number;
  rankSpacing?: number;
}

const nodeSizeMap = {
  sm: { width: 140, height: 70 },
  md: { width: 160, height: 80 },
  lg: { width: 180, height: 90 },
  xl: { width: 200, height: 100 },
};

export function useGraphLayout(
  nodes: GraphNode[],
  edges: Edge[],
  options: LayoutOptions = {}
): { nodes: Node[]; edges: Edge[] } {
  const { direction = 'TB', nodeSpacing = 50, rankSpacing = 100 } = options;

  return useMemo(() => {
    if (nodes.length === 0) {
      return { nodes: [], edges };
    }

    const g = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

    g.setGraph({
      rankdir: direction,
      nodesep: nodeSpacing,
      ranksep: rankSpacing,
      marginx: 50,
      marginy: 50,
    });

    // Add nodes with dynamic sizes based on influence
    nodes.forEach((node) => {
      const size = nodeSizeMap[node.data.size];
      g.setNode(node.id, { width: size.width, height: size.height });
    });

    // Add edges
    edges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    // Run layout
    dagre.layout(g);

    // Apply positions to nodes
    const layoutedNodes = nodes.map((node) => {
      const position = g.node(node.id);
      const size = nodeSizeMap[node.data.size];

      return {
        ...node,
        position: {
          x: position.x - size.width / 2,
          y: position.y - size.height / 2,
        },
      };
    });

    return { nodes: layoutedNodes, edges };
  }, [nodes, edges, direction, nodeSpacing, rankSpacing]);
}

// Alternative: simple radial layout for mini-networks
export function useRadialLayout(
  centerNode: GraphNode,
  surroundingNodes: GraphNode[],
  edges: Edge[],
  radius: number = 150
): { nodes: Node[]; edges: Edge[] } {
  return useMemo(() => {
    const nodes: Node[] = [
      {
        ...centerNode,
        position: { x: 0, y: 0 },
      },
    ];

    const angleStep = (2 * Math.PI) / surroundingNodes.length;

    surroundingNodes.forEach((node, i) => {
      const angle = i * angleStep - Math.PI / 2; // Start from top
      nodes.push({
        ...node,
        position: {
          x: radius * Math.cos(angle),
          y: radius * Math.sin(angle),
        },
      });
    });

    return { nodes, edges };
  }, [centerNode, surroundingNodes, edges, radius]);
}
