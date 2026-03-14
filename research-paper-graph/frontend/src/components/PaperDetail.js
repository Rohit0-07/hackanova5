import React from 'react';
import { FileText, User, Calendar, Link as LinkIcon, AlertCircle, Network, Microscope, CheckCircle, Megaphone, Brain, AlertTriangle, ExternalLink } from 'lucide-react';

const PaperDetail = ({ paper, analysis }) => {
  if (!paper) return null;

  return (
    <div className="space-y-0">
      {/* Header Section - Gradient Background */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-2xl" />
        <div className="relative z-10">
          <h2 className="text-2xl font-bold text-white mb-3 leading-snug">{paper.title}</h2>
          <div className="flex flex-wrap gap-3 text-sm">
            {paper.authors && paper.authors.length > 0 && (
              <div className="flex items-center gap-1.5 text-indigo-100">
                <User size={14} />
                <span className="line-clamp-1">{paper.authors.slice(0, 2).join(', ')}{paper.authors.length > 2 ? ` +${paper.authors.length - 2}` : ''}</span>
              </div>
            )}
            {paper.year && (
              <div className="flex items-center gap-1.5 text-indigo-100">
                <Calendar size={14} />
                <span>{paper.year}</span>
              </div>
            )}
            {paper.url && (
              <a 
                href={paper.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-indigo-100 hover:text-white transition-colors"
              >
                <ExternalLink size={14} />
                <span className="text-xs font-bold">Open Paper</span>
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Abstract Section */}
      {paper.abstract && (
        <div className="border-b border-slate-700/50 p-6 bg-slate-900/30">
          <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-3 flex items-center gap-2">
            <div className="w-2 h-2 bg-cyan-400 rounded-full"></div> Overview
          </h3>
          <p className="text-sm text-slate-300 leading-relaxed italic font-medium">
            {paper.abstract}
          </p>
        </div>
      )}
      
      <div className="space-y-0">
        {/* Extracted Artifacts (Figures/Tables) */}
        {paper.artifacts && paper.artifacts.length > 0 && (
          <div className="border-b border-slate-700/50 p-6 bg-slate-900/20">
            <h3 className="text-xs font-black uppercase tracking-widest text-purple-400 mb-4 flex items-center gap-2">
              <div className="w-2 h-2 bg-purple-400 rounded-full"></div> Visual Artifacts
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {paper.artifacts.map((art, i) => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4 shadow-sm">
                  <div className="flex items-center gap-2 mb-3">
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${art.type === 'table' ? 'bg-blue-500/20 text-blue-400' : 'bg-orange-500/20 text-orange-400'}`}>
                      {art.type.toUpperCase()}
                    </span>
                    <span className="text-xs font-bold text-slate-200">{art.content?.title || art.content?.number || `Artifact ${i+1}`}</span>
                  </div>
                  {art.type === 'table' ? (
                    <div className="overflow-x-auto">
                      <table className="min-w-full text-[10px] border-collapse text-slate-300">
                        <thead>
                          <tr>
                            {art.content.columns?.map((col, j) => (
                              <th key={j} className="border-b border-white/10 p-1 text-left bg-white/5">{col}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {art.content.rows?.slice(0, 5).map((row, k) => (
                            <tr key={k}>
                              {row.map((val, l) => (
                                <td key={l} className="border-b border-white/5 p-1">{val}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {art.content.rows?.length > 5 && <p className="text-[8px] text-slate-500 mt-1 italic">... and {art.content.rows.length - 5} more rows</p>}
                    </div>
                  ) : art.type === 'figure' || art.type === 'image' ? (
                    <div className="flex flex-col gap-2">
                       {art.content.image_path && (
                         <img src={art.content.image_path} alt={art.content.caption || 'Extracted figure'} className="rounded-lg object-contain w-full max-h-48 border border-white/5" />
                       )}
                       <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5 italic text-[11px] text-slate-400">
                         {art.content.caption || art.content.description}
                       </div>
                    </div>
                  ) : (
                    <div className="bg-slate-900/50 p-3 rounded-lg border border-white/5 italic text-xs text-slate-400">
                      {art.content?.caption || art.content?.description}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Sections */}
        {analysis && !analysis.status && (
          <>
            {/* Methodology */}
            {analysis.methodology && (
              <div className="border-b border-slate-700/50 p-6 bg-gradient-to-br from-amber-500/10 to-orange-500/5">
                <h3 className="text-xs font-black uppercase tracking-widest text-amber-400 mb-3 flex items-center gap-2">
                  <Microscope size={14} className="text-amber-500" /> Methodology
                </h3>
                <p className="text-sm text-amber-100/90 leading-relaxed mb-3 font-medium">{analysis.methodology?.approach || analysis.methodology}</p>
                {analysis.methodology?.evidence && (
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-amber-500/20 italic text-xs text-amber-200/70">
                    <span className="font-bold text-amber-300">Evidence:</span> "{analysis.methodology.evidence}"
                  </div>
                )}
              </div>
            )}

            {/* Key Findings */}
            {analysis.key_findings && analysis.key_findings.length > 0 && (
              <div className="border-b border-slate-700/50 p-6 bg-gradient-to-br from-emerald-500/10 to-green-500/5">
                <h3 className="text-xs font-black uppercase tracking-widest text-emerald-400 mb-4 flex items-center gap-2">
                  <CheckCircle size={14} className="text-emerald-500" /> Key Findings
                </h3>
                <ul className="space-y-3">
                  {(analysis.key_findings || []).map((item, i) => (
                    <li key={i}>
                      <p className="text-sm text-emerald-100 font-semibold leading-snug">{item.finding || item}</p>
                      {item.evidence && (
                        <p className="text-xs text-emerald-200/60 bg-slate-950/60 p-2 rounded border border-emerald-500/20 italic mt-2">
                          "{item.evidence}"
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Claims & Contributions */}
            {(analysis.claims || analysis.contributions) && (analysis.claims?.length > 0 || analysis.contributions?.length > 0) && (
              <div className="border-b border-slate-700/50 p-6 bg-gradient-to-br from-purple-500/10 to-fuchsia-500/5">
                <h3 className="text-xs font-black uppercase tracking-widest text-purple-400 mb-4 flex items-center gap-2">
                  <Megaphone size={14} className="text-purple-500" /> Claims & Contributions
                </h3>
                <ul className="space-y-3">
                  {(analysis.claims || analysis.contributions || []).map((item, i) => (
                    <li key={i}>
                      <p className="text-sm text-purple-100 font-semibold leading-snug">{item.claim || item.contribution || item}</p>
                      {item.evidence && (
                        <p className="text-xs text-purple-200/60 bg-slate-950/60 p-2 rounded border border-purple-500/20 italic mt-2">
                          "{item.evidence}"
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Limitations */}
            {analysis.limitations && analysis.limitations.length > 0 && (
              <div className="border-b border-slate-700/50 p-6 bg-gradient-to-br from-rose-500/10 to-red-500/5">
                <h3 className="text-xs font-black uppercase tracking-widest text-rose-400 mb-4 flex items-center gap-2">
                  <AlertTriangle size={14} className="text-rose-500" /> Limitations
                </h3>
                <ul className="space-y-2">
                  {(analysis.limitations || []).map((limit, i) => (
                    <li key={i} className="flex gap-2 text-xs text-rose-100/80">
                      <AlertCircle size={12} className="text-rose-400 mt-0.5 shrink-0" />
                      <span>{limit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default PaperDetail;
