import React from 'react';
import { Star, Trash2 } from 'lucide-react';
import { SavedLocationItem } from '../../types/auth';

interface SavedLocationsProps {
  locations: SavedLocationItem[];
  activeLocationName?: string | null;
  onSelectLocation: (loc: SavedLocationItem) => void;
  onRemoveLocation: (id: string, e: React.MouseEvent) => void;
}

export const SavedLocations: React.FC<SavedLocationsProps> = ({
  locations,
  activeLocationName,
  onSelectLocation,
  onRemoveLocation,
}) => {
  if (locations.length === 0) {
    return (
      <div className="py-8 px-3 text-center">
        <Star className="w-5 h-5 mx-auto mb-2 opacity-30 text-zinc-400" />
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
          No saved locations yet.
        </p>
        <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
          Click the star next to any searched location to save it for quick access.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div
        className="px-1 mb-2 text-[10px] font-semibold tracking-wider uppercase opacity-60"
        style={{ color: 'var(--text-muted)' }}
      >
        Saved Locations
      </div>

      {locations.map((loc) => {
        const isActive =
          activeLocationName &&
          loc.name.toLowerCase() === activeLocationName.toLowerCase();

        return (
          <div
            key={loc.id}
            onClick={() => onSelectLocation(loc)}
            className={`group relative flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all border ${
              isActive
                ? 'shadow-xs ring-1 ring-amber-400/30'
                : 'hover:border-zinc-700/60'
            }`}
            style={{
              backgroundColor: isActive
                ? 'var(--surface-elevated)'
                : 'rgba(255, 255, 255, 0.02)',
              borderColor: isActive ? 'var(--accent)' : 'var(--border-muted)',
              color: 'var(--text-primary)',
            }}
          >
            <div className="flex items-center gap-2.5 min-w-0 pr-6">
              <Star className="w-3.5 h-3.5 flex-shrink-0 fill-amber-400 text-amber-400" />
              <div className="truncate">
                <span className="font-medium">{loc.name}</span>
                {loc.country && (
                  <span
                    className="text-[10px] ml-1.5 opacity-60"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {loc.country}
                  </span>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={(e) => onRemoveLocation(loc.id, e)}
              title="Remove from saved"
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-rose-400 transition-all absolute right-2 text-zinc-400 cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
