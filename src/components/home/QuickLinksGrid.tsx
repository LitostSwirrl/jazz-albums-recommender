import { Link } from 'react-router-dom';

interface QuickLink {
  title: string;
  description: string;
  to: string;
  icon: React.ReactNode;
}

const links: QuickLink[] = [
  {
    title: 'Browse All Eras',
    description: '8 distinct periods of jazz history',
    to: '/eras',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: 'Timeline',
    description: 'Jazz evolution from 1900 to now',
    to: '/timeline',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
      </svg>
    ),
  },
  {
    title: 'Artist Connections',
    description: '377 verified influence links',
    to: '/influence',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
  },
  {
    title: 'Jazz & Society',
    description: 'Music in historical context',
    to: '/context',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: 'All Albums',
    description: '1000 curated jazz albums',
    to: '/albums',
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
  },
];

export function QuickLinksGrid() {
  return (
    <section className="mb-10">
      <h2 className="text-xl font-heading text-charcoal mb-4">Explore</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {links.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className="p-4 rounded-lg bg-surface border border-border hover:border-coral/30 hover:shadow-card-hover transition-all duration-300 group"
          >
            <div className="text-warm-gray group-hover:text-coral transition-colors mb-2">
              {link.icon}
            </div>
            <h3 className="font-semibold text-charcoal text-sm group-hover:text-coral transition-colors">
              {link.title}
            </h3>
            <p className="text-warm-gray text-xs mt-1">{link.description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
