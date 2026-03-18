import { useRef, useState, useEffect } from 'react';

interface LazySectionProps {
  children: React.ReactNode;
  rootMargin?: string;
  className?: string;
}

// Only mounts children when the section enters (or is near) the viewport.
// Uses a placeholder with min-height to prevent layout shift.
export function LazySection({ children, rootMargin = '200px', className = '' }: LazySectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [rootMargin]);

  return (
    <div ref={ref} className={className}>
      {visible ? children : <div className="h-48" />}
    </div>
  );
}
