import type { HistoricalEventCategory } from '../../types';
import { EVENT_CATEGORIES, ALL_CATEGORIES } from '../../utils/historicalContext';
import { EventCategoryIcon } from '../icons/EventCategoryIcon';

interface CategoryFilterProps {
  activeCategories: HistoricalEventCategory[];
  onToggle: (category: HistoricalEventCategory) => void;
}

export function CategoryFilter({ activeCategories, onToggle }: CategoryFilterProps) {
  const allActive = activeCategories.length === 0;

  return (
    <div className="flex flex-wrap gap-2">
      {ALL_CATEGORIES.map((category) => {
        const config = EVENT_CATEGORIES[category];
        const isActive = allActive || activeCategories.includes(category);

        return (
          <button
            key={category}
            onClick={() => onToggle(category)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
              isActive
                ? 'ring-1'
                : 'opacity-40 hover:opacity-70'
            }`}
            style={{
              backgroundColor: isActive ? config.color + '20' : 'transparent',
              color: config.color,
              '--tw-ring-color': isActive ? config.color + '80' : undefined,
            } as React.CSSProperties}
            aria-pressed={isActive}
          >
            <EventCategoryIcon category={category} className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{config.label}</span>
          </button>
        );
      })}
    </div>
  );
}
