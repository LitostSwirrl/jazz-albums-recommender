import type { HistoricalEventCategory } from '../../types';
import { getCategoryConfig } from '../../utils/historicalContext';
import { EventCategoryIcon } from '../icons/EventCategoryIcon';

interface CategoryBadgeProps {
  category: HistoricalEventCategory;
  size?: 'sm' | 'md';
}

export function CategoryBadge({ category, size = 'sm' }: CategoryBadgeProps) {
  const config = getCategoryConfig(category);
  const isSmall = size === 'sm';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${
        isSmall ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'
      }`}
      style={{ backgroundColor: config.color + '20', color: config.color }}
    >
      <EventCategoryIcon category={category} className={isSmall ? 'w-3 h-3' : 'w-4 h-4'} />
      {config.label}
    </span>
  );
}
