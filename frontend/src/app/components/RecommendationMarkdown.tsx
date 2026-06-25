import ReactMarkdown from 'react-markdown';

interface RecommendationMarkdownProps {
  content: string;
}

function normalizeRecommendationMarkdown(raw: string) {
  return raw
    .replace(/\s+(#{1,4}\s)/g, '\n\n$1')
    .replace(/([^\n])\s+-\s+/g, '$1\n- ')
    .replace(/\s*\(evidence:[^\)]+\)/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function RecommendationMarkdown({ content }: RecommendationMarkdownProps) {
  const normalizedContent = normalizeRecommendationMarkdown(content);

  return (
    <ReactMarkdown
      allowedElements={['p', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'strong', 'em', 'code', 'br']}
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0 text-foreground leading-relaxed">{children}</p>,
        h1: ({ children }) => <h1 className="mb-3 text-xl font-semibold text-foreground">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-3 text-lg font-semibold text-foreground">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-2 text-base font-semibold text-foreground">{children}</h3>,
        h4: ({ children }) => <h4 className="mb-2 text-sm font-semibold text-foreground">{children}</h4>,
        ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5 text-foreground">{children}</ul>,
        ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5 text-foreground">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed marker:text-muted-foreground">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
        em: ({ children }) => <em className="italic text-foreground">{children}</em>,
        code: ({ children }) => (
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.95em] text-foreground">
            {children}
          </code>
        ),
      }}
    >
      {normalizedContent}
    </ReactMarkdown>
  );
}
