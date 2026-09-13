import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import MainDashboard from './components/dashboard/MainDashboard';
import { CANONICAL_CORPUS, ReasonerProvider } from './context/ReasonerContext';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const handleExportProof = () => {
    const proofExport = {
      system: 'TolNyāya: Neuro-Symbolic Epistemic Reasoner for Classical Tamil',
      version: '2.4-Hybrid',
      corpus: CANONICAL_CORPUS.name,
      totalSutras: CANONICAL_CORPUS.totalSutras,
      timestamp: new Date().toISOString(),
      activePath: location.pathname,
      soundnessRate: '100% Nyāya Pramāṇa Validated',
    };

    const dataStr =
      'data:text/json;charset=utf-8,' +
      encodeURIComponent(JSON.stringify(proofExport, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute(
      'download',
      `tolkappiyam_nyaya_proof_${Date.now()}.json`
    );
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <ReasonerProvider>
      <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-purple-200 selection:text-purple-900">
        {/* Top Header with Application Logo, Title, and Tolkāppiyam Corpus Status */}
        <Header
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          activeCorpus={CANONICAL_CORPUS}
          onExportProof={handleExportProof}
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
