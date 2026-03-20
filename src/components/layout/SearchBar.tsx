import { useState, useRef, useEffect } from 'react';

interface SearchBarProps {
  onOpenChange?: (isOpen: boolean) => void;
}

export function SearchBar({ onOpenChange }: SearchBarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const iconRef = useRef<HTMLButtonElement>(null);

  const open = () => {
    setIsOpen(true);
    onOpenChange?.(true);
  };

  const close = () => {
    setIsOpen(false);
    onOpenChange?.(false);
    iconRef.current?.focus();
  };

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  return (
    <div className="relative">
      {isOpen ? (
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-warm-gray shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            role="searchbox"
            aria-label="Search artists and albums"
            placeholder="Search artists, albums..."
            className="bg-transparent border-b border-warm-gray/40 text-charcoal text-sm outline-none flex-1 min-w-0 md:w-56 py-1 placeholder:text-warm-gray/60 focus:border-coral transition-colors"
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                e.stopPropagation();
                close();
              }
            }}
          />
          <button
            onClick={close}
            className="text-warm-gray hover:text-charcoal transition-colors p-0.5 focus:outline-none focus:ring-2 focus:ring-coral rounded"
            aria-label="Close search"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      ) : (
        <button
          ref={iconRef}
          onClick={open}
          className="text-warm-gray hover:text-coral transition-colors p-1 focus:outline-none focus:ring-2 focus:ring-coral focus:ring-offset-2 focus:ring-offset-cream rounded"
          aria-label="Open search"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
      )}
    </div>
  );
}
