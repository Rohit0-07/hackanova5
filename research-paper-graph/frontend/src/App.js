import React, { useState, useEffect, useMemo } from 'react';
import { Search, Loader2, Network, BookOpen, MessageSquare, List, History, ChevronRight, AlertTriangle, Lightbulb, SplitSquareVertical, Clock, Play, X, Compass, RotateCcw, Zap, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { pipelineApi, chatApi } from './utils/api';
import KnowledgeGraph from './components/KnowledgeGraph';
import PaperDetail from './components/PaperDetail';

function App() {
  const [query, setQuery] = useState('');
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('sessionId') || null);
  const [status, setStatus] = useState(() => localStorage.getItem('status') || 'idle');
  const [pipelineState, setPipelineState] = useState(null);
  
  // Dashboard UI state
  const [activePane, setActivePane] = useState('none'); // 'none', 'synthesis', 'library', 'chat'
  const [selectedPaper, setSelectedPaper] = useState(null);
  
  // Chat state
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [sessions, setSessions] = useState([]);
  
  // Graph Search State
  const [graphSearchQuery, setGraphSearchQuery] = useState('');
  
  // Landing Page state
  const [sessionSearch, setSessionSearch] = useState('');
  const [sessionSort, setSessionSort] = useState('newest');

  // Settings state
  const [maxPapers, setMaxPapers] = useState(10);
  const [maxDepth, setMaxDepth] = useState(2);
  const [useGemini, setUseGemini] = useState(true);

  // Synthesis generation state
  const [isSynthesisGenerating, setIsSynthesisGenerating] = useState(false);
  const [synthesisProgress, setSynthesisProgress] = useState(0);

  // Reset/Re-analysis state
  const [reanalyzingPaperId, setReanalyzingPaperId] = useState(null);

  // Graph query parameters
  const [graphParams, setGraphParams] = useState({
    similarityThreshold: 0.5,
    maxHops: 2,
    nodeTypes: ['Paper', 'Concept', 'Finding'],
  });

  useEffect(() => {
    fetchSessions();
    if (sessionId && !pipelineState && status !== 'idle') {
      handleLoadSession(sessionId);
    }
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    localStorage.setItem('sessionId', sessionId || '');
    localStorage.setItem('status', status);
  }, [sessionId, status]);

  // Persist chat history whenever it changes
  useEffect(() => {
    if (sessionId && chatHistory.length > 0) {
      localStorage.setItem(`chatHistory_${sessionId}`, JSON.stringify(chatHistory));
    }
  }, [chatHistory, sessionId]);

  // Open library pane automatically if a paper is selected
  useEffect(() => {
    if (selectedPaper) {
      setActivePane('library');
    }
  }, [selectedPaper]);

  const fetchSessions = async () => {
    try {
      const res = await pipelineApi.listSessions();
      setSessions(res.data.sessions || []);
    } catch (err) {
      console.error('Failed to fetch sessions', err);
    }
  };

  const handleStartAnalysis = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setStatus('in_progress');
    setPipelineState(null);
    setSessionId(null);
    setChatHistory([]);
    setGraphSearchQuery('');
    setSelectedPaper(null);
    setActivePane('synthesis'); // Show synthesis by default while building

    try {
      const res = await pipelineApi.analyze(query, { 
        llm_provider: useGemini ? 'gemini' : 'ollama',
        max_papers: maxPapers,
        max_citation_depth: maxDepth
      });
      const newSessionId = res.data.session_id;
      setSessionId(newSessionId);
      
      pipelineApi.streamUpdates(
        newSessionId,
        (data) => {
          setPipelineState(data);
          if (data.status === 'completed') setStatus('completed');
          if (data.status === 'failed') setStatus('failed');
        },
        (err) => {
          console.error('Stream error', err);
          setStatus('failed');
        }
      );
    } catch (err) {
      console.error('Analysis failed', err);
      setStatus('failed');
    }
  };

  const handleLoadSession = async (sid) => {
    setSessionId(sid);
    setStatus('loading');
    
    // Load existing chat history if available
    const savedChat = localStorage.getItem(`chatHistory_${sid}`);
    if (savedChat) {
      try {
        setChatHistory(JSON.parse(savedChat));
      } catch(e) {
        setChatHistory([]);
      }
    } else {
      setChatHistory([]);
    }
    
    setGraphSearchQuery('');
    setSelectedPaper(null);
    setActivePane('synthesis');
    
    try {
      const res = await pipelineApi.getResults(sid);

      setSessions(prev => {
        const sessionData = prev.find(s => s.id === sid);
        if (sessionData && sessionData.query) {
           setQuery(sessionData.query);
        } else if (res.data.synthesis?.topic) {
           setQuery(res.data.synthesis.topic);
        }
        return prev;
      });

      setPipelineState(res.data);
      setStatus(res.data.status);
    } catch (err) {
      console.error('Failed to load session', err);
      setStatus('failed');
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim() || isChatLoading) return;

    const userMsg = { role: 'user', content: chatMessage };
    setChatHistory(prev => [...prev, userMsg]);
    setChatMessage('');
    setIsChatLoading(true);

    try {
      const res = await chatApi.sendMessage(sessionId, chatMessage);
      setChatHistory(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch (err) {
      console.error('Chat error:', err);
      // Fallback visual error
      let errorMsg = 'Agent failed to respond. Check API connection.';
      if (err.response && err.response.data && err.response.data.detail) {
        errorMsg = err.response.data.detail;
      }
      setChatHistory(prev => [...prev, { role: 'error', content: errorMsg }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleGenerateSynthesis = async () => {
    if (!sessionId || isSynthesisGenerating) return;
    
    setIsSynthesisGenerating(true);
    setSynthesisProgress(0);
    
    try {
      // Simulate progress updates (in real scenario, backend would stream this)
      const interval = setInterval(() => {
        setSynthesisProgress(prev => Math.min(prev + 10, 90));
      }, 300);

      const res = await pipelineApi.generateSynthesis(sessionId);
      
      clearInterval(interval);
      setSynthesisProgress(100);
      setPipelineState(prev => ({ ...prev, synthesis: res.data.synthesis }));
      
      setTimeout(() => setSynthesisProgress(0), 1000);
    } catch (err) {
      console.error('Synthesis generation failed:', err);
    } finally {
      setIsSynthesisGenerating(false);
    }
  };

  const handleReanalyzePaper = async (paperId) => {
    if (!sessionId || !paperId) return;
    
    setReanalyzingPaperId(paperId);
    
    try {
      const res = await pipelineApi.reanalyzePaper(sessionId, paperId);
      setPipelineState(prev => ({
        ...prev,
        analyses: { ...prev.analyses, [paperId]: res.data.analysis }
      }));
    } catch (err) {
      console.error('Paper re-analysis failed:', err);
    } finally {
      setReanalyzingPaperId(null);
    }
  };

  const formatDate = (ts) => {
    if (!ts) return 'Unknown Date';
    try {
      const date = new Date(ts * 1000);
      if (isNaN(date.getTime())) return 'Unknown Date';
      return date.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return 'Unknown Date';
    }
  };

  // Extract referenced papers from chat response markdown
  const extractCitedPapers = (markdownText) => {
    const linkRegex = /\*\*\[(.*?)\]\((.*?)\)\*\*/g;
    const cited = [];
    let match;
    while ((match = linkRegex.exec(markdownText)) !== null) {
      cited.push({
        title: match[1],
        url: match[2],
      });
    }
    return cited;
  };

  const currentAnalysis = useMemo(() => pipelineState?.analyses || {}, [pipelineState?.analyses]);
   const currentPapers = useMemo(() => pipelineState?.papers || [], [pipelineState?.papers]);
  const currentSynthesis = useMemo(() => pipelineState?.synthesis || {}, [pipelineState?.synthesis]);
  const currentGraphData = useMemo(() => pipelineState?.graph_nodes || { nodes: [], edges: [] }, [pipelineState?.graph_nodes]);

  const filteredSessions = useMemo(() => {
    let result = [...sessions];
    if (sessionSearch.trim()) {
      const lowerQ = sessionSearch.toLowerCase();
      result = result.filter(s => (s.query || s.id).toLowerCase().includes(lowerQ));
    }
    result.sort((a, b) => {
      if (sessionSort === 'newest') return b.created_at - a.created_at;
      if (sessionSort === 'oldest') return a.created_at - b.created_at;
      if (sessionSort === 'most_papers') return (b.papers_count || 0) - (a.papers_count || 0);
      return 0;
    });
    return result;
  }, [sessions, sessionSearch, sessionSort]);

  const renderLanding = () => (
    <div className="flex-1 flex flex-col p-8 w-full max-w-6xl mx-auto overflow-y-auto custom-scrollbar">
      {/* Header */}
      <header className="flex items-center gap-3 mb-16 mt-8 shrink-0">
        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 p-2.5 rounded-xl shadow-[0_0_20px_rgba(99,102,241,0.4)]">
          <Network size={26} className="text-white" />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">AgSearch</h1>
          <p className="text-xs text-indigo-400 uppercase tracking-widest font-bold">Autonomous Research Agent</p>
        </div>
      </header>

      {/* Main Search Area */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-10 shadow-2xl mb-12 shrink-0 relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <h2 className="text-4xl md:text-5xl font-extrabold text-white mb-6 tracking-tight">
          Automate Your Research
        </h2>
        <p className="text-slate-400 text-lg mb-10 max-w-3xl leading-relaxed">
          Enter a research question to autonomously crawl academic databases, follow citation trails, extract methodology, and generate a synthesized contradiction report.
        </p>

        <form onSubmit={handleStartAnalysis} className="w-full relative z-10">
          <div className="flex bg-slate-950/80 backdrop-blur-md border border-slate-700/50 hover:border-indigo-500/50 rounded-2xl p-2 items-center focus-within:border-indigo-500 focus-within:ring-4 focus-within:ring-indigo-500/20 transition-all shadow-inner">
            <div className="p-4 text-indigo-400">
              <Search size={28} />
            </div>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="E.g., What do recent papers say about attention mechanisms?"
              className="flex-1 bg-transparent border-none text-white focus:ring-0 text-xl placeholder-slate-600 outline-none w-full"
            />
            <button
              disabled={!query.trim() || status === 'loading'}
              className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 px-10 rounded-xl transition-all disabled:bg-slate-800 disabled:text-slate-500 flex items-center gap-3 shadow-lg hover:shadow-indigo-500/25"
            >
              {status === 'loading' ? <Loader2 size={20} className="animate-spin" /> : <Play size={20} />} 
              Analyze
            </button>
          </div>
          
          <div className="mt-8 flex flex-wrap items-center gap-8 text-sm bg-slate-950/40 p-5 rounded-2xl border border-slate-800/50 backdrop-blur-sm">
            <label className="flex items-center gap-3 text-slate-400">
              <span className="font-medium text-slate-300">Max Citation Depth:</span>
              <input type="number" min="1" max="5" value={maxDepth} onChange={e => setMaxDepth(parseInt(e.target.value))} className="bg-slate-900 border border-slate-700 rounded-lg w-16 px-3 py-2 text-center focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-white font-bold" />
            </label>
            <label className="flex items-center gap-3 text-slate-400">
              <span className="font-medium text-slate-300">Max Papers to Crawl:</span>
              <input type="number" min="5" max="50" value={maxPapers} onChange={e => setMaxPapers(parseInt(e.target.value))} className="bg-slate-900 border border-slate-700 rounded-lg w-16 px-3 py-2 text-center focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-white font-bold" />
            </label>
            <label className="flex items-center gap-3 text-slate-400 cursor-pointer ml-auto">
              <input type="checkbox" checked={useGemini} onChange={e => setUseGemini(e.target.checked)} className="w-5 h-5 rounded border-slate-700 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-slate-900 bg-slate-900" />
              <span className="font-bold text-slate-200 tracking-wide">Use Gemini for Deep Synthesis</span>
            </label>
          </div>
        </form>
      </div>

      {/* Recent Sessions */}
      <div className="flex-1 flex flex-col min-h-[400px] mt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 shrink-0">
          <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <History size={18} className="text-slate-500" /> Recent Research Sessions
          </h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input 
                type="text" 
                placeholder="Search sessions..." 
                value={sessionSearch}
                onChange={e => setSessionSearch(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 w-[240px] focus:bg-slate-900"
              />
            </div>
            <select 
              value={sessionSort}
              onChange={e => setSessionSort(e.target.value)}
              className="bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer focus:bg-slate-900 font-medium"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="most_papers">Most Papers</option>
            </select>
          </div>
        </div>
        
        {sessions.length === 0 ? (
          <div className="text-slate-500 italic p-12 border border-slate-800 border-dashed rounded-2xl text-center bg-slate-900/20 flex-1 flex flex-col items-center justify-center gap-4">
            <Compass size={40} className="text-slate-700" />
            <p>No past sessions found. Start a new analysis above.</p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="text-slate-500 italic p-12 border border-slate-800 border-dashed rounded-2xl text-center bg-slate-900/20 flex-1 flex flex-col items-center justify-center gap-4">
            <Search size={40} className="text-slate-700" />
            <p>No sessions match your search criteria.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 pb-12">
            {filteredSessions.map((s, i) => (
              <button 
                key={i}
                onClick={() => handleLoadSession(s.id)}
                className="text-left bg-slate-900 border border-slate-800/80 rounded-2xl p-6 hover:border-indigo-500 hover:shadow-xl hover:shadow-indigo-500/10 transition-all group relative overflow-hidden flex flex-col h-full hover:-translate-y-1"
              >
                <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-indigo-500 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="flex-1">
                  <h4 className="font-bold text-slate-100 text-lg line-clamp-2 leading-snug mb-3 group-hover:text-white transition-colors">{s.query || s.id}</h4>
                  {s.status === 'in_progress' && (
                    <span className="inline-block px-2.5 py-1 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px] uppercase font-bold tracking-widest mb-3">
                      In Progress
                    </span>
                  )}
                  {s.status === 'completed' && (
                    <span className="inline-block px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] uppercase font-bold tracking-widest mb-3">
                      Completed
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-5 text-xs text-slate-500 border-t border-slate-800/60 pt-4 w-full mt-2">
                  <span className="flex items-center gap-1.5"><Clock size={14} className="text-slate-600"/> {formatDate(s.created_at)}</span>
                  <span className="flex items-center gap-1.5"><Network size={14} className="text-indigo-900 group-hover:text-indigo-500 transition-colors"/> <strong className="text-slate-300 font-bold">{s.papers_count || 0}</strong> papers</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const renderSynthesisPane = () => (
    <div className="flex-1 overflow-y-auto custom-scrollbar p-6 bg-slate-900 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6 shrink-0">
        <h2 className="font-extrabold text-white text-xl flex items-center gap-3">
          <div className="bg-amber-500/20 p-2 rounded-lg text-amber-400"><Lightbulb size={20} /></div> 
          Synthesis Report
        </h2>
        <button onClick={() => setActivePane('none')} className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-lg transition-colors"><X size={16} /></button>
      </div>
      
      <div className="space-y-8 pb-8">
        <section>
          <h3 className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-3 flex items-center gap-2 border-b border-slate-800 pb-2">
            <BookOpen size={16} /> Overall Summary
          </h3>
          <div className="text-sm text-slate-300 leading-relaxed bg-slate-950/50 p-5 rounded-xl border border-slate-800/50 shadow-inner">
            {currentSynthesis.literature_summary || (status === 'in_progress' ? <span className="text-slate-500 italic flex items-center gap-2"><Loader2 size={14} className="animate-spin"/> Waiting for enough papers to synthesize...</span> : 'No summary generated yet.')}
          </div>
        </section>

        {currentSynthesis.contradictions?.length > 0 && (
          <section>
            <h3 className="text-xs font-bold text-amber-500 uppercase tracking-widest mb-3 flex items-center gap-2 border-b border-slate-800 pb-2">
              <AlertTriangle size={16} /> Contradictions
            </h3>
            <div className="space-y-4">
              {currentSynthesis.contradictions.map((c, i) => (
                <div key={i} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 shadow-sm">
                  <h4 className="text-sm font-bold text-amber-400 mb-2">{c.topic}</h4>
                  <p className="text-xs text-slate-300 mb-4 italic leading-relaxed">"{c.description}"</p>
                  <div className="flex flex-col gap-2">
                    <div className="bg-slate-900 border border-slate-700/50 rounded-lg p-3">
                      <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Argues For</span>
                      <span className="text-xs text-slate-200">{c.paper_a}</span>
                    </div>
                    <div className="bg-slate-900 border border-slate-700/50 rounded-lg p-3">
                      <span className="text-[10px] text-slate-500 uppercase font-bold block mb-1">Argues Against / Alternatively</span>
                      <span className="text-xs text-slate-200">{c.paper_b}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {currentSynthesis.research_gaps?.length > 0 && (
          <section>
            <h3 className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3 flex items-center gap-2 border-b border-slate-800 pb-2">
              <Network size={16} /> Identified Gaps
            </h3>
            <div className="space-y-3">
              {currentSynthesis.research_gaps.map((g, i) => (
                <div key={i} className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-5 relative overflow-hidden group shadow-sm">
                  <div className={`absolute top-0 right-0 w-1.5 h-full ${g.priority === 'High' ? 'bg-rose-500' : 'bg-purple-500'}`} />
                  <h4 className="text-sm font-bold text-slate-100 mb-2 pr-4">{g.gap}</h4>
                  <span className={`inline-block mb-3 text-[10px] px-2 py-0.5 rounded font-bold uppercase tracking-widest ${g.priority === 'High' ? 'bg-rose-500/20 text-rose-400' : 'bg-purple-500/20 text-purple-400'}`}>
                    {g.priority} Priority
                  </span>
                  <p className="text-xs text-slate-400 leading-relaxed pr-2">{g.justification}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );

  const renderLibraryPane = () => (
    <div className="flex-1 overflow-y-auto custom-scrollbar p-6 bg-slate-900 h-full flex flex-col relative">
      <div className="flex items-center justify-between mb-6 shrink-0 z-10">
        <h2 className="font-extrabold text-white text-xl flex items-center gap-3">
          <div className="bg-emerald-500/20 p-2 rounded-lg text-emerald-400"><BookOpen size={20} /></div> 
          {selectedPaper ? 'Paper Inspection' : 'Mined Library'}
        </h2>
        <button onClick={() => { setActivePane('none'); setSelectedPaper(null); }} className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-lg transition-colors"><X size={16} /></button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar relative">
        {selectedPaper ? (
          <div className="animate-in fade-in slide-in-from-right-4 duration-300 pb-8">
            <button onClick={() => setSelectedPaper(null)} className="mb-4 text-xs font-bold uppercase tracking-widest flex items-center gap-2 text-slate-400 hover:text-indigo-400 transition-colors bg-slate-950 px-4 py-2.5 rounded-xl border border-slate-800 hover:border-indigo-500/50 shadow-sm">
              ← Return to Full Library
            </button>
            <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
               <PaperDetail paper={selectedPaper} analysis={currentAnalysis[selectedPaper.id]} />
            </div>
          </div>
        ) : (
          <div className="space-y-3 animate-in fade-in slide-in-from-left-4 duration-300 pb-8">
            {currentPapers.length === 0 ? (
               <div className="text-center p-12 text-slate-500 italic bg-slate-950/50 border border-slate-800/50 rounded-2xl">
                 <BookOpen size={32} className="mx-auto mb-4 text-slate-700" />
                 No papers discovered yet.
               </div>
            ) : currentPapers.map(p => {
              const pid = p.id || p.title?.replace(/ /g, '_').slice(0, 50);
              const isAnalyzed = currentAnalysis[pid] && currentAnalysis[pid].status !== 'failed';
              return (
                <div key={pid} className="flex gap-2 items-stretch">
                  <button
                    onClick={() => setSelectedPaper({ ...p, id: pid })}
                    className="flex-1 text-left p-4 rounded-xl transition-all border block relative overflow-hidden bg-slate-950 border-slate-800/60 hover:border-emerald-500/50 hover:bg-slate-900 hover:shadow-lg hover:shadow-emerald-500/5 group"
                  >
                    {isAnalyzed && <div className="absolute top-0 right-0 w-1.5 h-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]" />}
                    <h4 className="font-bold text-sm leading-snug line-clamp-2 mb-2 text-slate-200 group-hover:text-white transition-colors pr-3">{p.title}</h4>
                    <div className="flex items-center gap-3">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{p.year || 'Unknown'}</span>
                    {isAnalyzed && <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400 flex items-center gap-1.5 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20"><SplitSquareVertical size={10} /> Extracted</span>}
                  </div>
                </button>
                <button
                  onClick={() => handleReanalyzePaper(pid)}
                  disabled={reanalyzingPaperId === pid}
                  title="Re-analyze this paper"
                  className="p-3 rounded-xl bg-slate-950 border border-slate-800/60 hover:border-orange-500/50 hover:bg-orange-500/5 text-slate-400 hover:text-orange-400 transition-all disabled:opacity-50 disabled:cursor-wait shrink-0"
                >
                  {reanalyzingPaperId === pid ? <Loader2 size={18} className="animate-spin" /> : <RotateCcw size={18} />}
                </button>
              </div>
            );
            })}
          </div>
        )}
      </div>
    </div>
  );

  const renderChatPane = () => (
    <div className="flex-1 flex flex-col h-full bg-slate-900 overflow-hidden relative">
      <div className="flex items-center justify-between p-6 shrink-0 border-b border-slate-800/50 bg-slate-900 z-10">
        <h2 className="font-extrabold text-white text-xl flex items-center gap-3">
          <div className="bg-indigo-500/20 p-2 rounded-lg text-indigo-400"><MessageSquare size={20} /></div> 
          Interrogator
        </h2>
        <button onClick={() => setActivePane('none')} className="text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 p-2 rounded-lg transition-colors"><X size={16} /></button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6 relative">
        {chatHistory.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center opacity-70">
            <div className="bg-indigo-500/10 p-5 rounded-full mb-6 border border-indigo-500/20 shadow-inner">
              <MessageSquare size={36} className="text-indigo-400" />
            </div>
            <h3 className="text-slate-200 font-bold mb-3 text-lg">Question the Graph</h3>
            <div className="text-sm text-slate-400 leading-relaxed mb-4 max-w-[280px] space-y-3 bg-slate-950 p-5 rounded-xl border border-slate-800 text-left w-full shadow-sm">
              <p className="italic text-slate-300">"What do the 2023 papers say about X that the 2020 papers don't?"</p>
              <div className="h-px bg-slate-800 w-full" />
              <p className="italic text-slate-300">"Which methodology is most contested?"</p>
            </div>
          </div>
        ) : (
          chatHistory.map((msg, i) => {
            const citedPapers = msg.role === 'assistant' ? extractCitedPapers(msg.content) : [];
            return (
              <div key={i} className="space-y-2">
                <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed shadow-md ${
                    msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-sm' : 
                    msg.role === 'error' ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20' : 
                    'bg-slate-800 text-slate-100 rounded-bl-sm border border-slate-700'
                  }`}>
                    {msg.role === 'assistant' ? (
                      <ReactMarkdown className="prose prose-invert prose-sm max-w-none prose-headings:text-slate-100 prose-headings:font-bold prose-a:text-indigo-400 prose-a:underline prose-code:text-yellow-300 prose-code:bg-slate-900 prose-code:px-1 prose-code:rounded prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 prose-li:text-slate-100 prose-strong:text-slate-50">
                        {msg.content}
                      </ReactMarkdown>
                    ) : (
                      msg.content
                    )}
                  </div>
                </div>
                
                {/* Display cited papers as reference cards */}
                {citedPapers.length > 0 && (
                  <div className="flex justify-start ml-2">
                    <div className="flex gap-2 flex-wrap max-w-[85%]">
                      {citedPapers.map((paper, idx) => (
                        <a
                          key={idx}
                          href={paper.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => {
                            // Also find and highlight the node in the graph if it exists
                            const matchingNode = currentGraphData?.nodes?.find(n => 
                              n.properties?.title?.toLowerCase().includes(paper.title.toLowerCase())
                            );
                            if (matchingNode) {
                              // This could trigger a graph highlight action
                              console.log('Found node:', matchingNode);
                            }
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/30 rounded-lg hover:border-indigo-500/60 hover:bg-indigo-500/20 transition-all group text-xs font-medium text-indigo-300 hover:text-indigo-200 no-underline"
                        >
                          <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full group-hover:scale-125 transition-transform" />
                          {paper.title.length > 40 ? paper.title.slice(0, 40) + '...' : paper.title}
                          <span className="opacity-0 group-hover:opacity-100 transition-opacity text-indigo-400">↗</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}}
        
        {isChatLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 p-4 rounded-2xl rounded-bl-sm border border-slate-700 flex items-center gap-3 shadow-md">
              <Loader2 className="animate-spin text-indigo-400" size={18} />
              <span className="text-xs text-slate-200 font-bold tracking-wide uppercase">Agent Reasoning...</span>
            </div>
          </div>
        )}
      </div>

      <div className="p-5 bg-slate-950 border-t border-slate-800 shrink-0 z-10 shadow-[0_-10px_40px_rgba(0,0,0,0.3)]">
        <form onSubmit={handleSendMessage} className="relative group">
          <input
            value={chatMessage}
            onChange={(e) => setChatMessage(e.target.value)}
            placeholder="Query the agent..."
            className="w-full bg-slate-900 border border-slate-700 focus:border-indigo-500 rounded-xl py-4 flex-1 pl-4 pr-16 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 transition-all shadow-inner"
          />
          <button
            disabled={!chatMessage.trim() || isChatLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white p-2.5 rounded-lg transition-colors shadow-md disabled:shadow-none"
            type="submit"
          >
            <ChevronRight size={20} />
          </button>
        </form>
      </div>
    </div>
  );

  const renderDashboard = () => (
    <div className="flex-1 flex flex-col w-full h-full overflow-hidden bg-slate-950 relative">
      
      {/* Top Session Bar (Moves above graph) */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-slate-900/80 backdrop-blur-md border border-slate-700/50 rounded-2xl flex items-center px-4 py-2.5 z-40 shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
        <button onClick={() => { setStatus('idle'); setPipelineState(null); setSessionId(null); fetchSessions(); }} className="text-slate-400 hover:text-white transition-colors bg-slate-800 p-1.5 rounded-lg border border-slate-700 hover:bg-slate-700 mr-4">
          <span className="font-bold text-lg leading-none">←</span>
        </button>
        <span className="text-[10px] font-bold text-indigo-400 tracking-widest uppercase bg-indigo-500/10 px-2 py-1 rounded shadow-inner mr-3 outline border border-indigo-500/20">Active Mission</span>
        <span className="text-sm font-extrabold text-white truncate max-w-[400px] drop-shadow-md mr-6">{query || 'Dashboard Session'}</span>
        
        {/* Graph Search */}
        <div className="flex items-center bg-slate-950 border border-slate-700 rounded-lg overflow-hidden ml-4 pl-3 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all">
          <Search size={14} className="text-slate-500 shrink-0" />
          <input 
            type="text"
            placeholder="Search graph nodes..."
            value={graphSearchQuery}
            onChange={(e) => setGraphSearchQuery(e.target.value)}
            className="bg-transparent border-none text-xs text-white p-2 w-48 focus:outline-none placeholder-slate-600 focus:ring-0"
          />
          {graphSearchQuery && (
            <button onClick={() => setGraphSearchQuery('')} className="p-2 text-slate-500 hover:text-white">
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Live Progress Banner (Floating above graph) */}
      {status === 'in_progress' && (
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-slate-900/90 backdrop-blur-md border border-indigo-500/40 rounded-2xl px-6 py-4 flex flex-col gap-3 z-40 shadow-[0_10px_40px_rgba(79,70,229,0.3)] w-[600px] max-w-[90vw]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-indigo-500/20 p-2 rounded-full">
                <Loader2 size={18} className="text-indigo-400 animate-spin" />
              </div>
              <span className="text-sm font-bold text-white tracking-wide">Crawling & Reasoning...</span>
            </div>
            <div className="flex items-center gap-5 text-xs text-slate-300 font-bold bg-slate-950/50 px-3 py-1.5 rounded-lg border border-slate-800">
              <span className="flex items-center gap-1.5"><Network size={14} className="text-blue-400"/> Found: <strong className="text-white">{pipelineState?.progress?.papers_found || 0}</strong></span>
              <div className="w-px h-3 bg-slate-700" />
              <span className="flex items-center gap-1.5"><SplitSquareVertical size={14} className="text-emerald-400"/> Mined: <strong className="text-white">{pipelineState?.progress?.analyses_complete || 0}</strong></span>
            </div>
          </div>
          {/* Progress Bar */}
          <div className="w-full bg-slate-950 rounded-full h-2 mt-1 overflow-hidden shadow-inner border border-slate-800">
             <div 
               className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full transition-all duration-500 ease-out relative overflow-hidden" 
               style={{ width: `${Math.min(100, Math.max(5, ((pipelineState?.progress?.analyses_complete || 0) / Math.max(1, pipelineState?.progress?.papers_found || 1)) * 100))}%` }}
             >
                <div className="absolute top-0 left-0 right-0 bottom-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.2)_50%,transparent_75%,transparent_100%)] bg-[length:20px_20px] animate-[shimmer_1s_linear_infinite]" />
             </div>
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden w-full h-full relative">
        
        {/* Left Navigation Icon Rail */}
        <div className="w-20 bg-slate-950/95 backdrop-blur-md border-r border-slate-800/80 flex flex-col items-center py-8 gap-4 z-30 shrink-0 shadow-[10px_0_30px_rgba(0,0,0,0.5)]">
           <NavButton 
              icon={<Network size={22} />} 
              label="Graph" 
              active={activePane === 'none'} 
              onClick={() => setActivePane('none')} 
              bgColor="bg-blue-500"
           />
           <div className="w-8 h-px bg-slate-800 my-2" />
           <NavButton 
              icon={<Lightbulb size={22} />} 
              label="Synthesis" 
              active={activePane === 'synthesis'} 
              onClick={() => setActivePane('synthesis')} 
              bgColor="bg-amber-500"
           />
           <NavButton 
              icon={<BookOpen size={22} />} 
              label="Library" 
              active={activePane === 'library'} 
              onClick={() => { setActivePane('library'); if(activePane === 'library') setSelectedPaper(null); }} 
              bgColor="bg-emerald-500"
              hasPing={currentPapers.length > 0}
           />
           <div className="flex-1" />
           <NavButton 
              icon={<MessageSquare size={22} />} 
              label="Chat" 
              active={activePane === 'chat'} 
              onClick={() => setActivePane('chat')} 
              bgColor="bg-indigo-500"
              hasPing={chatHistory.length > 0}
           />
        </div>

        {/* Expandable Panes */}
        <AnimatePresence mode="wait">
          {activePane !== 'none' && (
            <motion.div
              key="panel"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 450, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: 'spring', damping: 25, stiffness: 220, mass: 0.8 }}
              className="h-full border-r border-slate-800 flex flex-col z-20 shrink-0 overflow-hidden shadow-[20px_0_40px_rgba(0,0,0,0.4)] bg-slate-900 absolute left-20 top-0 bottom-0"
            >
               <div className="w-[450px] h-full">
                 {activePane === 'synthesis' && renderSynthesisPane()}
                 {activePane === 'library' && renderLibraryPane()}
                 {activePane === 'chat' && renderChatPane()}
               </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Large Main Graph Canvas */}
        <div className="flex-1 relative bg-slate-950 w-full h-full">
           {/* Decorative Grid Background */}
           <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none" />
           
           <div className="w-full h-full cursor-move z-10 relative">
             <KnowledgeGraph 
                  data={currentGraphData} 
                  analyses={currentAnalysis}
                  synthesis={currentSynthesis}
                  searchQuery={graphSearchQuery}
                  onNodeClick={(node) => {
                 if (node.type === 'Paper') {
                   setSelectedPaper({ ...node.properties, id: node.id.replace('paper_', '') });
                 }
               }}
             />
           </div>
        </div>

      </div>
    </div>
  );

  return (
    <div className="h-screen w-full flex flex-col bg-slate-950 text-slate-100 selection:bg-indigo-500/30 overflow-hidden font-sans">
      {status === 'idle' ? renderLanding() : renderDashboard()}
    </div>
  );
}

const NavButton = ({ icon, label, active, onClick, bgColor, hasPing }) => (
  <button 
    onClick={onClick}
    className="relative group flex flex-col items-center gap-1.5 focus:outline-none"
  >
    <div className={`
      relative p-3.5 rounded-2xl transition-all duration-300 shadow-md outline outline-2 outline-offset-2
      ${active ? `${bgColor} text-white outline-[${bgColor}]` : 'bg-slate-900 text-slate-400 outline-transparent hover:bg-slate-800 hover:text-white'}
    `}>
       {active && <div className="absolute inset-0 bg-white/20 rounded-2xl" />}
       {icon}
       {hasPing && !active && (
         <span className="absolute top-0 right-0 flex h-3 w-3 -mr-1 -mt-1">
           <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${bgColor}`}></span>
           <span className={`relative inline-flex rounded-full h-3 w-3 ${bgColor}`}></span>
         </span>
       )}
    </div>
    <span className={`text-[9px] font-extrabold uppercase tracking-widest transition-colors ${active ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'}`}>
      {label}
    </span>
  </button>
);

export default App;
