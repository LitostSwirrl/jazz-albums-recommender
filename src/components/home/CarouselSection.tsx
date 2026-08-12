interface CarouselSectionProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

export function CarouselSection({ title, subtitle, children, className = '' }: CarouselSectionProps) {
  return (
    <section className={`mb-10 ${className}`}>
      <div className="mb-4">
        <h2 className="text-xl font-heading text-charcoal">{title}</h2>
        {subtitle && (
          <p className="text-warm-gray text-sm mt-0.5">{subtitle}</p>
        )}
      </div>
      {children}
    </section>
  );
}
