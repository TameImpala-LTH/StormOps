import React, { useState } from 'react';
import { Search, MapPin, LocateFixed, Loader2, Mic, MicOff } from 'lucide-react';
import { PRESET_LOCATIONS } from '../utils/locations';
import { CoordinateInput, LanguageCode } from '../types/weather';
import { LanguageSelector } from './LanguageSelector';
import { useVoiceRecording } from '../hooks/useVoiceRecording';

interface QueryInputProps {
  onQuerySubmit: (query: string, location?: CoordinateInput, language?: LanguageCode) => void;
  isLoading?: boolean;
  selectedLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
}

export const QueryInput: React.FC<QueryInputProps> = ({
  onQuerySubmit,
  isLoading,
  selectedLanguage,
  onLanguageChange,
}) => {
  const [query, setQuery] = useState('');
  const [isGeolocating, setIsGeolocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [pendingLocation, setPendingLocation] = useState<CoordinateInput | null>(null);

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
    },
  });

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

  return (
    <div className="w-full max-w-xl mx-auto space-y-2.5">
      {/* Centered Language Selector without label */}
      <div className="flex justify-center mb-1">
        <LanguageSelector
          currentLanguage={selectedLanguage}
          onLanguageChange={onLanguageChange}
          disabled={isLoading || isGeolocating || isRecording || isTranscribing}
        />
      </div>

      <form onSubmit={handleSubmit} className="relative group">
        <div
          className="relative flex items-center rounded-2xl p-2 shadow-lg transition-all"
          style={{
            backgroundColor: 'var(--surface-input)',
            border: '1px solid var(--border)',
          }}
          onFocusCapture={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--text-muted)';
          }}
          onBlurCapture={(e) => {
            (e.currentTarget as HTMLDivElement).style.borderColor = 'var(--border)';
          }}
        >
          <div className="pl-4" style={{ color: 'var(--text-muted)' }}>
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (geoError) setGeoError(null);
              if (voiceError) clearVoiceError();
            }}
            disabled={isLoading || isGeolocating}
            placeholder={
              isRecording
                ? 'Listening... speak now'
                : isTranscribing
                ? 'Transcribing...'
                : selectedLanguage === 'hi'
                ? 'मौसम के बारे में पूछें (उदा. क्या कल दिल्ली में बारिश होगी?)'
                : selectedLanguage === 'bn'
                ? 'আবহাওয়া সম্পর্কে জিজ্ঞাসা করুন (যেমন: কাল কলকাতায় কি বৃষ্টি হবে?)'
                : 'Ask anything e.g. Will it rain in Darjeeling tomorrow?'
            }
            className="flex-1 min-w-0 bg-transparent px-3 py-3 focus:outline-none text-base"
            style={{
              color: 'var(--text-primary)',
            }}
          />

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
              className={`p-2.5 mr-1 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center relative ${
                isRecording ? 'animate-pulse' : ''
              }`}
              style={{
                color: isRecording ? '#ef4444' : 'var(--text-secondary)',
                backgroundColor: isRecording ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
                border: isRecording ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid transparent',
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
                <Loader2 className="w-5 h-5 animate-spin text-purple-400" />
              ) : isRecording ? (
                <MicOff className="w-5 h-5 text-red-500 animate-pulse" />
              ) : (
                <Mic className="w-5 h-5" />
              )}
              {isRecording && (
                <span className="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500"></span>
                </span>
              )}
            </button>
          )}

          {/* Location button */}
          <button
            type="button"
            onClick={handleUseMyLocation}
            disabled={isLoading || isGeolocating || isRecording || isTranscribing}
            title="Use my location"
            aria-label="Use my location"
            className="p-2.5 mr-1 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center"
            style={{
              color: 'var(--text-secondary)',
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
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
            }}
          >
            {isGeolocating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <LocateFixed className="w-5 h-5" />
            )}
          </button>

          <button
            type="submit"
            disabled={isLoading || isGeolocating || isRecording || isTranscribing || !query.trim()}
            className="px-4 py-2.5 font-medium text-sm rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
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
            Ask
          </button>
        </div>
      </form>

      {/* Geolocation or Voice error or listening status message */}
      {(isRecording || isTranscribing || geoError || voiceError) && (
        <div
          className="text-xs text-center px-3 py-1.5 rounded-lg transition-all"
          style={{
            color: voiceError || geoError ? 'var(--alert-warning-text, #f59e0b)' : 'var(--accent, #a78bfa)',
            backgroundColor: voiceError || geoError ? 'var(--alert-warning-bg, rgba(245, 158, 11, 0.1))' : 'var(--surface-elevated)',
            border: `1px solid ${voiceError || geoError ? 'var(--alert-warning-border, rgba(245, 158, 11, 0.2))' : 'var(--border-muted)'}`,
          }}
        >
          {voiceError || geoError || (isTranscribing ? 'Transcribing audio...' : `Listening (${selectedLanguage === 'hi' ? 'Hindi' : selectedLanguage === 'bn' ? 'Bengali' : 'English'})... Speak now`)}
        </div>
      )}

      {/* Quick Location Suggestions in ONE clean horizontal row */}
      <div className="flex items-center justify-center gap-1.5 pt-1 overflow-x-auto whitespace-nowrap">
        <span
          className="text-xs mr-1 flex items-center gap-1 flex-shrink-0"
          style={{ color: 'var(--text-muted)' }}
        >
          <MapPin className="w-3 h-3" /> Quick Locations:
        </span>
        {PRESET_LOCATIONS.map((loc) => (
          <button
            key={loc.name}
            type="button"
            onClick={() => handlePresetClick(loc.name)}
            className="px-2.5 py-1 rounded-lg text-xs transition-colors cursor-pointer flex-shrink-0"
            style={{
              backgroundColor: 'var(--surface-elevated)',
              border: '1px solid var(--border-muted)',
              color: 'var(--text-secondary)',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface)';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'var(--surface-elevated)';
              (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)';
            }}
          >
            {loc.name}
          </button>
        ))}
      </div>
    </div>
  );
};

