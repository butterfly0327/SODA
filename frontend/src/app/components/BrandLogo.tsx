import { useState } from 'react';
import logoImage from '../../assets/images/sodalogo.png';
import { TextLogo } from './TextLogo';

interface BrandLogoProps {
  className?: string;
  fallbackClassName?: string;
}

export function BrandLogo({ className, fallbackClassName }: BrandLogoProps) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return <TextLogo className={fallbackClassName} />;
  }

  return (
    <img
      src={logoImage}
      alt="SODA"
      className={className ?? 'h-8 w-auto object-contain'}
      onError={() => setHasError(true)}
    />
  );
}
