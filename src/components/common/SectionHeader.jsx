
/**
 * Reusable SectionHeader component for workspace sections.
 */
export default function SectionHeader({
  title,
  subtitle,
  badge = null,
  icon: Icon = null,
  actions = null,
  className = '',
}) {
  return (
    <div
      className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 mb-4 border-b border-slate-200/80 ${className}`}
    >
      <div className="flex items-start sm:items-center gap-2.5">
        {Icon && (
          <div className="p-2 rounded-lg bg-purple-50 text-purple-700 border border-purple-200/60 shrink-0">
            <Icon className="w-4 h-4" />
          </div>
        )}
        <div>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-base font-bold text-slate-900 tracking-tight">
              {title}
            </h2>
            {badge}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-0.5 font-normal">
              {subtitle}
            </p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
          {actions}
        </div>
      )}
    </div>
  );
}
