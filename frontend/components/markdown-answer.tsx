"use client";

import { Children, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Matches a whole bracketed citation, including the grouped form models emit
 * despite the prompt ("[Source 1, Source 2]"), so every number gets a badge.
 * Markdown links are separate nodes by this point, so they can't be caught here.
 */
const CITATION_BLOCK_PATTERN = /\[\s*Sources?\b[^\]]*\]/gi;
const NUMBER_PATTERN = /\d+/g;

interface MarkdownAnswerProps {
  content: string;
  /** Source numbers available for this answer; unknown markers stay inert. */
  sourceNumbers: number[];
  onCitationClick?: (sourceNumber: number) => void;
}

/**
 * Replaces citation markers in plain text runs with interactive references.
 * Markers split across inline markup are left as-is rather than mis-parsed.
 */
function withCitations(
  children: ReactNode,
  renderCitations: (sourceNumbers: number[], key: string) => ReactNode,
): ReactNode {
  return Children.map(children, (child, childIndex) => {
    if (typeof child !== "string") {
      return child;
    }

    const parts: ReactNode[] = [];
    const pattern = new RegExp(CITATION_BLOCK_PATTERN);
    let cursor = 0;
    let match = pattern.exec(child);

    while (match) {
      const numbers = (match[0].match(NUMBER_PATTERN) ?? []).map(Number);
      if (match.index > cursor) {
        parts.push(child.slice(cursor, match.index));
      }
      parts.push(
        numbers.length > 0
          ? renderCitations(numbers, `${childIndex}-${match.index}`)
          : match[0],
      );
      cursor = match.index + match[0].length;
      match = pattern.exec(child);
    }

    if (parts.length === 0) {
      return child;
    }
    if (cursor < child.length) {
      parts.push(child.slice(cursor));
    }
    return parts;
  });
}

export function MarkdownAnswer({
  content,
  sourceNumbers,
  onCitationClick,
}: MarkdownAnswerProps) {
  const renderCitations = (numbers: number[], key: string): ReactNode => (
    <span key={key} className="ml-0.5 inline-flex gap-0.5 align-baseline">
      {numbers.map((sourceNumber) => {
        const label = `Source ${sourceNumber}`;
        const isResolvable = sourceNumbers.includes(sourceNumber);

        if (!isResolvable || !onCitationClick) {
          return (
            <span
              key={sourceNumber}
              title={label}
              className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-muted-foreground"
            >
              {sourceNumber}
            </span>
          );
        }

        return (
          <button
            key={sourceNumber}
            type="button"
            onClick={() => onCitationClick(sourceNumber)}
            aria-label={`Jump to ${label}`}
            title={label}
            className="rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-semibold text-primary transition-colors hover:bg-primary/20"
          >
            {sourceNumber}
          </button>
        );
      })}
    </span>
  );

  const decorate = (children: ReactNode) => withCitations(children, renderCitations);

  const components: Components = {
    p: ({ children }) => <p className="my-3 first:mt-0 last:mb-0">{decorate(children)}</p>,
    ul: ({ children }) => (
      <ul className="my-3 list-disc space-y-1.5 pl-5 first:mt-0 last:mb-0">
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol className="my-3 list-decimal space-y-1.5 pl-5 first:mt-0 last:mb-0">
        {children}
      </ol>
    ),
    li: ({ children }) => <li className="leading-7">{decorate(children)}</li>,
    strong: ({ children }) => (
      <strong className="font-semibold">{decorate(children)}</strong>
    ),
    em: ({ children }) => <em className="italic">{decorate(children)}</em>,
    h1: ({ children }) => (
      <h1 className="mb-2 mt-5 text-base font-semibold first:mt-0">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="mb-2 mt-5 text-base font-semibold first:mt-0">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="mb-2 mt-4 text-sm font-semibold first:mt-0">{children}</h3>
    ),
    blockquote: ({ children }) => (
      <blockquote className="my-3 border-l-2 border-primary/40 pl-3 text-muted-foreground">
        {children}
      </blockquote>
    ),
    a: ({ children, href }) => (
      <a
        href={href}
        target="_blank"
        rel="noreferrer"
        className="font-medium text-primary underline underline-offset-2"
      >
        {children}
      </a>
    ),
    code: ({ children }) => (
      <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.85em]">
        {children}
      </code>
    ),
    pre: ({ children }) => (
      <pre className="my-3 overflow-x-auto rounded-xl border bg-muted/50 p-3 text-xs [&_code]:bg-transparent [&_code]:p-0">
        {children}
      </pre>
    ),
    hr: () => <hr className="my-4" />,
    table: ({ children }) => (
      <div className="my-3 overflow-x-auto rounded-xl border">
        <table className="w-full text-left text-xs">{children}</table>
      </div>
    ),
    th: ({ children }) => (
      <th className="border-b bg-muted/40 px-3 py-2 font-semibold">{children}</th>
    ),
    td: ({ children }) => (
      <td className="border-b px-3 py-2 last:border-0">{decorate(children)}</td>
    ),
  };

  return (
    <div className="text-sm leading-7">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
