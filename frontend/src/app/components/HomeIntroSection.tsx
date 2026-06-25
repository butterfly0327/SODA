import type { LucideIcon } from 'lucide-react';
import { MessageInput } from './MessageInput';

interface IntroExample {
  label: string;
  prompt: string;
  icon: LucideIcon;
}

interface HomeIntroSectionProps {
  onSubmitPrompt: (text: string) => void;
  isLoading: boolean;
  title: string;
  examples: IntroExample[];
  footerNote: string;
}

export function HomeIntroSection({ onSubmitPrompt, isLoading, title, examples, footerNote }: HomeIntroSectionProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 overflow-y-auto">
      <div className="text-center max-w-3xl w-full px-2 sm:px-6">
        <h1 className="text-3xl font-normal text-foreground mb-8">{title}</h1>

        <MessageInput inline onSubmitMessage={onSubmitPrompt} isLoading={isLoading} />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
          {examples.map((example) => {
            const Icon = example.icon;
            return (
              <button
                type="button"
                key={example.label}
                onClick={() => onSubmitPrompt(example.prompt)}
                className="rounded-xl border border-border bg-white p-4 text-left shadow-sm transition-shadow hover:shadow-md flex flex-col items-start gap-2 cursor-pointer"
              >
                <Icon className="w-5 h-5 text-muted-foreground" />
                <span className="text-sm text-foreground">{example.label}</span>
              </button>
            );
          })}
        </div>

        <p className="text-xs text-muted-foreground">{footerNote}</p>
      </div>
    </div>
  );
}
