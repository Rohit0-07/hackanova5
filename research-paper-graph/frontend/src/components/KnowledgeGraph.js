import React, { useMemo, useState, useCallback, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { motion, AnimatePresence } from 'framer-motion';
import { BookOpen, ExternalLink, X } from 'lucide-react';

const KnowledgeGraph = ({ data, analyses, synthesis, onNodeClick, searchQuery = '' }) => {
  const [hoverNode, setHoverNode] = useState(null);
  const [hoverLink, setHoverLink] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [actionCard, setActionCard] = useState(null); // { node, x, y }
  
  const fgRef = useRef();

  const graphData = useMemo(() => {
    if (!data || !data.nodes) return { nodes: [], edges: [] };
    
    // Include Papers and CitedPapers for comprehensive view
    const validNodes = data.nodes.filter(node => node.type === 'Paper' || node.type === 'CitedPaper');
    const validNodeIds = new Set(validNodes.map(n => n.id));
    const titleToId = {};

    const nodes = validNodes.map(node => {
      const isPaper = node.type === 'Paper';
      const isCited = node.type === 'CitedPaper';
      const topic = node.properties?.topic || 'General';
      const title = node.properties?.title || node.properties?.name || node.id;
      
      titleToId[title] = node.id;
      
      let color = '#6b7280'; // Default gray-500 for cited papers
      let isAnalyzed = false;

      if (isPaper) {
        const paperId = node.id.replace('paper_', '');
        isAnalyzed = analyses && analyses[paperId] && (analyses[paperId].status === undefined || analyses[paperId].status !== 'failed');
        
        if (isAnalyzed) {
          color = '#10b981'; // Emerald-500 for analyzed
        } else {
          // Vibrant colors for different topics
          const colors = ['#06b6d4', '#3b82f6', '#8b5cf6', '#d946ef', '#ec4899', '#f43f5e', '#f97316', '#d97706', '#16a34a'];
          const topicHash = topic.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
          color = colors[topicHash % colors.length];
        }
      } else if (isCited) {
        // Cited papers get a distinguished violet
        color = '#7c3aed'; // Violet for cited papers
      }

      // Add search filtering calculation
      const isMatch = searchQuery 
        ? (node.properties?.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          node.properties?.topic?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          node.id.toLowerCase().includes(searchQuery.toLowerCase()))
        : true;

      return {
        id: node.id,
        name: title,
        val: isAnalyzed ? 12 : (isPaper ? 8 : 4),
        color: color,
        type: node.type,
        topic: topic,
        isAnalyzed: isAnalyzed,
        properties: node.properties || {},
        isFaded: !isMatch,
      };
    });

    const links = (data.edges || [])
      .filter(edge => validNodeIds.has(edge.source) && validNodeIds.has(edge.target))
      .map(edge => ({
        source: edge.source,
        target: edge.target,
        label: edge.label || edge.relationship || edge.type || 'RELATED',
        type: edge.type || edge.relationship || edge.label || 'RELATED', // Normalized type field
        description: edge.properties?.description || edge.description
      }));

    // Add Semantic Edges from Synthesis (Contradictions)
    if (synthesis && synthesis.contradictions) {
      synthesis.contradictions.forEach(c => {
        const sourceId = titleToId[c.paper_a] || `paper_${c.paper_a}`;
        const targetId = titleToId[c.paper_b] || `paper_${c.paper_b}`;
        
        if (validNodeIds.has(sourceId) && validNodeIds.has(targetId)) {
          links.push({
            source: sourceId,
            target: targetId,
            label: 'CONTRADICTS',
            type: 'CONTRADICTS',
            description: c.description
          });
        }
      });
    }

    return { nodes, links };
  }, [data, analyses, synthesis, searchQuery]);

  useEffect(() => {
    if (fgRef.current) {
      const fg = fgRef.current;
      // Adjust Graph Physics to spread nodes out further
      fg.d3Force('charge').strength(-400).distanceMax(800);
      fg.d3Force('link').distance(edge => edge.label === 'CONTRADICTS' ? 150 : 80);
      fg.d3Force('center', null); // Remove strict centering for more organic spread
      
      // Optional: Re-heat simulation down the line if edges change
      if (fg.d3AlphaDecay) fg.d3AlphaDecay(0.02);
      if (fg.d3VelocityDecay) fg.d3VelocityDecay(0.3);
    }
  }, [graphData]);

  const paintNode = useCallback((node, ctx, globalScale) => {
    const label = node.name.length > 40 ? node.name.slice(0, 40) + '...' : node.name;
    const fontSize = 14 / globalScale < 3 ? 0 : 14 / globalScale;
    const isHovered = hoverNode && hoverNode.id === node.id;
    
    // Determine base color for glow and border
    let baseColor = node.color;
    if (node.isAnalyzed) baseColor = '#10b981'; // Emerald-500
    else if (node.type === 'Paper') baseColor = '#3b82f6'; // Blue-500
    else baseColor = '#8b5cf6'; // Violet-500

    // Pulse / Outer Glow
    if (!node.isFaded && (node.isAnalyzed || isHovered)) {
       ctx.beginPath();
       const glowRadius = isHovered ? node.val + 6 : node.val + 3;
       ctx.arc(node.x, node.y, glowRadius, 0, 2 * Math.PI, false);
       ctx.fillStyle = isHovered ? 'rgba(99, 102, 241, 0.4)' : 'rgba(16, 185, 129, 0.25)';
       ctx.shadowBlur = isHovered ? 15 : 10;
       ctx.shadowColor = isHovered ? '#6366f1' : '#10b981';
       ctx.fill();
       ctx.shadowBlur = 0; // Reset shadow
    }

    // Node Fill (Dark core)
    ctx.beginPath();
    ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.isFaded ? 'rgba(15, 23, 42, 0.4)' : '#0f172a'; // slate-900 background, dimmed if faded
    ctx.fill();

    // Node Border
    ctx.lineWidth = Math.max(1, node.val * 0.2);
    ctx.strokeStyle = node.isFaded ? 'rgba(51, 65, 85, 0.3)' : (isHovered ? '#818cf8' : baseColor); // indigo-400 if hover, dimmed if faded
    ctx.stroke();
    
    // Draw Label Pill (only if not faded out)
    if (!node.isFaded && fontSize > 0) {
      ctx.font = `600 ${Math.max(fontSize, 4)}px 'Inter', sans-serif`;
      const textWidth = ctx.measureText(label).width;
      const paddingX = fontSize * 0.8;
      const paddingY = fontSize * 0.5;
      const bckgDimensions = [textWidth + paddingX * 2, fontSize + paddingY * 2];
      
      const rx = node.x - bckgDimensions[0] / 2;
      const ry = node.y + node.val + 4;
      const radius = bckgDimensions[1] / 2;
      
      // Pill Background
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)'; // slate-900 with opacity
      ctx.beginPath();
      ctx.moveTo(rx + radius, ry);
      ctx.lineTo(rx + bckgDimensions[0] - radius, ry);
      ctx.quadraticCurveTo(rx + bckgDimensions[0], ry, rx + bckgDimensions[0], ry + radius);
      ctx.lineTo(rx + bckgDimensions[0], ry + bckgDimensions[1] - radius);
      ctx.quadraticCurveTo(rx + bckgDimensions[0], ry + bckgDimensions[1], rx + bckgDimensions[0] - radius, ry + bckgDimensions[1]);
      ctx.lineTo(rx + radius, ry + bckgDimensions[1]);
      ctx.quadraticCurveTo(rx, ry + bckgDimensions[1], rx, ry + bckgDimensions[1] - radius);
      ctx.lineTo(rx, ry + radius);
      ctx.quadraticCurveTo(rx, ry, rx + radius, ry);
      ctx.closePath();
      
      // Border for pill
      ctx.strokeStyle = isHovered ? 'rgba(99, 102, 241, 0.8)' : 'rgba(51, 65, 85, 0.6)'; // slate-700
      ctx.lineWidth = 1/globalScale;
      ctx.fill();
      ctx.stroke();
      
      // Text
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = node.isAnalyzed ? '#34d399' : (isHovered ? '#818cf8' : '#f1f5f9'); // emerald-400, indigo-400, slate-100
      ctx.fillText(label, node.x, ry + bckgDimensions[1] / 2 + (fontSize * 0.1)); // slight vertical tweak
    }
  }, [hoverNode]);

  if (!data || !data.nodes || data.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-transparent text-slate-500 italic text-sm">
        No graph data available yet
      </div>
    );
  }

  const handleMouseMove = (e) => {
    setMousePos({ x: e.clientX, y: e.clientY });
  };

  return (
    <div className="h-full w-full relative group" onMouseMove={handleMouseMove}>
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeLabel={() => ''} 
        nodeRelSize={node => node.val}
        
        // Link Rendering
        linkColor={link => {
          const isHoveredLink = hoverNode && (link.source.id === hoverNode.id || link.target.id === hoverNode.id) || (hoverLink && hoverLink === link);
          if (isHoveredLink) return 'rgba(99, 102, 241, 0.95)'; // Indigo-500 (bright)
          if (link.type === 'CONTRADICTS') return 'rgba(244, 63, 94, 0.8)'; // Rose-500 (prominent)
          if (link.source.isFaded || link.target.isFaded) return 'rgba(148, 163, 184, 0.15)'; // Dimmed if connected to faded node
          if (link.type === 'CITES' || link.label === 'CITES') return 'rgba(148, 163, 184, 0.5)'; // slate-400 (visible)
          return 'rgba(99, 102, 241, 0.4)'; // indigo-400 (default)
        }}
        linkWidth={link => {
          const isHoveredLink = hoverNode && (link.source.id === hoverNode.id || link.target.id === hoverNode.id) || (hoverLink && hoverLink === link);
          if (link.type === 'CONTRADICTS') return isHoveredLink ? 4 : 2.5;
          return isHoveredLink ? 2.5 : 1.8;
        }}
        linkLineDash={link => {
          if (link.type === 'CONTRADICTS') return [6, 4];
          if (link.type !== 'CITES') return [3, 3];
          return null;
        }}
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={0.9}
        linkCurvature={0.2}
        
        // Particles (visual indicators of edge relationships)
        linkDirectionalParticles={edge => {
          const isHoveredLink = hoverNode && (edge.source.id === hoverNode.id || edge.target.id === hoverNode.id) || (hoverLink && hoverLink === edge);
          if (edge.type === 'CONTRADICTS') return 4;
          if (isHoveredLink) return 3;
          return edge.type === 'CITES' ? 2 : 1;
        }}
        linkDirectionalParticleSpeed={edge => {
          const isHoveredLink = hoverNode && (edge.source.id === hoverNode.id || edge.target.id === hoverNode.id) || (hoverLink && hoverLink === edge);
          if (edge.type === 'CONTRADICTS') return 0.009;
          return isHoveredLink ? 0.012 : 0.006;
        }}
        linkDirectionalParticleWidth={edge => {
          const isHoveredLink = hoverNode && (edge.source.id === hoverNode.id || edge.target.id === hoverNode.id) || (hoverLink && hoverLink === edge);
          if (edge.type === 'CONTRADICTS') return 3.5;
          return isHoveredLink ? 3 : 2.2;
        }}
        linkDirectionalParticleColor={edge => {
          const isHoveredLink = hoverNode && (edge.source.id === hoverNode.id || edge.target.id === hoverNode.id) || (hoverLink && hoverLink === edge);
          if (isHoveredLink) return '#06b6d4';
          if (edge.type === 'CONTRADICTS') return '#f97316';
          if (edge.type === 'CITES') return '#06b6d4';
          if (edge.type === 'CITED_BY') return '#8b5cf6';
          return '#06b6d4';
        }}
        
        // Link label and tooltip rendering
        linkLabel={edge => edge.type || edge.label || 'relation'}
        
        // Interaction
        onNodeClick={(node, event) => {
          if (node.type === 'Paper') {
            setActionCard({ node, x: event.clientX, y: event.clientY });
          }
        }}
        onBackgroundClick={() => setActionCard(null)}
        onNodeHover={node => setHoverNode(node)}
        onLinkHover={link => setHoverLink(link)}
        
        // Canvas Rendering
        backgroundColor="transparent"
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.val + 4, 0, 2 * Math.PI, false); // Increase hit area slightly
          ctx.fill();
        }}
        
        // Force Engine tweak
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
      
      {/* Premium Hover Card */}
      <AnimatePresence>
        {(hoverNode || hoverLink) && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.1 } }}
            transition={{ type: 'spring', damping: 20, stiffness: 300, mass: 0.5 }}
            style={{ 
              left: Math.min(mousePos.x + 20, window.innerWidth - 340), 
              top: Math.min(mousePos.y + 20, window.innerHeight - 250)
            }}
            className="fixed pointer-events-none z-50 bg-slate-900/90 backdrop-blur-xl border border-slate-700/60 p-5 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.6)] w-80"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 rounded-2xl pointer-events-none" />
            
            {hoverNode && !hoverLink && (
              <>
                <div className="flex items-center gap-2 mb-3 relative z-10">
                  <span className={`text-[9px] font-extrabold uppercase tracking-widest px-2.5 py-1 rounded-md shadow-inner border ${hoverNode.isAnalyzed ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-slate-800 text-slate-400 border-slate-700'}`}>
                    {hoverNode.type}
                  </span>
                  {hoverNode.topic && hoverNode.topic !== 'General' && (
                    <span className="text-[9px] font-extrabold uppercase tracking-widest px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 truncate">
                      {hoverNode.topic}
                    </span>
                  )}
                </div>
                
                <h4 className="font-extrabold text-[15px] text-white leading-snug mb-2 drop-shadow-sm relative z-10">{hoverNode.name}</h4>
                
                {hoverNode.properties?.authors && (
                  <p className="text-xs text-slate-400 mb-3 truncate font-medium relative z-10">
                    {Array.isArray(hoverNode.properties.authors) ? hoverNode.properties.authors.join(', ') : hoverNode.properties.authors}
                  </p>
                )}
                
                {hoverNode.properties?.abstract && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 relative z-10">
                    <p className="text-xs text-slate-300 line-clamp-4 leading-relaxed tracking-wide">
                      {hoverNode.properties.abstract}
                    </p>
                  </div>
                )}
              </>
            )}

            {hoverLink && !hoverNode && (
              <>
                <div className="flex items-center gap-2 mb-3 relative z-10">
                  <span className={`text-[9px] font-extrabold uppercase tracking-widest px-2.5 py-1 rounded-md shadow-inner border ${
                    hoverLink.type === 'CONTRADICTS' ? 'bg-orange-500/20 text-orange-300 border-orange-500/40' :
                    hoverLink.type === 'CITED_BY' ? 'bg-purple-500/20 text-purple-300 border-purple-500/40' :
                    hoverLink.type === 'CITES' ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' :
                    'bg-indigo-500/20 text-indigo-300 border-indigo-500/40'
                  }`}>
                    {hoverLink.type || hoverLink.label}
                  </span>
                </div>
                
                <div className="relative z-10 mb-2">
                  <h4 className="font-bold text-[13px] text-slate-400 leading-snug truncate">
                    {hoverLink.source.name || hoverLink.source.id}
                  </h4>
                  <div className="flex items-center gap-2 py-2">
                    <div className={`w-full h-0.5 ${hoverLink.type === 'CONTRADICTS' ? 'bg-orange-500/50' : 'bg-cyan-500/50'}`} />
                    <span className={`text-[10px] uppercase font-bold tracking-widest whitespace-nowrap ${hoverLink.type === 'CONTRADICTS' ? 'text-orange-400' : hoverLink.type === 'CITED_BY' ? 'text-purple-400' : 'text-cyan-400'}`}>{hoverLink.type || hoverLink.label}</span>
                    <div className={`w-full h-0.5 ${hoverLink.type === 'CONTRADICTS' ? 'bg-orange-500/50' : 'bg-cyan-500/50'}`} />
                  </div>
                  <h4 className="font-bold text-[13px] text-slate-200 leading-snug truncate">
                    {hoverLink.target.name || hoverLink.target.id}
                  </h4>
                </div>

                {hoverLink.description && (
                  <div className="mt-3 pt-3 border-t border-slate-700/60 relative z-10 space-y-2">
                    <p className="text-xs text-slate-300 line-clamp-4 leading-relaxed tracking-wide italic font-medium">
                      "{hoverLink.description}"
                    </p>
                    {hoverLink.properties?.strength && (
                      <div className="text-[10px] text-slate-400 bg-slate-900/40 px-2 py-1 rounded">
                        Strength: <span className="text-cyan-400 font-bold">{hoverLink.properties.strength}</span>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Node Action Card */}
      <AnimatePresence>
        {actionCard && (
          <motion.div
            key="action-card"
            initial={{ opacity: 0, scale: 0.9, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 4 }}
            transition={{ type: 'spring', damping: 22, stiffness: 320, mass: 0.5 }}
            style={{
              left: Math.min(actionCard.x + 12, window.innerWidth - 260),
              top: Math.min(actionCard.y + 12, window.innerHeight - 160),
            }}
            className="fixed z-50 bg-slate-900/95 backdrop-blur-xl border border-slate-700/60 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.7)] p-4 w-56"
          >
            {/* Decorative gradient */}
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 rounded-2xl pointer-events-none" />

            {/* Title */}
            <div className="flex items-start justify-between mb-3 relative z-10">
              <p className="text-[11px] font-bold text-slate-300 leading-snug line-clamp-2 pr-2">
                {actionCard.node.name}
              </p>
              <button
                onClick={() => setActionCard(null)}
                className="shrink-0 text-slate-500 hover:text-white p-0.5 rounded transition-colors"
              >
                <X size={13} />
              </button>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2 relative z-10">
              <button
                onClick={() => {
                  setActionCard(null);
                  if (onNodeClick) onNodeClick(actionCard.node);
                }}
                className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 hover:border-emerald-400/40 text-emerald-300 hover:text-emerald-200 text-xs font-bold transition-all group"
              >
                <BookOpen size={13} className="shrink-0 group-hover:scale-110 transition-transform" />
                Open in Library
              </button>
              {actionCard.node.properties?.url ? (
                <a
                  href={actionCard.node.properties.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => setActionCard(null)}
                  className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 hover:border-indigo-400/40 text-indigo-300 hover:text-indigo-200 text-xs font-bold transition-all no-underline group"
                >
                  <ExternalLink size={13} className="shrink-0 group-hover:scale-110 transition-transform" />
                  View Source ↗
                </a>
              ) : (
                <div className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-slate-800/50 border border-slate-700/30 text-slate-600 text-xs font-bold cursor-not-allowed">
                  <ExternalLink size={13} className="shrink-0" />
                  No Source URL
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Edge Legend - Bottom Right Corner */}
      <div className="absolute bottom-6 right-6 bg-slate-950/80 backdrop-blur-md border border-slate-700/60 rounded-xl p-4 z-10 shadow-[0_10px_30px_rgba(0,0,0,0.4)]">
        <h3 className="text-xs font-extrabold text-slate-300 uppercase tracking-widest mb-3 flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-indigo-400" /> Relationships
        </h3>
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-6 h-0.5 bg-indigo-400" />
            <span className="text-slate-400">Citations</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-6 h-0.5 bg-rose-500 rounded" style={{backgroundImage: 'repeating-linear-gradient(90deg, #f43f5e 0px, #f43f5e 4px, transparent 4px, transparent 8px)'}} />
            <span className="text-slate-400">Contradicts</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mt-3 pt-2 border-t border-slate-700">
            <div className="w-2 h-2 bg-emerald-500 rounded-full" />
            <span className="text-slate-400">Analyzed</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <div className="w-2 h-2 bg-blue-500 rounded-full" />
            <span className="text-slate-400">Pending</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(KnowledgeGraph);
