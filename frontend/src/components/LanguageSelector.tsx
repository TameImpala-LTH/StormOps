import React from 'react';
import { Globe } from 'lucide-react';
import { LanguageCode } from '../types/weather';

interface LanguageSelectorProps {
  currentLanguage: LanguageCode;
  onLanguageChange: (lang: LanguageCode) => void;
  disabled?: boolean;
}

const LANGUAGES: { code: LanguageCode; label: string; title: string }[] = [
  { code: 'auto', label: 'Auto', title: 'Automatically detect language' },
  { code: 'en', label: 'EN', title: 'English' },
  { code: 'hi', label: 'हिन्दी', title: 'हिंदी (Hindi)' },
  { code: 'bn', label: 'বাংলা', title: 'বাংলা (Bengali)' },
  { code: 'ta', label: 'தமிழ்', title: 'தமிழ் (Tamil)' },
  { code: 'te', label: 'తెలుగు', title: 'తెలుగు (Telugu)' },
  { code: 'mr', label: 'मराठी', title: 'मराठी (Marathi)' },
];

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  currentLanguage,
  onLanguageChange,
  disabled = false,
}) => {
  return (
    <div
      className="inline-flex items-center p-0.5 rounded-xl border transition-all text-[11px] sm:text-xs font-mono max-w-full overflow-x-auto no-scrollbar"
      style={{
        backgroundColor: 'var(--surface-elevated)',
        borderColor: 'var(--border-muted)',
      }}
      role="group"
      aria-label="Language selection"
    >
      <div className="pl-1.5 pr-0.5 shrink-0" style={{ color: 'var(--text-muted)' }}>
        <Globe className="w-3.5 h-3.5 opacity-70" />
      </div>
      {LANGUAGES.map((lang) => {
        const isSelected = currentLanguage === lang.code;
        return (
          <button
            key={lang.code}
            type="button"
            disabled={disabled}
            onClick={() => onLanguageChange(lang.code)}
            title={lang.title}
            aria-pressed={isSelected}
            className={`px-1.5 sm:px-2 py-0.5 sm:py-1 rounded-lg transition-all font-medium whitespace-nowrap cursor-pointer ${
              isSelected ? 'shadow-xs font-semibold' : 'hover:opacity-80'
            }`}
            style={{
              backgroundColor: isSelected ? 'var(--btn-primary-bg)' : 'transparent',
              color: isSelected ? 'var(--btn-primary-text)' : 'var(--text-secondary)',
            }}
          >
            {lang.label}
          </button>
        );
      })}
    </div>
  );
};
