import { useState, useCallback } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
} from '@xyflow/react';
import type { Edge, EdgeProps } from '@xyflow/react';

export type ConnectionEdgeData = {
  explanation?: string;
  verified?: boolean;
};

type ConnectionEdgeType = Edge<ConnectionEdgeData, 'connection'>;

export function ConnectionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps<ConnectionEdgeType>) {
  const [showTooltip, setShowTooltip] = useState(false);

  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const explanation = data?.explanation;
  const verified = data?.verified ?? false;

  const handleMouseEnter = useCallback(() => {
    if (explanation) setShowTooltip(true);
  }, [explanation]);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
  }, []);

  return (
    <>
      {/* Invisible wider path for easier hover targeting */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      />
      <BaseEdge
        id={id}
        path={edgePath}
        style={style}
        markerEnd={markerEnd}
      />
      {showTooltip && explanation && (
        <EdgeLabelRenderer>
          <div
            className="absolute pointer-events-none px-3 py-2 rounded-lg bg-navy border border-white/10 shadow-elevated max-w-[280px] z-50"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
          >
            <p className="text-xs text-white/80 leading-relaxed">{explanation}</p>
            {verified && (
              <span className="inline-flex items-center gap-1 mt-1 text-teal text-[10px]">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Sourced
              </span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
