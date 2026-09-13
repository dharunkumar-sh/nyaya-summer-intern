export default function LotusLogo({ className = 'w-8 h-8', showGlow = true }) {
  return (
    <div className={`relative flex items-center justify-center shrink-0 ${className}`}>
      {showGlow && (
        <span className="absolute -inset-1 rounded-full bg-gradient-to-tr from-purple-600/40 via-fuchsia-500/30 to-indigo-500/40 blur-[3px] opacity-70" />
      )}
      <svg
        viewBox="0 0 40 40"
        className="w-full h-full relative z-10 drop-shadow-[0_1px_4px_rgba(168,85,247,0.4)]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="lotusPetalGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#6d28d9" />
            <stop offset="45%" stopColor="#a855f7" />
            <stop offset="100%" stopColor="#f472b6" />
          </linearGradient>
          <linearGradient id="lotusSideGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#5b21b6" />
            <stop offset="60%" stopColor="#9333ea" />
            <stop offset="100%" stopColor="#e879f9" />
          </linearGradient>
          <linearGradient id="lotusOuterGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#4c1d95" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>
        </defs>

        {/* Outer Left Petal */}
        <path
          d="M17.5 17 C9.5 19.5, 6 27, 18 29.5 C13 26.5, 12.5 20.5, 17.5 17 Z"
          fill="url(#lotusOuterGrad)"
          fillOpacity="0.85"
        />

        {/* Outer Right Petal */}
        <path
          d="M22.5 17 C30.5 19.5, 34 27, 22 29.5 C27 26.5, 27.5 20.5, 22.5 17 Z"
          fill="url(#lotusOuterGrad)"
          fillOpacity="0.85"
        />

        {/* Mid-Left Petal */}
        <path
          d="M19 11.5 C12.5 14.5, 10.5 23, 19 28.5 C15.5 22.5, 15.5 16.5, 19 11.5 Z"
          fill="url(#lotusSideGrad)"
          fillOpacity="0.95"
        />

        {/* Mid-Right Petal */}
        <path
          d="M21 11.5 C27.5 14.5, 29.5 23, 21 28.5 C24.5 22.5, 24.5 16.5, 21 11.5 Z"
          fill="url(#lotusSideGrad)"
          fillOpacity="0.95"
        />

        {/* Central Core Petal */}
        <path
          d="M20 6.5 C17.8 13, 16.8 21.5, 20 29.5 C23.2 21.5, 22.2 13, 20 6.5 Z"
          fill="url(#lotusPetalGrad)"
        />

        {/* Base Calyx/Platform */}
        <path
          d="M13 29.5 C16.5 32.5, 23.5 32.5, 27 29.5 C24.5 31.2, 15.5 31.2, 13 29.5 Z"
          fill="#c084fc"
        />

        {/* Golden Central Bindu (Epistemic Core) */}
        <circle cx="20" cy="17.5" r="1.5" fill="#fef08a" />
        <circle cx="20" cy="17.5" r="0.8" fill="#eab308" />
      </svg>
    </div>
  );
}
