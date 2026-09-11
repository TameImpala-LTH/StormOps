import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Plus,
  Compass,
  Star,
  Clock,
  Calendar,
  LogOut,
  LogIn,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { HistoryList } from './HistoryList';
import { SavedLocations } from './SavedLocations';
import { EnvironmentalOutlook } from './EnvironmentalOutlook';
import { SavedLocationItem, EnvironmentalOutlookItem } from '../../types/auth';
import { fetchEnvironmentalOutlook } from '../../services/auth';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
  onSelectSavedLocation: (loc: SavedLocationItem) => void;
  onOpenAuthModal: (mode: 'login' | 'register') => void;
  activeConversationId?: string;
  activeLocationName?: string | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  onSelectConversation,
  onSelectSavedLocation,
  onOpenAuthModal,
  activeConversationId,
  activeLocationName,
}) => {
  const [activeTab, setActiveTab] = useState<'history' | 'saved' | 'outlook'>('history');
  const [outlookItems, setOutlookItems] = useState<EnvironmentalOutlookItem[]>([]);
  const [locationsEvaluated, setLocationsEvaluated] = useState<string[]>([]);
  const [isOutlookLoading, setIsOutlookLoading] = useState<boolean>(false);

  const {
    user,
    isAuthenticated,
    history,
    savedLocations,
    deleteConversation,
    removeSavedLocation,
    logout,
  } = useAuth();

  // Load deterministic environmental outlook via backend endpoint whenever savedLocations or active location changes
  useEffect(() => {
    let isMounted = true;

    if (!isAuthenticated) {
      setOutlookItems([]);
      setLocationsEvaluated([]);
      return;
    }

    const loadOutlook = async () => {
      setIsOutlookLoading(true);
      try {
        const data = await fetchEnvironmentalOutlook(activeLocationName);
        if (isMounted) {
          setOutlookItems(data.items || []);
          setLocationsEvaluated(data.locations_evaluated || []);
        }
      } catch {
        if (isMounted) {
          setOutlookItems([]);
          setLocationsEvaluated([]);
        }
      } finally {
        if (isMounted) {
          setIsOutlookLoading(false);
        }
      }
    };

    loadOutlook();

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, activeLocationName, savedLocations]);

  return (
    <>
      {/* Mobile Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-xs md:hidden"
          />
        )}
      </AnimatePresence>

      {/* Drawer panel */}
      <div
        className={`fixed top-0 bottom-0 left-0 z-50 w-80 flex flex-col transition-transform duration-300 ease-in-out border-r ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{
          backgroundColor: 'var(--surface)',
          borderColor: 'var(--border)',
          color: 'var(--text-primary)',
        }}
      >
        {/* Header */}
        <div
          className="p-4 flex items-center justify-between border-b"
          style={{ borderColor: 'var(--border-muted)' }}
        >
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            <span className="text-sm font-semibold tracking-tight">StormOps</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:opacity-75 transition-opacity"
            style={{ color: 'var(--text-secondary)' }}
            aria-label="Close sidebar"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <button
            onClick={() => {
              onNewChat();
              onClose();
            }}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-medium transition-all cursor-pointer border"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              borderColor: 'var(--border-muted)',
              color: 'var(--text-primary)',
            }}
          >
            <Plus className="w-4 h-4" />
            <span>New Weather Query</span>
          </button>
        </div>

        {/* Tabs: Timeline vs Saved vs Outlook */}
        <div className="px-3 pt-1 pb-2">
          <div
            className="grid grid-cols-3 p-1 rounded-xl text-xs font-medium border gap-0.5"
            style={{
              backgroundColor: 'var(--bg)',
              borderColor: 'var(--border-muted)',
            }}
          >
            {/* Timeline Tab */}
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center justify-center gap-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeTab === 'history' ? 'shadow-xs' : 'opacity-60 hover:opacity-100'
              }`}
              style={{
                backgroundColor: activeTab === 'history' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'history' ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}
            >
              <Clock className="w-3.5 h-3.5" />
              <span className="truncate">Timeline</span>
              {history.length > 0 && (
                <span className="text-[9px] px-1 rounded-full bg-zinc-800 text-zinc-300">
                  {history.length}
                </span>
              )}
            </button>

            {/* Saved Tab */}
            <button
              onClick={() => setActiveTab('saved')}
              className={`flex items-center justify-center gap-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeTab === 'saved' ? 'shadow-xs' : 'opacity-60 hover:opacity-100'
              }`}
              style={{
                backgroundColor: activeTab === 'saved' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'saved' ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}
            >
              <Star className="w-3.5 h-3.5" />
              <span className="truncate">Saved</span>
              {savedLocations.length > 0 && (
                <span className="text-[9px] px-1 rounded-full bg-zinc-800 text-zinc-300">
                  {savedLocations.length}
                </span>
              )}
            </button>

            {/* Outlook Tab */}
            <button
              onClick={() => setActiveTab('outlook')}
              className={`flex items-center justify-center gap-1 py-1.5 rounded-lg transition-all cursor-pointer ${
                activeTab === 'outlook' ? 'shadow-xs' : 'opacity-60 hover:opacity-100'
              }`}
              style={{
                backgroundColor: activeTab === 'outlook' ? 'var(--surface)' : 'transparent',
                color: activeTab === 'outlook' ? 'var(--text-primary)' : 'var(--text-secondary)',
              }}
            >
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <span className="truncate">Outlook</span>
              {outlookItems.length > 0 && (
                <span className="text-[9px] px-1 rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/50 font-mono">
                  {outlookItems.length}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto px-3 py-1">
          {activeTab === 'history' ? (
            !isAuthenticated ? (
              <div className="py-8 px-4 text-center">
                <UserIcon className="w-8 h-8 mx-auto mb-2 opacity-30 text-zinc-400" />
                <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                  Personal History
                </p>
                <p className="text-[11px] mt-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
                  Sign in to keep your search history synchronized across sessions.
                </p>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      onOpenAuthModal('login');
                      onClose();
                    }}
                    className="w-full py-2 rounded-xl text-xs font-medium transition-all cursor-pointer"
                    style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }}
                  >
                    Sign In
                  </button>
                </div>
              </div>
            ) : (
              <HistoryList
                conversations={history}
                activeConversationId={activeConversationId}
                onSelectConversation={(id) => {
                  onSelectConversation(id);
                  onClose();
                }}
                onDeleteConversation={(id, e) => {
                  e.stopPropagation();
                  deleteConversation(id);
                  if (activeConversationId === id) {
                    onNewChat();
                  }
                }}
              />
            )
          ) : activeTab === 'saved' ? (
            !isAuthenticated ? (
              <div className="py-8 px-4 text-center">
                <Star className="w-8 h-8 mx-auto mb-2 opacity-30 text-zinc-400" />
                <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
                  Saved Locations
                </p>
                <p className="text-[11px] mt-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
                  Sign in to star your favorite cities and access them instantly.
                </p>
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => {
                      onOpenAuthModal('login');
                      onClose();
                    }}
                    className="w-full py-2 rounded-xl text-xs font-medium transition-all cursor-pointer"
                    style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }}
                  >
                    Sign In
                  </button>
                </div>
              </div>
            ) : (
              <SavedLocations
                locations={savedLocations}
                activeLocationName={activeLocationName}
                onSelectLocation={(loc) => {
                  onSelectSavedLocation(loc);
                  onClose();
                }}
                onRemoveLocation={(id, e) => {
                  e.stopPropagation();
                  removeSavedLocation(id);
                }}
              />
            )
          ) : (
            /* Environmental Outlook Tab */
            <EnvironmentalOutlook
              items={outlookItems}
              locationsEvaluated={locationsEvaluated}
              isLoading={isOutlookLoading}
              isAuthenticated={isAuthenticated}
              onOpenAuthModal={() => {
                onOpenAuthModal('login');
                onClose();
              }}
              onSelectLocation={(locName) => {
                onSelectSavedLocation({
                  id: '',
                  user_id: '',
                  name: locName,
                  latitude: 0,
                  longitude: 0,
                  created_at: '',
                });
                onClose();
              }}
            />
          )}
        </div>

        {/* User footer */}
        <div
          className="p-3 border-t"
          style={{ borderColor: 'var(--border-muted)', backgroundColor: 'var(--surface-elevated)' }}
        >
          {isAuthenticated && user ? (
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5 min-w-0 pr-2">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold uppercase"
                  style={{ backgroundColor: 'var(--accent)', color: '#ffffff' }}
                >
                  {user.display_name.charAt(0)}
                </div>
                <div className="truncate">
                  <div className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                    {user.display_name}
                  </div>
                  <div className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>
                    {user.email}
                  </div>
                </div>
              </div>
              <button
                onClick={() => {
                  logout();
                  onClose();
                }}
                title="Sign Out"
                aria-label="Sign Out"
                className="p-1.5 rounded-lg hover:bg-zinc-800/40 transition-colors cursor-pointer text-zinc-400 hover:text-rose-400"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                Guest Visitor
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onOpenAuthModal('login');
                    onClose();
                  }}
                  className="flex items-center gap-1 text-xs font-medium hover:underline cursor-pointer"
                  style={{ color: 'var(--accent)' }}
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Sign In</span>
                </button>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>·</span>
                <button
                  type="button"
                  onClick={() => {
                    onOpenAuthModal('register');
                    onClose();
                  }}
                  className="text-xs font-medium hover:underline cursor-pointer"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  Sign Up
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
};
