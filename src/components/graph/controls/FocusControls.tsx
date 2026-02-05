import type { Artist } from '../../../types';

interface FocusControlsProps {
  focusArtist: Artist | null;
  depth: number;
  onDepthChange: (depth: number) => void;
  onClearFocus: () => void;
}

export function FocusControls({ focusArtist, depth, onDepthChange, onClearFocus }: FocusControlsProps) {
  if (!focusArtist) return null;

  return (
    <div className="bg-zinc-900 border border-cyan-500/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-sm text-zinc-400">Focused on: </span>
          <span className="text-cyan-400 font-semibold">{focusArtist.name}</span>
        </div>
        <button
          onClick={onClearFocus}
          className="text-zinc-500 hover:text-white transition-colors"
          title="Clear focus"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-zinc-400">Network depth:</span>
        <div className="flex gap-1">
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              onClick={() => onDepthChange(d)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                depth === d
                  ? 'bg-cyan-600 text-white'
                  : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
              }`}
            >
              {d}-hop
            </button>
          ))}
        </div>
      </div>

      <div className="mt-2 text-xs text-zinc-500">
        Showing artists within {depth} step{depth > 1 ? 's' : ''} of {focusArtist.name}
      </div>
    </div>
  );
}
