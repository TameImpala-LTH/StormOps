import React, { useState, useEffect, useRef } from 'react';
import { Search, MapPin, LocateFixed, Loader2, Mic, MicOff, X, ArrowRight } from 'lucide-react';
import { PRESET_LOCATIONS } from '../utils/locations';
import { CoordinateInput, LanguageCode } from '../types/weather';
import { LanguageSelector } from './LanguageSelector';
import { useVoiceRecording } from '../hooks/useVoiceRecording';

export interface QueryInputProps {
  onQuerySubmit: (query: string, location?: CoordinateInput, language?: LanguageCode) => void;
  isLoading?: boolean;
  selectedLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  variant?: 'discovery' | 'docked';
  initialQuery?: string;
}

const ROTATING_PROMPTS = [
  'Ask about the weather anywhere...',
  'Will it rain in Kolkata tonight?',
  'Cherrapunji rainfall outlook',
  'How hot will Gariahat feel this afternoon?',
  'Will I need an umbrella in Koramangala at 7?',
  'Weather at my location',
];

export const QueryInput: React.FC<QueryInputProps> = ({
  onQuerySubmit,
  isLoading = false,
  selectedLanguage,
  onLanguageChange,
  variant = 'discovery',
  initialQuery = '',
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [isFocused, setIsFocused] = useState(false);
  const [isGeolocating, setIsGeolocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [pendingLocation, setPendingLocation] = useState<CoordinateInput | null>(null);
  const [promptIndex, setPromptIndex] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);

  // Sync initialQuery if it changes externally
  useEffect(() => {
    if (initialQuery && initialQuery !== query) {
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  // Voice recording integration
  const {
    isSupported: isVoiceSupported,
    isRecording,
    isTranscribing,
    error: voiceError,
    startRecording,
    stopRecording,
    clearError: clearVoiceError,
  } = useVoiceRecording({
    onTranscript: (spokenText) => {
      setQuery(spokenText);
      if (inputRef.current) {
        inputRef.current.focus();
      }
    },
  });

  // Rotating placeholder mechanism (respects prefers-reduced-motion)
  useEffect(() => {
    if (variant === 'docked') return;
    if (isFocused || query.trim().length > 0 || isRecording || isTranscribing) return;
    if (selectedLanguage === 'hi' || selectedLanguage === 'bn') return;

    // Check reduced motion preference
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    const timer = setInterval(() => {
      setPromptIndex((prev) => (prev + 1) % ROTATING_PROMPTS.length);
    }, 4800);

    return () => clearInterval(timer);
  }, [variant, isFocused, query, isRecording, isTranscribing, selectedLanguage]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isRecording) stopRecording();
    if (!query.trim()) return;

    setGeoError(null);
    clearVoiceError();

    const lower = query.toLowerCase();
    const isLocationQuery = lower.includes('my location') || lower.includes('current location');
    const locPayload = isLocationQuery && pendingLocation ? pendingLocation : undefined;

    onQuerySubmit(query.trim(), locPayload, selectedLanguage);
  };

  const handleToggleSpeech = () => {
    if (isRecording) {
      stopRecording();
    } else {
      clearVoiceError();
      setGeoError(null);
      startRecording(selectedLanguage);
    }
  };

  const handlePresetClick = (cityName: string) => {
    if (isRecording) stopRecording();
    const fullQuery = `What's the weather in ${cityName}?`;
    setQuery(fullQuery);
    setGeoError(null);
    clearVoiceError();
    setPendingLocation(null);
    onQuerySubmit(fullQuery, undefined, selectedLanguage);
  };

  const handleUseMyLocation = () => {
    if (isRecording) stopRecording();
    setGeoError(null);
    clearVoiceError();

    if (!navigator.geolocation) {
      setGeoError('Geolocation is not supported by your browser.');
      return;
    }

    setIsGeolocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setIsGeolocating(false);
        const coords: CoordinateInput = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        setPendingLocation(coords);
        const locationQuery = "What's the weather at my location?";
        setQuery(locationQuery);
        onQuerySubmit(locationQuery, coords, selectedLanguage);
      },
      (error) => {
        setIsGeolocating(false);
        setPendingLocation(null);
        let msg = 'Could not determine your location.';
        if (error.code === error.PERMISSION_DENIED) {
          msg = 'Location access denied. Please type a city name.';
        } else if (error.code === error.POSITION_UNAVAILABLE) {
          msg = 'Location information unavailable.';
        } else if (error.code === error.TIMEOUT) {
          msg = 'Location request timed out.';
        }
        setGeoError(msg);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const handleClear = () => {
    setQuery('');
    setGeoError(null);
    clearVoiceError();
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Determine active placeholder string
  const getPlaceholder = () => {
    if (isRecording) return 'Listening... speak now';
    if (isTranscribing) return 'Transcribing audio...';
    if (selectedLanguage === 'hi') {
      return 'मौसम के बारे में पूछें (उदा. क्या कल दिल्ली में बारिश होगी?)';
    }
    if (selectedLanguage === 'bn') {
      return 'আবহাওয়া সম্পর্কে জিজ্ঞাসা করুন (যেমন: কাল কলকাতায় কি বৃষ্টি হবে?)';
    }
    if (variant === 'docked') {
      return 'Search or ask follow-up...';
    }
    return ROTATING_PROMPTS[promptIndex];
  };

  const isDocked = variant === 'docked';

  return (
    <div className={`w-full ${isDocked ? 'max-w-full' : 'max-w-2xl mx-auto space-y-3'}`}>
      {/* Discovery Mode: Clean Centered Language Selector */}
      {!isDocked && (
        <div className="flex justify-center mb-1">
          <LanguageSelector
            currentLanguage={selectedLanguage}
            onLanguageChange={onLanguageChange}
            disabled={isLoading || isGeolocating || isRecording || isTranscribing}
          />
        </div>
      )}

      {/* The Unified Omnibar Form */}
      <form onSubmit={handleSubmit} className="relative group w-full">
        <div
          className={`relative flex items-center transition-all ${
            isDocked
              ? 'rounded-xl px-2.5 py-1.5'
              : 'rounded-2xl px-3 sm:px-4 py-2 sm:py-2.5'
          }`}
          style={{
            backgroundColor: 'var(--surface-input)',
            border: `1px solid ${isFocused ? 'var(--border-strong)' : 'var(--border-default)'}`,
            boxShadow: isFocused ? '0 0 0 2px var(--focus-ring)' : 'var(--shadow-sm)',
          }}
        >
          {/* Leading Search Icon */}
          <div
            className={`shrink-0 flex items-center justify-center ${isDocked ? 'pr-2' : 'pr-3'}`}
            style={{ color: isFocused ? 'var(--accent-primary)' : 'var(--text-tertiary)' }}
          >
            <Search className={isDocked ? 'w-4 h-4' : 'w-5 h-5'} />
          </div>

          {/* Main Search Input Field */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onChange={(e) => {
              setQuery(e.target.value);
              if (geoError) setGeoError(null);
              if (voiceError) clearVoiceError();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                handleClear();
              }
            }}
            disabled={isLoading || isGeolocating}
            placeholder={getPlaceholder()}
            aria-label="Search weather by location or question"
            className={`flex-1 min-w-0 bg-transparent focus:outline-none ${
              isDocked ? 'text-xs sm:text-sm py-1' : 'text-sm sm:text-base py-1.5'
            }`}
            style={{
              color: 'var(--text-primary)',
            }}
          />

          {/* Clear Button (when text exists) */}
          {query.trim().length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              title="Clear input (Esc)"
              aria-label="Clear query input"
              className="p-1 rounded-md transition-colors cursor-pointer shrink-0 mr-1"
              style={{ color: 'var(--text-tertiary)' }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-tertiary)';
              }}
            >
              <X className={isDocked ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
            </button>
          )}

          {/* Voice Input Button */}
          {isVoiceSupported && (
            <button
              type="button"
              onClick={handleToggleSpeech}
              disabled={isLoading || isGeolocating || isTranscribing}
              title={
                isRecording
                  ? 'Listening... Click to stop'
                  : isTranscribing
                  ? 'Transcribing audio...'
                  : 'Voice input (English, Hindi, Bengali)'
              }
              aria-label={isRecording ? 'Stop voice recording' : 'Start voice input'}
              className={`p-1.5 sm:p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center relative shrink-0 ${
                isRecording ? 'animate-pulse' : ''
              }`}
              style={{
                color: isRecording ? 'var(--severity-red)' : 'var(--text-secondary)',
                backgroundColor: isRecording ? 'var(--severity-red-bg)' : 'transparent',
                border: isRecording ? '1px solid var(--severity-red-border)' : '1px solid transparent',
              }}
              onMouseEnter={(e) => {
                if (!e.currentTarget.disabled && !isRecording) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-elevated)';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isRecording) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
                }
              }}
            >
              {isTranscribing ? (
                <Loader2 className={`${isDocked ? 'w-3.5 h-3.5' : 'w-4 h-4'} animate-spin`} style={{ color: 'var(--accent-primary)' }} />
              ) : isRecording ? (
                <MicOff className={`${isDocked ? 'w-3.5 h-3.5' : 'w-4 h-4'} text-red-500 animate-pulse`} />
              ) : (
                <Mic className={isDocked ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
              )}
            </button>
          )}

          {/* Current Location Button */}
          <button
            type="button"
            onClick={handleUseMyLocation}
            disabled={isLoading || isGeolocating || isRecording || isTranscribing}
            title="Use my current location"
            aria-label="Use my current location"
            className="p-1.5 sm:p-2 rounded-xl transition-all cursor-pointer flex items-center justify-center shrink-0 mr-1"
            style={{
              color: isGeolocating ? 'var(--accent-primary)' : 'var(--text-secondary)',
              backgroundColor: 'transparent',
            }}
            onMouseEnter={(e) => {
              if (!e.currentTarget.disabled) {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-elevated)';
                (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
              (e.currentTarget as HTMLButtonElement).style.color = isGeolocating ? 'var(--accent-primary)' : 'var(--text-secondary)';
            }}
          >
            {isGeolocating ? (
              <Loader2 className={`${isDocked ? 'w-3.5 h-3.5' : 'w-4 h-4'} animate-spin`} />
            ) : (
              <LocateFixed className={isDocked ? 'w-3.5 h-3.5' : 'w-4 h-4'} />
            )}
          </button>

          {/* Submit Action Button */}
          <button
            type="submit"
            disabled={isLoading || isGeolocating || isRecording || isTranscribing || !query.trim()}
            title="Submit query (Enter)"
            aria-label="Submit weather query"
            className={`font-medium transition-all shrink-0 cursor-pointer flex items-center justify-center ${
              isDocked
                ? 'px-2.5 py-1 text-xs rounded-lg'
                : 'px-3.5 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm rounded-xl'
            } disabled:opacity-30 disabled:cursor-not-allowed`}
            style={{
              backgroundColor: 'var(--btn-primary-bg)',
              color: 'var(--btn-primary-text)',
            }}
            onMouseEnter={(e) => {
              if (!e.currentTarget.disabled) {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--btn-primary-hover)';
              }
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--btn-primary-bg)';
            }}
          >
            {isDocked ? (
              <ArrowRight className="w-3.5 h-3.5" />
            ) : (
              <span>Ask</span>
            )}
          </button>
        </div>
      </form>

      {/* Geolocation or Voice Error / Status Notification */}
      {(isRecording || isTranscribing || geoError || voiceError) && (
        <div
          className="text-xs text-center px-3 py-1.5 rounded-lg transition-all"
          style={{
            color: voiceError || geoError ? 'var(--severity-orange-text)' : 'var(--accent-primary)',
            backgroundColor: voiceError || geoError ? 'var(--severity-orange-bg)' : 'var(--surface-elevated)',
            border: `1px solid ${voiceError || geoError ? 'var(--severity-orange-border)' : 'var(--border-subtle)'}`,
          }}
        >
          {voiceError ||
            geoError ||
            (isTranscribing
              ? 'Transcribing audio...'
              : `Listening (${selectedLanguage === 'hi' ? 'Hindi' : selectedLanguage === 'bn' ? 'Bengali' : 'English'})... Speak now`)}
        </div>
      )}

      {/* Discovery Mode: Capability Cue & Contextual Suggestions */}
      {!isDocked && (
        <div className="space-y-3 pt-1">
          {/* Subtle Geographic Capability Cue */}
          <div className="pt-1 text-center select-none pointer-events-none space-y-0.5">
            <p
              className="type-label text-[11px] tracking-widest uppercase opacity-75"
              style={{ color: 'var(--text-tertiary)' }}
            >
              Search beyond cities
            </p>
            <p
              className="type-body-sm text-xs font-light"
              style={{ color: 'var(--text-secondary)' }}
            >
              Cities &middot; Towns &middot; Villages &middot; Localities
            </p>
          </div>

          {/* Contextual Preset Examples */}
          <div className="flex items-center justify-center gap-1.5 pt-1 overflow-x-auto whitespace-nowrap scrollbar-none px-2">
            <span
              className="type-label text-[10px] mr-1 flex items-center gap-1 shrink-0"
              style={{ color: 'var(--text-tertiary)' }}
            >
              <MapPin className="w-3 h-3" /> Examples:
            </span>
            {PRESET_LOCATIONS.map((loc) => (
              <button
                key={loc.name}
                type="button"
                onClick={() => handlePresetClick(loc.name)}
                className="px-2.5 py-1 rounded-lg text-xs transition-all cursor-pointer shrink-0 border"
                style={{
                  backgroundColor: 'var(--surface-elevated)',
                  borderColor: 'var(--border-subtle)',
                  color: 'var(--text-secondary)',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-default)';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border-subtle)';
                  (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
                }}
              >
                {loc.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
