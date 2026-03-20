'use client'

interface BrandLogoProps {
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  className?: string
}

const CRM_LOGO_URL = 'https://crm.evpowerenergy.com/logo.svg'

export function BrandLogo({ size = 'md', showText = true, className = '' }: BrandLogoProps) {
  const sizeMap = {
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-14 w-14',
  }

  const titleSizeMap = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-xl',
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src={CRM_LOGO_URL}
        alt="EV Power Energy"
        className={`${sizeMap[size]} rounded-xl object-contain`}
      />
      {showText && (
        <div className="min-w-0">
          <p className={`truncate font-semibold text-foreground ${titleSizeMap[size]}`}>EV Power Energy</p>
          <p className="truncate text-xs text-muted-foreground">AI Assistant</p>
        </div>
      )}
    </div>
  )
}
