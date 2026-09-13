
/**
 * Reusable Badge component for the Nyāya Neuro-Symbolic dashboard.
 * Supports academic color tokens:
 * - purple: primary neuro-symbolic accent
 * - green / emerald: validation, sound proofs, Pratyakṣa
 * - blue: canonical testimony, Upamāna, metadata
 * - orange / amber: inferential reasoning, Hetu, Anumāna
 * - slate / gray: neutral taxonomy, corpus citations
 */
export default function Badge({
  children,
  variant = 'purple',
  size = 'md',
  dot = false,
  className = '',
  icon: Icon = null,
}) {
  const variantStyles = {
    purple: 'bg-purple-50 text-purple-700 border-purple-200/70',
    purpleDark: 'bg-purple-950/70 text-purple-300 border-purple-800/60',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200/70',
    greenDark: 'bg-emerald-950/70 text-emerald-300 border-emerald-800/60',
    blue: 'bg-blue-50 text-blue-700 border-blue-200/70',
    blueDark: 'bg-blue-950/70 text-blue-300 border-blue-800/60',
    orange: 'bg-amber-50 text-amber-700 border-amber-200/70',
    orangeDark: 'bg-amber-950/70 text-amber-300 border-amber-800/60',
    slate: 'bg-slate-100 text-slate-700 border-slate-200/80',
    slateDark: 'bg-slate-800 text-slate-300 border-slate-700/60',
    red: 'bg-rose-50 text-rose-700 border-rose-200/70',
  };

  const dotColors = {
    purple: 'bg-purple-500',
    purpleDark: 'bg-purple-400',
    green: 'bg-emerald-500',
    greenDark: 'bg-emerald-400',
    blue: 'bg-blue-500',
    blueDark: 'bg-blue-400',
    orange: 'bg-amber-500',
    orangeDark: 'bg-amber-400',
    slate: 'bg-slate-500',
    slateDark: 'bg-slate-400',
    red: 'bg-rose-500',
  };

  const sizeStyles = {
    xs: 'text-[10px] px-1.5 py-0.5 font-medium',
    sm: 'text-xs px-2 py-0.5 font-medium',
    md: 'text-xs px-2.5 py-1 font-semibold tracking-wide',
    lg: 'text-sm px-3 py-1.5 font-semibold',
  };

  const currentVariant = variantStyles[variant] || variantStyles.purple;
  const currentDot = dotColors[variant] || dotColors.purple;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border transition-colors select-none whitespace-nowrap shrink-0 ${currentVariant} ${sizeStyles[size]} ${className}`}
    >
      {dot && (
        <span className="relative flex h-2 w-2">
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${currentDot}`} />
          <span className={`relative inline-flex rounded-full h-2 w-2 ${currentDot}`} />
        </span>
      )}
      {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
      <span>{children}</span>
    </span>
  );
}
