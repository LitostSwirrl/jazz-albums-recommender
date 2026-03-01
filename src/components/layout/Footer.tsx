export function Footer() {
  return (
    <footer className="mt-auto">
      {/* Decorative gradient line */}
      <div className="bg-gradient-to-r from-coral via-teal to-mustard h-[2px]" />
      <div className="bg-navy text-white/70 py-6">
        <div className="max-w-6xl mx-auto px-4 text-center text-sm font-mono">
          <p>A personal jazz listening guide</p>
          <p className="mt-2">
            Data sourced from Wikipedia and MusicBrainz
          </p>
        </div>
      </div>
    </footer>
  );
}
