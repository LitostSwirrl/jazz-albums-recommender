import { Link } from 'react-router-dom';

interface CarouselSectionProps {
  title: string;
  subtitle?: string;
  linkTo?: string;
  linkLabel?: string;
  children: React.ReactNode;
  className?: string;
}

export function CarouselSection({ title, subtitle, linkTo, linkLabel = 'See all', children, className = '' }: CarouselSectionProps) {
  return (
    <section className={`mb-10 ${className}`}>
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <h2 className="text-xl font-heading text-charcoal">{title}</h2>
          {subtitle && (
            <p className="text-warm-gray text-sm mt-0.5">{subtitle}</p>
          )}
        </div>
        {linkTo && (
          <Link
            to={linkTo}
            className="text-coral hover:text-coral/80 text-sm transition-colors flex-shrink-0 ml-4"
          >
            {linkLabel} &rarr;
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}
