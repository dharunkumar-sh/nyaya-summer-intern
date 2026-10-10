import {
  Library,
  Sparkles,
  ArrowRight,
  Cpu,
} from "lucide-react";
import Badge from "../common/Badge";
import Button from "../common/Button";
import { Link } from "react-router-dom";
import BilingualQueryLibrarySection from "./BilingualQueryLibrarySection";

export default function QueryLibraryView() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Breadcrumb & Navigation Anchor */}
      <div className="flex items-center justify-between text-xs text-slate-500 pb-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Link to="/" className="hover:text-indigo-600 transition-colors">
            Dashboard
          </Link>
          <span>/</span>
          <span className="text-slate-700 font-semibold">Corpus & Evidence</span>
          <span>/</span>
          <span className="text-indigo-700 font-bold">Query Library</span>
        </div>

        <Link
          to="/query-center"
          className="inline-flex items-center gap-1 text-xs font-semibold text-purple-700 hover:text-purple-900 bg-purple-50 hover:bg-purple-100 border border-purple-200 px-2.5 py-1 rounded-lg transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-purple-600" />
          <span>Interactive Query Center</span>
          <ArrowRight className="w-3 h-3 ml-0.5" />
        </Link>
      </div>

      {/* Top Banner / Hero Card */}
      <div className="bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-900 text-white rounded-2xl p-6 sm:p-7 shadow-xl border border-indigo-800/60 relative overflow-hidden">
        {/* Subtle background ornamentation */}
        <div className="absolute right-0 top-0 translate-x-8 -translate-y-8 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute right-1/4 bottom-0 translate-y-12 w-48 h-48 bg-purple-500/10 rounded-full blur-2xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2.5 max-w-3xl">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="p-1.5 rounded-lg bg-indigo-500/20 border border-indigo-400/30 text-indigo-300">
                <Library className="w-4 h-4" />
              </span>
              <Badge variant="purple" size="xs">
                Canonical Research Corpus
              </Badge>
              <Badge variant="blue" size="xs">
                Curated Inquiries
              </Badge>
              <span className="text-[11px] font-semibold text-emerald-300 font-mono bg-emerald-950/60 border border-emerald-700/50 px-2 py-0.5 rounded-full">
                Bilingual (தமிழ் + English)
              </span>
            </div>

            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-white">
              Canonical Bilingual Research Queries Library
            </h1>
            <p className="text-sm font-serif text-indigo-200 italic">
              தொல்காப்பிய இருமொழி வினா களஞ்சியம் • இலக்கணம், அகத்திணை, புறத்திணை &amp; மெய்ப்பாட்டியல்
            </p>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans pt-1">
              Complete, browsable repository of curated natural-language inquiries over the Tolkāppiyam corpus. Every question seamlessly pairs Classical Tamil terminology with rigorous analytical English epistemics, ready to load and execute across the 3-channel Hybrid RAG and 5-stage Pañcāvayava deduction pipeline.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0 self-start lg:self-auto">
            <Link to="/query-center">
              <Button
                variant="primary"
                size="md"
                icon={Sparkles}
                iconRight={ArrowRight}
                className="w-full text-xs font-bold bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 shadow-md border-0"
              >
                Go to Query Center
              </Button>
            </Link>
            <Link to="/reasoning">
              <Button
                variant="outline"
                size="md"
                icon={Cpu}
                className="w-full text-xs font-semibold text-slate-200 border-indigo-700/60 bg-indigo-950/40 hover:bg-indigo-900/60"
              >
                Reasoning Trace
              </Button>
            </Link>
          </div>
        </div>

        {/* Quick KPI Stat Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2.5 pt-6 mt-6 border-t border-indigo-800/60 text-xs">
          <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
            <span className="text-[10px] text-indigo-300 uppercase font-mono block">Grammar</span>
            <span className="font-bold text-white text-sm sm:text-base">314</span>
            <span className="text-[10px] text-slate-400 block font-serif">இலக்கணம்</span>
          </div>

          <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
            <span className="text-[10px] text-indigo-300 uppercase font-mono block">Akam Love</span>
            <span className="font-bold text-white text-sm sm:text-base">278</span>
            <span className="text-[10px] text-slate-400 block font-serif">அகத்திணை</span>
          </div>

          <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
            <span className="text-[10px] text-indigo-300 uppercase font-mono block">Puram Heroics</span>
            <span className="font-bold text-white text-sm sm:text-base">165</span>
            <span className="text-[10px] text-slate-400 block font-serif">புறத்திணை</span>
          </div>

          <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
            <span className="text-[10px] text-indigo-300 uppercase font-mono block">Ethics &amp; Culture</span>
            <span className="font-bold text-white text-sm sm:text-base">101</span>
            <span className="text-[10px] text-slate-400 block font-serif">அறநெறி</span>
          </div>

          <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
            <span className="text-[10px] text-indigo-300 uppercase font-mono block">Literature</span>
            <span className="font-bold text-white text-sm sm:text-base">89</span>
            <span className="text-[10px] text-slate-400 block font-serif">இலக்கியம்</span>
          </div>

          <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 backdrop-blur-xs">
            <span className="text-[10px] text-indigo-300 uppercase font-mono block">Commentary &amp; Meta</span>
            <span className="font-bold text-white text-sm sm:text-base">53</span>
            <span className="text-[10px] text-slate-400 block font-serif">உரை &amp; மெய்யியல்</span>
          </div>
        </div>
      </div>

      {/* Main Queries Library Section with Filter and Pagination */}
      <BilingualQueryLibrarySection />
    </div>
  );
}
