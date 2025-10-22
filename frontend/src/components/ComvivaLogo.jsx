import React from 'react';

const ComvivaLogo = ({ className = "w-8 h-8", variant = "icon", theme = "auto" }) => {
  // Determine which logo to use based on theme
  const getLogoSrc = () => {
    if (theme === "dark") {
      return "/assets/logos/comviva-dark.png";
    } else if (theme === "light") {
      return "/assets/logos/comviva-light.png";
    } else {
      // Auto mode - use CSS to show appropriate logo
      return null;
    }
  };

  if (variant === "orb") {
    return (
      <img 
        src="/assets/logos/comviva-orb.jpg"
        alt="Comviva"
        className={`object-contain ${className}`}
      />
    );
  }

  if (variant === "full") {
    const logoSrc = getLogoSrc();
    if (logoSrc) {
      return (
        <img 
          src={logoSrc}
          alt="Comviva - A Tech Mahindra Company"
          className={`object-contain ${className}`}
        />
      );
    } else {
      // Auto mode with theme-aware display
      return (
        <div className={className}>
          <img 
            src="/assets/logos/comviva-light.png"
            alt="Comviva - A Tech Mahindra Company"
            className="object-contain dark:hidden w-full h-full"
          />
          <img 
            src="/assets/logos/comviva-dark.png"
            alt="Comviva - A Tech Mahindra Company"
            className="object-contain hidden dark:block w-full h-full"
          />
        </div>
      );
    }
  }
  
  // Default icon variant - use the orb logo
  return (
    <img 
      src="/assets/logos/comviva-orb.jpg"
      alt="Comviva"
      className={`object-contain rounded-full ${className}`}
    />
  );
};

// Legacy SVG component for fallback
const ComvivaIcon = ({ className = "w-8 h-8" }) => (
  <svg 
    className={className}
    viewBox="0 0 100 100" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <linearGradient id="comvivaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#dc2626" />
        <stop offset="50%" stopColor="#f97316" />
        <stop offset="100%" stopColor="#dc2626" />
      </linearGradient>
    </defs>
    
    <circle 
      cx="50" 
      cy="50" 
      r="45" 
      fill="url(#comvivaGradient)"
      className="drop-shadow-md"
    />
    
    <circle cx="50" cy="50" r="15" fill="white" />
    
    <path 
      d="M35 20 L65 35 L50 50 L35 65 L20 50 Z" 
      fill="white"
      fillOpacity="0.9"
    />
  </svg>
);

export default ComvivaLogo;
export { ComvivaIcon };