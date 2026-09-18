import React from 'react';
import { motion } from 'framer-motion';

interface LoadingStateProps {
  locationName: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ locationName }) => {
  const isLongQuery = locationName.length > 25 || locationName.includes(' ');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="w-full space-y-6"
    >
      {/* Status banner */}
      <div
        className="w-full rounded-3xl p-6 text-center space-y-3"
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
        }}
      >
        <div className="flex justify-center">
          <div
            className="w-8 h-8 border-2 rounded-full animate-spin"
            style={{
              borderColor: 'var(--spinner-track)',
              borderTopColor: 'var(--spinner-head)',
            }}
          />
        </div>
        <div className="text-base font-light" style={{ color: 'var(--text-primary)' }}>
          {isLongQuery ? (
            <span>Analyzing meteorological conditions...</span>
          ) : (
            <span>
              Retrieving atmospheric observations for{' '}
              <span className="font-medium" style={{ color: 'var(--accent)' }}>
                {locationName}
              </span>
            </span>
          )}
        </div>
        <div className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
          Connecting to Open-Meteo &amp; official advisory feeds
        </div>
      </div>

      {/* Structural skeleton surface to prevent layout shift */}
      <div
        className="w-full rounded-3xl p-6 sm:p-8 space-y-6 animate-pulse"
        style={{
          backgroundColor: 'var(--surface)',
          border: '1px solid var(--border)',
        }}
      >
        {/* Header skeleton */}
        <div className="flex justify-between items-center">
          <div className="space-y-2">
            <div className="h-7 w-40 rounded-lg bg-slate-700/20" />
            <div className="h-4 w-24 rounded bg-slate-700/15" />
          </div>
          <div className="h-8 w-28 rounded-full bg-slate-700/20" />
        </div>

        {/* Hero weather skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div className="flex items-center space-x-6">
            <div className="w-20 h-20 rounded-2xl bg-slate-700/20 flex-shrink-0" />
            <div className="space-y-2">
              <div className="h-12 w-28 rounded-lg bg-slate-700/20" />
              <div className="h-4 w-36 rounded bg-slate-700/15" />
            </div>
          </div>
          <div className="h-20 rounded-2xl bg-slate-700/15" />
        </div>

        {/* 4-metric grid skeleton */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-2xl bg-slate-700/15" />
          ))}
        </div>
      </div>
    </motion.div>
  );
};
