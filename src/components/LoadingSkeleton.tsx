export function LoadingSkeleton() {
  return (
    <div className="min-h-screen bg-cream flex items-center justify-center">
      <div className="flex flex-col items-center gap-6">
        <div className="geometric-spinner" />
        <div className="font-mono uppercase tracking-wider text-warm-gray text-sm">
          Loading...
        </div>
      </div>
    </div>
  );
}
