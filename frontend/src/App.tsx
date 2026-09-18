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

  // Sidebar & Auth modal states
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
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
    <div
      className="min-h-screen flex flex-col transition-colors duration-300 relative selection:bg-sky-500/30 selection:text-sky-200"
      style={{
        backgroundColor: 'var(--bg)',
        color: 'var(--text-primary)',
      }}
    >
      {/* Subtle background radial accent glow for night theme */}
      <div
        className="fixed inset-0 pointer-events-none transition-opacity duration-700 -z-10 opacity-0 dark:opacity-0 night:opacity-100"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(56, 189, 248, 0.04), transparent 70%)',
        }}
      />

      {/* Top Header */}
      <Header
        onReset={handleReset}
        onOpenSidebar={() => setIsSidebarOpen(true)}
        onOpenAuthModal={handleOpenAuthModal}
      />

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
      <main className="flex-1 w-full max-w-5xl mx-auto px-6 py-12 flex flex-col items-center">
        {/* Landing Hero Section (only when no query response, no restored thread, not loading, no error) */}
        {!queryResponse && !isThreadActive && !isLoading && !error && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full flex flex-col items-center text-center my-auto py-12 space-y-8"
          >
            <div className="flex flex-col items-center space-y-3 max-w-2xl">
              {isAuthenticated && <PersonalizedGreeting />}
              <h1
                className="text-4xl sm:text-5xl font-light tracking-tight"
                style={{ color: 'var(--text-primary)' }}
              >
                WeatherGPT
              </h1>
              <p
                className="text-lg font-normal"
                style={{ color: 'var(--text-secondary)' }}
              >
                Contextual, real-time meteorological intelligence.
              </p>
            </div>

            <div className="w-full pt-4">
              <QueryInput
                onQuerySubmit={handleQuerySubmit}
                isLoading={isLoading}
                selectedLanguage={selectedLanguage}
                onLanguageChange={setSelectedLanguage}
              />
            </div>
          </motion.div>
        )}

        {/* Query Input Sticky Bar when viewing results or active conversation thread */}
        {(queryResponse || isThreadActive || isLoading || error) && (
          <div className="w-full mb-8">
            <QueryInput
              onQuerySubmit={handleQuerySubmit}
              isLoading={isLoading}
              selectedLanguage={selectedLanguage}
              onLanguageChange={setSelectedLanguage}
            />
          </div>
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
        className="w-full max-w-5xl mx-auto px-6 py-6 text-center text-xs font-mono"
        style={{
          borderTop: '1px solid var(--border-muted)',
          color: 'var(--text-tertiary)',
        }}
      >
        StormOps WeatherGPT &copy; 2026 — Powered by FastAPI, Open-Meteo &amp; Geocoding Service
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
