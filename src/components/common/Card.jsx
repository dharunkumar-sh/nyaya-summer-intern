
/**
 * Reusable Card component for structured academic panels.
 */
export default function Card({
  title,
  subtitle,
  icon: Icon = null,
  actions = null,
  children,
  footer = null,
  accent = 'none', // 'none' | 'purple' | 'green' | 'orange' | 'blue'
  accentPosition = 'left', // 'left' | 'top'
  padding = 'md', // 'none' | 'sm' | 'md' | 'lg'
  className = '',
  headerClassName = '',
}) {
  const accentBorders = {
    none: '',
    purple: accentPosition === 'left' ? 'border-l-4 border-l-purple-600' : 'border-t-4 border-t-purple-600',
    green: accentPosition === 'left' ? 'border-l-4 border-l-emerald-600' : 'border-t-4 border-t-emerald-600',
    orange: accentPosition === 'left' ? 'border-l-4 border-l-amber-500' : 'border-t-4 border-t-amber-500',
    blue: accentPosition === 'left' ? 'border-l-4 border-l-blue-600' : 'border-t-4 border-t-blue-600',
  };

  const paddingStyles = {
    none: 'p-0',
    sm: 'p-3',
    md: 'p-4 sm:p-5',
    lg: 'p-6 sm:p-7',
  };

  const hasHeader = title || subtitle || Icon || actions;

  return (
    <div
      className={`bg-white rounded-xl border border-slate-200/90 shadow-xs hover:shadow-sm transition-all duration-200 overflow-hidden flex flex-col ${accentBorders[accent] || ''} ${className}`}
    >
      {hasHeader && (
        <div
          className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-5 py-4 border-b border-slate-100 bg-slate-50/50 ${headerClassName}`}
        >
          <div className="flex items-start sm:items-center gap-2.5 min-w-0 flex-1">
            {Icon && (
              <div className="p-1.5 rounded-lg bg-slate-100 border border-slate-200/80 text-slate-700 shrink-0 mt-0.5 sm:mt-0">
                <Icon className="w-4 h-4" />
              </div>
            )}
            <div className="min-w-0 flex-1">
              {title && (
                <h3 className="text-sm sm:text-base font-semibold text-slate-900 tracking-tight leading-snug">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs text-slate-500 mt-0.5 leading-normal">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {actions && <div className="flex items-center gap-2 flex-wrap shrink-0 sm:self-center">{actions}</div>}
        </div>
      )}

      <div className={`flex-1 ${paddingStyles[padding]}`}>
        {children}
      </div>

      {footer && (
        <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/70 text-xs text-slate-500">
          {footer}
        </div>
      )}
    </div>
  );
}
