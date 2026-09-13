
/**
 * Reusable Button component adhering to the academic research theme.
 */
export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  disabled = false,
  loading = false,
  icon: Icon = null,
  iconRight: IconRight = null,
  className = '',
  type = 'button',
  title = '',
}) {
  const variantStyles = {
    primary:
      'bg-purple-700 hover:bg-purple-800 active:bg-purple-900 text-white shadow-sm hover:shadow border border-purple-800/40 focus-visible:ring-purple-500',
    secondary:
      'bg-slate-800 hover:bg-slate-900 active:bg-slate-950 text-slate-100 border border-slate-700 shadow-sm focus-visible:ring-slate-400',
    outline:
      'bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 border border-slate-300 shadow-sm hover:border-slate-400 focus-visible:ring-purple-500',
    ghost:
      'bg-transparent hover:bg-slate-100 active:bg-slate-200 text-slate-600 hover:text-slate-900 focus-visible:ring-purple-500',
    ghostDark:
      'bg-transparent hover:bg-slate-800 text-slate-300 hover:text-white focus-visible:ring-purple-400',
    reasoning:
      'bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white shadow-sm border border-amber-700/40 focus-visible:ring-amber-500',
    success:
      'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-sm border border-emerald-700/40 focus-visible:ring-emerald-500',
    subtleNavy:
      'bg-slate-900/60 hover:bg-slate-800/80 text-purple-200 border border-purple-500/20 hover:border-purple-500/40',
  };

  const sizeStyles = {
    xs: 'text-xs px-2.5 py-1 rounded-md gap-1.5 font-medium',
    sm: 'text-xs px-3 py-1.5 rounded-lg gap-1.5 font-medium',
    md: 'text-sm px-4 py-2 rounded-lg gap-2 font-medium',
    lg: 'text-base px-5 py-2.5 rounded-xl gap-2.5 font-semibold',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      title={title}
      className={`inline-flex flex-row items-center justify-center transition-all duration-150 select-none outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:opacity-50 disabled:pointer-events-none cursor-pointer whitespace-nowrap ${variantStyles[variant] || variantStyles.primary} ${sizeStyles[size]} ${className}`}
    >
      {loading ? (
        <svg
          className="animate-spin h-4 w-4 text-current shrink-0"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : (
        Icon && <Icon className="w-4 h-4 shrink-0" />
      )}
      {children && (
        <span className="inline-flex flex-row items-center justify-center gap-1.5 whitespace-nowrap">
          {children}
        </span>
      )}
      {!loading && IconRight && <IconRight className="w-4 h-4 shrink-0" />}
    </button>
  );
}
