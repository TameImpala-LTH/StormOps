import React, { useState, useEffect } from 'react';
import { Compass, Menu, User as UserIcon, Search, X } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { LiveWeatherHeader } from './LiveWeatherHeader';
import { useAuth } from '../context/AuthContext';
import { useDeviceLocation } from '../context/DeviceLocationContext';

export interface HeaderProps {
  onReset?: () => void;
  onOpenSidebar?: () => void;
  onOpenAuthModal?: (mode: 'login' | 'register') => void;
  searchSlot?: React.ReactNode;
}

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < 768;
    }
    return false;
  });

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
}

export const Header: React.FC<HeaderProps> = ({
  onReset,
  onOpenSidebar,
  onOpenAuthModal,
  searchSlot,
}) => {
  const { user, isAuthenticated } = useAuth();
  const { deviceLocation, deviceTemperature, isLocating, requestDeviceLocation } = useDeviceLocation();
  const [isMobileSearchOpen, setIsMobileSearchOpen] = useState(false);
  const isMobile = useIsMobile();

  // Close mobile search on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobileSearchOpen) {
        setIsMobileSearchOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMobileSearchOpen]);

  // When reset is called, also close mobile search
  const handleBrandReset = () => {
    setIsMobileSearchOpen(false);
    onReset?.();
  };

  // The LiveWeatherHeader strictly represents the current device location and temperature.
  const displayLocation = deviceLocation;
  const displayTemperature = deviceTemperature;

  return (
    <header className="stormops-header transition-colors">
      <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2 sm:gap-4">
        {/* Brand & Drawer Toggle */}
        <div className="flex items-center space-x-2.5 sm:space-x-3 shrink-0">
          {onOpenSidebar && (
            <button
              type="button"
              onClick={onOpenSidebar}
              aria-label="Open sidebar navigation"
              className="p-2 rounded-xl border transition-opacity hover:opacity-80 cursor-pointer flex items-center justify-center"
              style={{
                backgroundColor: 'var(--surface-elevated)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            >
              <Menu className="w-4 h-4" />
            </button>
          )}

          <div
            onClick={handleBrandReset}
            className="flex items-center space-x-2.5 sm:space-x-3 cursor-pointer group transition-opacity hover:opacity-75 shrink-0"
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
              style={{
                backgroundColor: 'var(--icon-bg)',
                border: '1px solid var(--icon-border)',
              }}
            >
              <Compass className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
            </div>
            <div>
              <span
                className="text-base font-medium tracking-tight"
                style={{ color: 'var(--text-primary)' }}
              >
                StormOps
              </span>
              <span
                className="text-xs ml-2 font-mono uppercase tracking-wider hidden sm:inline"
                style={{ color: 'var(--text-tertiary)' }}
              >
                WeatherGPT
              </span>
            </div>
          </div>
        </div>

        {/* Center Docked Search Slot (Desktop & Tablet) - Rendered strictly when NOT mobile to prevent duplicate inputs */}
        {searchSlot && !isMobile && (
          <div className="flex flex-1 max-w-md xl:max-w-lg 2xl:max-w-xl mx-2 lg:mx-4 min-w-[180px]">
            {searchSlot}
          </div>
        )}

        {/* Right side: persistent live weather/time header + theme switcher + Auth/Avatar + Mobile Search Toggle */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0">
          {/* Mobile search trigger affordance (only when searchSlot exists and viewport is mobile) */}
          {searchSlot && isMobile && (
            <button
              type="button"
              onClick={() => setIsMobileSearchOpen((prev) => !prev)}
              aria-expanded={isMobileSearchOpen}
              aria-label={isMobileSearchOpen ? 'Close search' : 'Search location or weather'}
              className="p-2 rounded-xl border transition-colors cursor-pointer flex items-center justify-center"
              style={{
                backgroundColor: isMobileSearchOpen ? 'var(--surface-elevated)' : 'transparent',
                borderColor: isMobileSearchOpen ? 'var(--border-strong)' : 'var(--border-subtle)',
                color: isMobileSearchOpen ? 'var(--accent-primary)' : 'var(--text-primary)',
              }}
            >
              {isMobileSearchOpen ? <X className="w-4 h-4" /> : <Search className="w-4 h-4" />}
            </button>
          )}

          <LiveWeatherHeader
            location={displayLocation}
            temperature={displayTemperature}
            isLocating={isLocating}
            onRequestLocation={requestDeviceLocation}
          />
          <ThemeToggle />

          {isAuthenticated && user ? (
            <button
              type="button"
              onClick={onOpenSidebar}
              title={`${user.display_name} (${user.email})`}
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold uppercase cursor-pointer transition-transform hover:scale-105 border"
              style={{
                backgroundColor: 'var(--accent-primary)',
                color: '#ffffff',
                borderColor: 'var(--border-subtle)',
              }}
            >
              {user.display_name.charAt(0)}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onOpenAuthModal?.('login')}
              aria-label="Sign In"
              className="px-3 py-1.5 rounded-xl text-xs font-medium border transition-all hover:opacity-80 cursor-pointer flex items-center space-x-1.5"
              style={{
                backgroundColor: 'var(--surface-elevated)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            >
              <UserIcon className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
              <span className="hidden sm:inline">Sign In</span>
            </button>
          )}
        </div>
      </div>

      {/* Mobile Expandable Docked Search Slot - Rendered strictly when mobile and toggled open */}
      {searchSlot && isMobile && isMobileSearchOpen && (
        <div className="w-full pb-3 px-4 transition-all">
          {searchSlot}
        </div>
      )}
    </header>
  );
};
