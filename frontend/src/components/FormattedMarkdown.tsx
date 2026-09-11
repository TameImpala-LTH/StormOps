import React from 'react';

interface FormattedMarkdownProps {
  content: string;
  className?: string;
}

/**
 * Safely parse inline markdown tokens:
 * - Bold: **text** or __text__
 * - Italic: *text* or _text_
 * - Inline code: `code`
 * - Plain text
 * Strictly renders React DOM nodes without any dangerouslySetInnerHTML or arbitrary HTML execution.
 */
function renderInlineMarkdown(text: string): React.ReactNode[] {
  // Regex to match `code`, **bold**, __bold__, *italic*, _italic_
  const tokenRegex = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, index) => {
    if (!part) return null;

    // Inline code: `code`
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return (
        <code
          key={index}
          className="px-1.5 py-0.5 rounded font-mono text-[11px] bg-zinc-800/60 text-sky-300 border border-zinc-700/50"
        >
          {part.slice(1, -1)}
        </code>
      );
    }

    // Bold: **text** or __text__
    if (
      (part.startsWith('**') && part.endsWith('**') && part.length >= 4) ||
      (part.startsWith('__') && part.endsWith('__') && part.length >= 4)
    ) {
      return (
        <strong key={index} className="font-semibold text-inherit">
          {part.slice(2, -2)}
        </strong>
      );
    }

    // Italic: *text* or _text_
    if (
      (part.startsWith('*') && part.endsWith('*') && part.length >= 2) ||
      (part.startsWith('_') && part.endsWith('_') && part.length >= 2)
    ) {
      return (
        <em key={index} className="italic text-inherit opacity-90">
          {part.slice(1, -1)}
        </em>
      );
    }

    return <React.Fragment key={index}>{part}</React.Fragment>;
  });
}

/**
 * FormattedMarkdown — safe, lightweight Markdown renderer for assistant messages and summaries.
 * Supports:
 * - Unordered lists (- or *)
 * - Paragraphs and line breaks
 * - Bold, italic, inline code
 * - Prevents raw syntax leakage (`**`, `__`, etc.)
 * - Zero raw HTML injection
 */
export const FormattedMarkdown: React.FC<FormattedMarkdownProps> = ({ content, className = '' }) => {
  if (!content) return null;

  // Split by newlines
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];

  let currentList: React.ReactNode[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="list-disc list-inside space-y-1 my-1.5 pl-1">
          {currentList}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Empty line
    if (!trimmed) {
      flushList();
      return;
    }

    // Unordered list item: - item or * item
    const listMatch = trimmed.match(/^[-*]\s+(.*)$/);
    if (listMatch) {
      currentList.push(
        <li key={`li-${idx}`} className="leading-relaxed">
          {renderInlineMarkdown(listMatch[1])}
        </li>
      );
      return;
    }

    // Regular line / paragraph
    flushList();
    elements.push(
      <p key={`p-${idx}`} className="leading-relaxed">
        {renderInlineMarkdown(line)}
      </p>
    );
  });

  flushList();

  return <div className={`space-y-1.5 ${className}`}>{elements}</div>;
};
