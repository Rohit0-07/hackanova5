import React, { useState } from 'react';
import { X, ExternalLink, MapPin, FileText, BookOpen, Monitor, Globe, Loader } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * SourceViewer modal — shows where a finding/claim was cited from,
 * plus an inline paper preview via iframe.
 *
 * Props:
 *   isOpen       {boolean}
 *   onClose      {function}
 *   paperTitle   {string}
 *   paperUrl     {string}
 *   sectionName  {string}
 *   quote        {string}
 *   findingText  {string}
 */
const SourceViewer = ({ isOpen, onClose, paperTitle, paperUrl, sectionName, quote, findingText }) => {
  const [showPreview, setShowPreview] = useState(false);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeError, setIframeError] = useState(false);

  if (!isOpen) return null;

  // Build a previewable URL:
  // ArXiv papers → convert to ar5iv.labs.arxiv.org which renders HTML (embeddable)
  // Semantic Scholar / DOI / others → try direct embed
  const getPreviewUrl = (url) => {
    if (!url) return null;
    // arxiv.org/abs/XXXX → ar5iv renders in browser
    const arxivAbsMatch = url.match(/arxiv\.org\/abs\/([\d.]+v?\d*)/i);
    if (arxivAbsMatch) {
      return `https://ar5iv.labs.arxiv.org/html/${arxivAbsMatch[1]}`;
    }
    // arxiv.org/pdf → use ar5iv too
    const arxivPdfMatch = url.match(/arxiv\.org\/pdf\/([\d.]+v?\d*)/i);
    if (arxivPdfMatch) {
      return `https://ar5iv.labs.arxiv.org/html/${arxivPdfMatch[1]}`;
    }
    // Otherwise fallback to the URL directly
    return url;
  };

  const previewUrl = getPreviewUrl(paperUrl);

  const handleTogglePreview = () => {
    setShowPreview(p => !p);
    setIframeLoaded(false);
    setIframeError(false);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Modal — expands horizontally when preview is open */}
          <motion.div
            key="modal"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300, mass: 0.6 }}
            className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none"
          >
            <motion.div
              layout
              animate={{ width: showPreview ? '90vw' : '100%', maxWidth: showPreview ? '1200px' : '560px' }}
              transition={{ type: 'spring', damping: 30, stiffness: 280 }}
              className="bg-slate-900 border border-slate-700/60 rounded-2xl shadow-[0_25px_60px_rgba(0,0,0,0.7)] pointer-events-auto overflow-hidden flex flex-row"
              onClick={e => e.stopPropagation()}
              style={{ maxHeight: '90vh' }}
            >
              {/* Left panel: source info */}
              <div className="flex flex-col overflow-y-auto" style={{ minWidth: '340px', maxWidth: showPreview ? '400px' : '100%', flex: showPreview ? '0 0 400px' : '1 1 auto' }}>
                {/* Header */}
                <div className="bg-gradient-to-r from-indigo-600/90 to-purple-600/80 px-6 py-4 flex items-start justify-between gap-3 shrink-0">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <MapPin size={13} className="text-indigo-200 shrink-0" />
                      <span className="text-[10px] font-extrabold uppercase tracking-widest text-indigo-200">Cited From</span>
                    </div>
                    <h3 className="text-base font-bold text-white leading-snug line-clamp-2">
                      {paperTitle || 'Unknown Paper'}
                    </h3>
                  </div>
                  <button onClick={onClose} className="shrink-0 bg-white/10 hover:bg-white/20 text-white p-1.5 rounded-lg transition-colors mt-0.5">
                    <X size={16} />
                  </button>
                </div>

                {/* Section Badge */}
                {sectionName && (
                  <div className="px-6 pt-5 pb-0 shrink-0">
                    <div className="flex items-center gap-2">
                      <BookOpen size={13} className="text-indigo-400" />
                      <span className="text-xs font-black uppercase tracking-widest text-indigo-400">Section:</span>
                      <span className="text-xs font-bold text-indigo-300 bg-indigo-500/15 border border-indigo-500/25 px-3 py-1 rounded-full">
                        {sectionName}
                      </span>
                    </div>
                  </div>
                )}

                {/* Body */}
                <div className="p-6 space-y-5 flex-1">
                  {/* Derived Finding */}
                  {findingText && (
                    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4">
                      <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 block mb-2">Derived Finding / Claim</span>
                      <p className="text-sm text-slate-200 font-semibold leading-relaxed">{findingText}</p>
                    </div>
                  )}

                  {/* Highlighted Quote */}
                  {quote ? (
                    <div className="relative">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText size={13} className="text-amber-400" />
                        <span className="text-[10px] font-black uppercase tracking-widest text-amber-400">Exact Text from Paper</span>
                      </div>
                      <div className="relative bg-amber-500/8 border border-amber-500/25 rounded-xl p-5 overflow-hidden">
                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-amber-400 to-orange-500 rounded-l-xl" />
                        <p className="pl-3 text-sm text-amber-100/95 leading-relaxed italic font-medium">"{quote}"</p>
                        <div className="absolute inset-0 bg-gradient-to-r from-amber-400/5 to-transparent pointer-events-none rounded-xl" />
                      </div>
                    </div>
                  ) : (
                    <div className="bg-slate-800/30 border border-slate-700/30 rounded-xl p-4 text-center">
                      <p className="text-xs text-slate-500 italic">No verbatim quote available for this item.</p>
                    </div>
                  )}
                </div>

                {/* Footer Actions */}
                <div className="px-6 pb-6 flex flex-col gap-2 shrink-0">
                  {/* Preview toggle */}
                  {previewUrl && (
                    <button
                      onClick={handleTogglePreview}
                      className={`flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all border ${
                        showPreview
                          ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                          : 'bg-purple-600/20 border-purple-500/30 text-purple-300 hover:bg-purple-600/30 hover:border-purple-400/50'
                      }`}
                    >
                      <Monitor size={13} />
                      {showPreview ? 'Hide Paper Preview' : 'Preview Paper Inline'}
                    </button>
                  )}

                  {/* Row: Open Full Paper + Close */}
                  <div className="flex items-center gap-2">
                    {paperUrl ? (
                      <a
                        href={paperUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold py-3 px-5 rounded-xl transition-all shadow-lg hover:shadow-indigo-500/25 group"
                      >
                        <ExternalLink size={15} className="group-hover:scale-110 transition-transform" />
                        Open Full Paper
                      </a>
                    ) : (
                      <div className="flex-1 flex items-center justify-center gap-2 bg-slate-800 text-slate-500 text-sm font-bold py-3 px-5 rounded-xl cursor-not-allowed border border-slate-700">
                        <ExternalLink size={15} />
                        No External URL
                      </div>
                    )}
                    <button
                      onClick={onClose}
                      className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-sm font-bold transition-colors border border-slate-700 hover:border-slate-600"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>

              {/* Right panel: inline paper preview (iframe) */}
              <AnimatePresence>
                {showPreview && previewUrl && (
                  <motion.div
                    key="preview-panel"
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: '100%' }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ type: 'spring', damping: 28, stiffness: 260 }}
                    className="flex-1 relative bg-slate-950 border-l border-slate-700/60 overflow-hidden min-w-0"
                  >
                    {/* Loading overlay */}
                    {!iframeLoaded && !iframeError && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-slate-950 z-10">
                        <Loader size={22} className="text-indigo-400 animate-spin" />
                        <p className="text-xs text-slate-400 font-medium">Loading paper…</p>
                        <p className="text-[10px] text-slate-600 max-w-[200px] text-center">
                          Rendering from ar5iv.labs.arxiv.org
                        </p>
                      </div>
                    )}

                    {/* Error state */}
                    {iframeError && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-slate-950 z-10 p-8">
                        <Globe size={32} className="text-slate-600" />
                        <div className="text-center">
                          <p className="text-sm font-bold text-slate-400 mb-2">Preview unavailable</p>
                          <p className="text-xs text-slate-500 leading-relaxed mb-4">
                            This paper can't be embedded. Open it directly instead.
                          </p>
                        </div>
                        {paperUrl && (
                          <a
                            href={paperUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition-all"
                          >
                            <ExternalLink size={13} />
                            Open in New Tab
                          </a>
                        )}
                      </div>
                    )}

                    {/* Preview header bar */}
                    <div className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between px-4 py-2.5 bg-slate-900/90 backdrop-blur-md border-b border-slate-700/50">
                      <div className="flex items-center gap-2">
                        <Globe size={12} className="text-slate-500" />
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider truncate max-w-[300px]">
                          {previewUrl}
                        </span>
                      </div>
                      {paperUrl && (
                        <a
                          href={paperUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-[10px] font-bold text-slate-400 hover:text-indigo-300 transition-colors shrink-0"
                        >
                          <ExternalLink size={11} />
                          Open Tab
                        </a>
                      )}
                    </div>

                    {/* The iframe */}
                    <iframe
                      src={previewUrl}
                      title="Paper Preview"
                      className="w-full h-full border-0"
                      style={{ paddingTop: '40px', height: '100%' }}
                      onLoad={() => setIframeLoaded(true)}
                      onError={() => setIframeError(true)}
                      sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default SourceViewer;
