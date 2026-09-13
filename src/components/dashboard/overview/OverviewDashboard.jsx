import OverviewHeroBanner from './OverviewHeroBanner';
import OverviewKpiGrid from './OverviewKpiGrid';
import OverviewTinaiLandscapeExplorer from './OverviewTinaiLandscapeExplorer';
import OverviewPramanaMatrix from './OverviewPramanaMatrix';
import OverviewHetvabhasaGuard from './OverviewHetvabhasaGuard';
import OverviewCorpusAtikaramCard from './OverviewCorpusAtikaramCard';
import OverviewModulesQuickNav from './OverviewModulesQuickNav';

export default function OverviewDashboard() {
  return (
    <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-200">
      {/* 1. Hero Executive System Banner */}
      <OverviewHeroBanner />

      {/* 2. Key Epistemic & Architectural KPI Cards */}
      <OverviewKpiGrid />

      {/* 3. Specialized Research Workspace Quick Navigation Hub */}
      <OverviewModulesQuickNav />

      {/* 4. Classical Tamil Tiṇai Eco-Poetic Triad Explorer (Mutal, Karu, Uri) */}
      <OverviewTinaiLandscapeExplorer />

      {/* 5. Epistemic Instruments (4 Pramāṇas in Tolkāppiyam Epistemology) */}
      <OverviewPramanaMatrix />

      {/* 6. Classical Fallacy Guard (Hetvābhāsa Defeasible Logic) */}
      <OverviewHetvabhasaGuard />

      {/* 7. Canonical 3-Atikāram Corpus Architecture */}
      <OverviewCorpusAtikaramCard />
    </div>
  );
}
