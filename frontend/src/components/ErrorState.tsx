import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ message, onRetry }) => {
  return (
    <div
      className="w-full max-w-lg mx-auto rounded-3xl p-8 text-center space-y-4"
      style={{
        backgroundColor: 'var(--error-bg)',
        border: '1px solid var(--error-border)',
      }}
    >
      <div className="flex justify-center text-red-400">
        <AlertTriangle className="w-10 h-10" />
      </div>
      <div className="font-medium text-base" style={{ color: 'var(--text-primary)' }}>
        {message}
      </div>
      <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
        Weather information couldn&apos;t be retrieved right now. Please check backend status and try again.
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 text-red-400 rounded-xl text-sm font-medium transition-colors cursor-pointer"
      >
        <RefreshCw className="w-4 h-4" /> Retry Query
      </button>
    </div>
  );
};
