"""
Pipeline State Storage Manager
Handles persistence and retrieval of pipeline state and intermediate results.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from app.agents.orchestrator import PipelineState


class PipelineStorageManager:
    """Manages persistent storage of pipeline states and intermediate results."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize storage manager.
        
        Args:
            base_dir: Base directory for storage (default: ./data/pipeline_storage)
        """
        self.base_dir = base_dir or Path("./data/pipeline_storage")
        self.states_dir = self.base_dir / "states"
        self.findings_dir = self.base_dir / "findings"
        self.graphs_dir = self.base_dir / "graphs"
        
        # Create directories
        self.states_dir.mkdir(parents=True, exist_ok=True)
        self.findings_dir.mkdir(parents=True, exist_ok=True)
        self.graphs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized storage manager at {self.base_dir}")
    
    # ==================== State Management ====================
    
    def save_state(self, state: PipelineState) -> Path:
        """Save pipeline state to disk."""
        return state.save_to_file(self.states_dir)
    
    def load_state(self, state_file: Path) -> PipelineState:
        """Load pipeline state from disk."""
        with open(state_file, 'r') as f:
            data = json.load(f)
        
        # logger.debug(f"Loaded state from {state_file}")
        return PipelineState(**data)
    
    def get_state_by_session(self, session_id: str) -> Optional[PipelineState]:
        """Retrieve the latest state for a session."""
        filepath = self.states_dir / f"{session_id}.json"
        if filepath.exists():
            try:
                return self.load_state(filepath)
            except Exception as e:
                logger.error(f"Error loading state {filepath}: {e}")
        
        # Fallback to history if main file is missing or corrupt
        history_files = list((self.states_dir / "history").glob(f"{session_id}_*.json"))
        if history_files:
            latest = max(history_files, key=lambda p: p.stat().st_mtime)
            return self.load_state(latest)
            
        return None
    
    def list_states(self) -> List[Dict[str, Any]]:
        """List all available unique sessions by their latest state."""
        session_map = {}
        
        # Look for all state files
        for state_file in self.states_dir.glob("*.json"):
            if state_file.is_dir():
                continue
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    
                    session_id = data.get("session_id")
                    if not session_id:
                        continue
                    
                    # Track the latest file for each session_id
                    mtime = state_file.stat().st_mtime
                    if session_id not in session_map or mtime > session_map[session_id]['mtime']:
                        # Extract and parse date
                        created_at_str = data.get("created_at")
                        created_at_ts = mtime # fallback
                        if created_at_str:
                            try:
                                # Standard ISO parse
                                dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                created_at_ts = dt.timestamp()
                            except (ValueError, TypeError):
                                pass

                        session_map[session_id] = {
                            "id": session_id,
                            "session_id": session_id,
                            "query": data.get("raw_query") or data.get("query") or "Untitled Research",
                            "status": data.get("status") or "unknown",
                            "papers_count": len(data.get("papers", [])),
                            "analyses_count": len(data.get("analyses", {})),
                            "created_at": created_at_ts,
                            "updated_at": data.get("updated_at") or created_at_str,
                            "mtime": mtime
                        }
            except Exception as e:
                logger.error(f"Failed to load state file {state_file}: {e}")
        
        # Convert map to list and sort by mtime
        states = list(session_map.values())
        states.sort(key=lambda x: x['mtime'], reverse=True)
        
        # Clean up the internal mtime before returning
        for s in states:
            del s['mtime']
            
        return states
    
    # ==================== Findings Management ====================
    
    def save_findings(self, session_id: str, findings: Dict[str, Any]) -> Path:
        """Save extracted findings to disk."""
        timestamp = datetime.utcnow().isoformat().replace(':', '-')
        filename = f"{session_id}_findings_{timestamp}.json"
        filepath = self.findings_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(findings, f, indent=2, default=str)
        
        logger.info(f"Saved findings to {filepath}")
        return filepath
    
    def load_findings(self, findings_file: Path) -> Dict[str, Any]:
        """Load findings from disk."""
        with open(findings_file, 'r') as f:
            return json.load(f)
    
    def export_findings_report(
        self,
        session_id: str,
        format: str = "markdown"
    ) -> str:
        """Export findings as a formatted report."""
        state = self.get_state_by_session(session_id)
        if not state:
            raise ValueError(f"Session not found: {session_id}")
        
        if format == "markdown":
            return self._format_markdown_report(state)
        elif format == "json":
            return json.dumps(state.to_dict(), indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _format_markdown_report(self, state: PipelineState) -> str:
        """Format pipeline state as markdown report."""
        lines = []
        
        lines.append("# Research Analysis Report\n")
        lines.append(f"**Query:** {state.raw_query}\n")
        lines.append(f"**Session:** {state.session_id}\n")
        lines.append(f"**Status:** {state.status}\n")
        lines.append(f"**Generated:** {state.updated_at}\n\n")
        
        # Papers found
        lines.append("## Papers Found\n")
        lines.append(f"Total: {len(state.papers)}\n\n")
        for paper in state.papers:
            lines.append(f"### {paper.get('title', 'Unknown')}\n")
            lines.append(f"- **Authors:** {', '.join(paper.get('authors', []))}\n")
            lines.append(f"- **Year:** {paper.get('year', 'Unknown')}\n")
            lines.append(f"- **URL:** {paper.get('url', 'N/A')}\n\n")
        
        # Key findings
        lines.append("## Key Findings\n\n")
        for paper in state.papers:
            paper_id = paper.get('id') or paper.get('title', '')[:50]
            analysis = state.analyses.get(paper_id, {})
            if analysis:
                lines.append(f"### {paper.get('title', 'Unknown')}\n")
                lines.append(f"**Methodology:** {analysis.get('methodology', 'N/A')}\n\n")
                lines.append("**Key Findings:**\n")
                for finding in analysis.get('key_findings', []):
                    lines.append(f"- {finding}\n")
                lines.append("\n")
        
        # Citation insights
        if state.citation_tree:
            lines.append("## Citation Analysis\n")
            lines.append(f"- **Unique Papers in Citation Tree:** {state.citation_tree.get('total_unique_papers', 0)}\n")
            lines.append(f"- **Depth Levels:** {len(state.citation_tree.get('depth_levels', {}))}\n\n")
        
        # Relationships
        if state.relationships:
            lines.append("## Relationships Identified\n")
            lines.append(f"- **Feature Relationships:** {len(state.relationships.get('feature_relationships', []))}\n")
            lines.append(f"- **Key Connections:** {len(state.relationships.get('key_connections', []))}\n\n")
        
        # Graph info
        if state.graph_nodes:
            lines.append("## Knowledge Graph\n")
            lines.append(f"- **Nodes:** {state.graph_nodes.get('total_nodes', 0)}\n")
            lines.append(f"- **Edges:** {state.graph_nodes.get('total_edges', 0)}\n\n")
        
        # Errors if any
        if state.errors:
            lines.append("## Warnings/Errors\n")
            for error in state.errors:
                lines.append(f"- {error}\n")
        
        return "".join(lines)
    
    # ==================== Graph Management ====================
    
    def save_graph(self, session_id: str, graph_data: Dict[str, Any]) -> Path:
        """Save knowledge graph to disk."""
        timestamp = datetime.utcnow().isoformat().replace(':', '-')
        filename = f"{session_id}_graph_{timestamp}.json"
        filepath = self.graphs_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(graph_data, f, indent=2, default=str)
        
        logger.info(f"Saved graph to {filepath}")
        return filepath
    
    def load_graph(self, graph_file: Path) -> Dict[str, Any]:
        """Load knowledge graph from disk."""
        with open(graph_file, 'r') as f:
            return json.load(f)
    
    # ==================== Utility Methods ====================
    
    def cleanup_old_states(self, days: int = 30):
        """Remove state files older than specified days."""
        import time
        cutoff_time = time.time() - (days * 86400)
        
        removed_count = 0
        for state_file in self.states_dir.glob("*.json"):
            if state_file.stat().st_mtime < cutoff_time:
                state_file.unlink()
                removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old state files")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about storage usage."""
        return {
            "states": len(list(self.states_dir.glob("*.json"))),
            "findings": len(list(self.findings_dir.glob("*.json"))),
            "graphs": len(list(self.graphs_dir.glob("*.json"))),
            "states_dir_size_mb": self._get_dir_size(self.states_dir) / (1024 * 1024),
            "findings_dir_size_mb": self._get_dir_size(self.findings_dir) / (1024 * 1024),
            "graphs_dir_size_mb": self._get_dir_size(self.graphs_dir) / (1024 * 1024),
        }
    
    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """Get total size of directory in bytes."""
        total = 0
        for file in path.rglob("*"):
            if file.is_file():
                total += file.stat().st_size
        return total
