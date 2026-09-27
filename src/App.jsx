import { useState } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import MainDashboard from './components/dashboard/MainDashboard';
import { CANONICAL_CORPUS, ReasonerProvider } from './context/ReasonerContext';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <ReasonerProvider>
      <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-purple-200 selection:text-purple-900">
        {/* Top Header with Application Logo, Title, and Tolkāppiyam Corpus Status */}
        <Header
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          activeCorpus={CANONICAL_CORPUS}
        />

        {/* Main Workspace Layout */}
        <div className="flex-1 flex w-full relative">
          {/* Left Sidebar with Tolkāppiyam Corpus Card, React Router Navigation, Quick Stats, and KG Health */}
          <Sidebar
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />

          {/* Main Content Area rendering separate route views via react-router-dom */}
          <MainDashboard />
        </div>
      </div>
    </ReasonerProvider>
  );
}
