export function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
      <div className="animate-pulse flex flex-col items-center gap-4">
        <div className="w-16 h-16 bg-zinc-800 rounded-full" />
        <div className="w-32 h-4 bg-zinc-800 rounded" />
        <div className="text-zinc-600 text-sm">Loading...</div>
      </div>
    </div>
  );
}
