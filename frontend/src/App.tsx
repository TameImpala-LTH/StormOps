import { useState, useCallback, lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from './components/Header';
import { QueryInput } from './components/QueryInput';
import { LoadingState } from './components/LoadingState';
import { ErrorState } from './components/ErrorState';
import { PersonalizedGreeting } from './components/PersonalizedGreeting';

const WeatherAnswerSurface = lazy(() =>
  import('./components/WeatherAnswerSurface').then((m) => ({ default: m.WeatherAnswerSurface }))
);
const ConversationThread = lazy(() =>
  import('./components/ConversationThread').then((m) => ({ default: m.ConversationThread }))
);
const Sidebar = lazy(() =>
  import('./components/sidebar/Sidebar').then((m) => ({ default: m.Sidebar }))
);
const AuthModal = lazy(() =>
  import('./components/auth/AuthModal').then((m) => ({ default: m.AuthModal }))
);
const EventsDrawer = lazy(() =>
  import('./components/events/EventsDrawer').then((m) => ({ default: m.EventsDrawer }))
);
import { postWeatherQuery } from './services/weather';
import { fetchConversationDetail } from './services/auth';
import { CoordinateInput, GeocodedLocationSchema, LanguageCode, QueryResponse } from './types/weather';
import { SavedLocationItem, ConversationDetail } from './types/auth';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { DeviceLocationProvider } from './context/DeviceLocationContext';

function AppContent() {
  const { isAuthenticated, refreshHistory } = useAuth();

  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [currentQuery, setCurrentQuery] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>('auto');

  // Sidebar, Events drawer & Auth modal states
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isEventsDrawerOpen, setIsEventsDrawerOpen] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(undefined);
  const [restoredConversation, setRestoredConversation] = useState<ConversationDetail | null>(null);

  // Persistent active location state across re-renders and page refreshes within the session
  const [persistedLocation, setPersistedLocation] = useState<GeocodedLocationSchema | null>(() => {
    try {
      const stored = sessionStorage.getItem('stormops_active_location');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const handleQuerySubmit = useCallback(
    async (
      queryText: string,
      location?: CoordinateInput,
      lang?: LanguageCode,
      customSessionId?: string
    ) => {
      setCurrentQuery(queryText);
      setIsLoading(true);
      setError(null);

      const activeLang = lang || selectedLanguage;
      try {
        const effectiveSessionId = customSessionId !== undefined ? customSessionId : activeConversationId;
        const response = await postWeatherQuery(queryText, effectiveSessionId, location, activeLang);
        setQueryResponse(response);

        if (response.session_id) {
          setActiveConversationId(response.session_id);
          // Append new messages to local thread if viewing a restored conversation
          setRestoredConversation((prev) => {
            if (!prev || prev.id !== response.session_id) return null;
            return {
              ...prev,
              messages: [
                ...prev.messages,
                {
                  id: `user-${Date.now()}`,
                  role: 'user',
                  content: queryText,
                  created_at: new Date().toISOString(),
                },
                {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: response.summary,
                  created_at: new Date().toISOString(),
                },
              ],
            };
          });
        }

        if (response.location?.name) {
          setPersistedLocation(response.location);
          try {
            sessionStorage.setItem('stormops_active_location', JSON.stringify(response.location));
          } catch {
            // Ignore
          }
        }

        // If authenticated, refresh sidebar history
        if (isAuthenticated) {
          refreshHistory();
        }
      } catch (err: unknown) {
        const errMsg =
          err instanceof Error ? err.message : "Weather query couldn't be processed right now.";
        setError(errMsg);
      } finally {
        setIsLoading(false);
      }
    },
    [selectedLanguage, isAuthenticated, refreshHistory, activeConversationId]
  );

  const handleReset = () => {
    setQueryResponse(null);
    setRestoredConversation(null);
    setCurrentQuery('');
    setError(null);
    setIsLoading(false);
    setActiveConversationId(undefined);
  };

  /**
   * Phase 15 Architectural Correction:
   * When opening a historical conversation:
   * 1. Fetch GET /api/history/{conversation_id}
   * 2. Load stored conversation messages
   * 3. Render existing conversation thread in main viewport
   * 4. Set active conversation/session ID for future follow-ups
   * 5. DO NOT re-execute previous query
   * 6. DO NOT make a new weather API request
   * 7. DO NOT create new database messages
   */
  const handleSelectConversation = async (conversationId: string) => {
    setActiveConversationId(conversationId);
    setQueryResponse(null);
    setError(null);
    try {
      setIsLoading(true);
      const detail = await fetchConversationDetail(conversationId);
      setRestoredConversation(detail);
      if (detail.location_name) {
        setPersistedLocation({
          name: detail.location_name,
          country: '',
          latitude: 0,
          longitude: 0,
          timezone: 'UTC',
        });
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Could not load conversation.';
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSavedLocation = (loc: SavedLocationItem) => {
    handleReset();
    const coords =
      typeof loc.latitude === 'number' && typeof loc.longitude === 'number'
        ? { latitude: loc.latitude, longitude: loc.longitude }
        : undefined;
    handleQuerySubmit(`What's the weather in ${loc.name}?`, coords);
  };

  const handleOpenAuthModal = (mode: 'login' | 'register') => {
    setAuthModalMode(mode);
    setIsAuthModalOpen(true);
  };

  const activeLocation = queryResponse?.location || persistedLocation;

  const isThreadActive = restoredConversation !== null && restoredConversation.messages.length > 0;

  return (
    <div className="stormops-shell transition-colors duration-300">
      {/* Ambient atmospheric backdrop */}
      <div className="stormops-atmospheric-backdrop" />

      {/* Top Header with Docked Search Slot in Intelligence State */}
      <Header
        onReset={handleReset}
        onOpenSidebar={() => setIsSidebarOpen(true)}
        onOpenAuthModal={handleOpenAuthModal}
        onOpenEvents={() => setIsEventsDrawerOpen(true)}
        isEventsOpen={isEventsDrawerOpen}
        eventCount={queryResponse?.environmental_events?.length ?? 0}
        searchSlot={
          queryResponse || isThreadActive || isLoading || error ? (
            <QueryInput
              variant="docked"
              onQuerySubmit={handleQuerySubmit}
              isLoading={isLoading}
              selectedLanguage={selectedLanguage}
              onLanguageChange={setSelectedLanguage}
              initialQuery={currentQuery}
            />
          ) : undefined
        }
      />

      {/* Events & Information Surface Drawer */}
      {isEventsDrawerOpen && (
        <Suspense fallback={null}>
          <EventsDrawer
            isOpen={isEventsDrawerOpen}
            onClose={() => setIsEventsDrawerOpen(false)}
            events={queryResponse?.environmental_events || []}
            onSelectLocation={(locationName) => {
              setIsEventsDrawerOpen(false);
              handleQuerySubmit(`What is the weather in ${locationName}?`);
            }}
            activeLocationName={activeLocation?.name}
          />
        </Suspense>
      )}

      {/* Sidebar Navigation Drawer */}
      {isSidebarOpen && (
        <Suspense fallback={null}>
          <Sidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
            onNewChat={handleReset}
            onSelectConversation={handleSelectConversation}
            onSelectSavedLocation={handleSelectSavedLocation}
            onOpenAuthModal={handleOpenAuthModal}
            activeConversationId={activeConversationId}
            activeLocationName={activeLocation?.name}
          />
        </Suspense>
      )}

      {/* Authentication Modal */}
      {isAuthModalOpen && (
        <Suspense fallback={null}>
          <AuthModal
            isOpen={isAuthModalOpen}
            onClose={() => setIsAuthModalOpen(false)}
            initialMode={authModalMode}
          />
        </Suspense>
      )}

      {/* Main Container */}
      <main className="stormops-container flex-1 py-6 sm:py-10 flex flex-col items-center">
        {/* Landing Hero Section (only when no query response, no restored thread, not loading, no error) */}
        {!queryResponse && !isThreadActive && !isLoading && !error && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
            className="stormops-discovery-canvas space-y-6 sm:space-y-8 my-auto py-8 sm:py-12"
          >
            <div className="flex flex-col items-center space-y-2.5 max-w-2xl">
              {isAuthenticated && <PersonalizedGreeting />}
              <h1
                className="type-display"
                style={{ color: 'var(--text-primary)' }}
              >
                StormOps
              </h1>
              <p
                className="type-body text-base sm:text-lg font-normal"
                style={{ color: 'var(--text-secondary)' }}
              >
                Conversational weather intelligence.
              </p>
            </div>

            <div className="w-full pt-2">
              <QueryInput
                variant="discovery"
                onQuerySubmit={handleQuerySubmit}
                isLoading={isLoading}
                selectedLanguage={selectedLanguage}
                onLanguageChange={setSelectedLanguage}
              />
            </div>
          </motion.div>
        )}

        {/* Content Reveal Area */}
        <AnimatePresence mode="wait">
          {/* Loading State */}
          {isLoading && (
            <LoadingState key="loading" locationName={currentQuery || restoredConversation?.location_name || 'location'} />
          )}

          {/* Error State */}
          {!isLoading && error && (
            <ErrorState
              key="error"
              message={error}
              onRetry={() => currentQuery && handleQuerySubmit(currentQuery)}
            />
          )}

          {/* Restored Conversation Thread View */}
          {!isLoading && !error && isThreadActive && (
            <motion.div
              key={`thread-${restoredConversation.id}`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="w-full"
            >
              <Suspense fallback={null}>
                <ConversationThread
                  messages={restoredConversation.messages}
                  locationName={restoredConversation.location_name}
                  title={restoredConversation.title}
                />
              </Suspense>
            </motion.div>
          )}

          {/* Single Unified Weather Answer Surface (for new live weather answers) */}
          {!isLoading && !error && queryResponse && (
            <motion.div
              key={queryResponse.timestamp || 'results'}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              className="w-full"
            >
              <Suspense
                fallback={
                  <LoadingState locationName={currentQuery || 'location'} />
                }
              >
                <WeatherAnswerSurface
                  response={queryResponse}
                  onSelectPresetLocation={(cityName) =>
                    handleQuerySubmit(`What's the weather in ${cityName}?`)
                  }
                  onOpenAuthModal={handleOpenAuthModal}
                />
              </Suspense>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer
        className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-6 text-center text-xs font-mono"
        style={{
          borderTop: '1px solid var(--border-subtle)',
          color: 'var(--text-tertiary)',
        }}
      >
        WeatherGPT &copy; 2026 — Built on StormOps Meteorological Architecture
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <DeviceLocationProvider>
          <AppContent />
        </DeviceLocationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
