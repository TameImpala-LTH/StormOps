import React from 'react';
import { Compass, Menu, User as UserIcon } from 'lucide-react';
import { ThemeToggle } from './ThemeToggle';
import { LiveWeatherHeader } from './LiveWeatherHeader';
import { useAuth } from '../context/AuthContext';
import { useDeviceLocation } from '../context/DeviceLocationContext';

interface HeaderProps {
  onReset?: () => void;
  onOpenSidebar?: () => void;
  onOpenAuthModal?: (mode: 'login' | 'register') => void;
}

export const Header: React.FC<HeaderProps> = ({
  onReset,
  onOpenSidebar,
  onOpenAuthModal,
}) => {
  const { user, isAuthenticated } = useAuth();
  const { deviceLocation, deviceTemperature } = useDeviceLocation();

  // The LiveWeatherHeader strictly represents the current device location and temperature.
  const displayLocation = deviceLocation;
  const displayTemperature = deviceTemperature;

  return (
    <header
      className="w-full relative"
      style={{ borderBottom: '1px solid var(--border-header)' }}
    >
      <div className="w-full max-w-5xl mx-auto px-6 py-5 flex items-center justify-between gap-4">
        {/* Brand & Drawer Toggle */}
      <div className="flex items-center space-x-3">
        {onOpenSidebar && (
          <button
            type="button"
            onClick={onOpenSidebar}
            aria-label="Open sidebar navigation"
            className="p-2 rounded-xl border transition-opacity hover:opacity-80 cursor-pointer flex items-center justify-center"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              borderColor: 'var(--border-muted)',
              color: 'var(--text-primary)',
            }}
          >
            <Menu className="w-4 h-4" />
          </button>
        )}

        <div
          onClick={onReset}
          className="flex items-center space-x-3 cursor-pointer group transition-opacity hover:opacity-75 flex-shrink-0"
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
            style={{
              backgroundColor: 'var(--icon-bg)',
              border: '1px solid var(--icon-border)',
            }}
          >
            <Compass className="w-4 h-4" style={{ color: 'var(--accent)' }} />
          </div>
          <div>
            <span
              className="text-base font-medium tracking-tight"
              style={{ color: 'var(--text-primary)' }}
            >
              StormOps
            </span>
            <span
              className="text-xs ml-2 font-mono uppercase tracking-wider"
              style={{ color: 'var(--text-muted)' }}
            >
              WeatherGPT
            </span>
          </div>
        </div>
      </div>

      {/* Right side: persistent live weather/time header + theme switcher + Auth/Avatar */}
      <div className="flex items-center space-x-1.5 sm:space-x-3 shrink-0">
        <LiveWeatherHeader location={displayLocation} temperature={displayTemperature} />
        <ThemeToggle />

        {isAuthenticated && user ? (
          <button
            type="button"
            onClick={onOpenSidebar}
            title={`${user.display_name} (${user.email})`}
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold uppercase cursor-pointer transition-transform hover:scale-105 border"
            style={{
              backgroundColor: 'var(--accent)',
              color: '#ffffff',
              borderColor: 'var(--border-muted)',
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
              borderColor: 'var(--border-muted)',
              color: 'var(--text-primary)',
            }}
          >
            <UserIcon className="w-3.5 h-3.5" style={{ color: 'var(--accent)' }} />
            <span className="hidden sm:inline">Sign In</span>
          </button>
        )}
      </div>
    </div>
  </header>
);
};
