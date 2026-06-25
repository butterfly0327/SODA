interface TextLogoProps {
  className?: string;
  text?: string;
}

export function TextLogo({ className, text = 'SODA' }: TextLogoProps) {
  return <span className={className ?? 'text-lg font-semibold text-foreground'}>{text}</span>;
}
