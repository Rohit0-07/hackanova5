"""Neo4j Database implementation for the Research Paper Graph."""

from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase
from loguru import logger

from app.services.crawler.models import AnalyzedPaper, ReferenceDetail
from app.core.config import settings


class Neo4jBackend:
    """Manages connection and operations for Neo4j."""

    def __init__(self):
        uri = settings.neo4j.uri
        user = settings.neo4j.user
        password = settings.neo4j.password
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Initialized Neo4j backend at {uri}")

    async def close(self):
        await self._driver.close()

    async def setup_indexes(self):
        """Create constraints and indexes."""
        query_paper_constraint = """
        CREATE CONSTRAINT paper_id_unique IF NOT EXISTS
        FOR (p:Paper) REQUIRE p.id IS UNIQUE
        """
        async with self._driver.session() as session:
            await session.run(query_paper_constraint)
            logger.info("Neo4j indexes and constraints ensured.")

    # ─────────────────────────────────────────
    # Write Operations
    # ─────────────────────────────────────────

    async def upsert_paper(self, paper: AnalyzedPaper, session_id: str) -> bool:
        """Insert or update a paper node."""
        query = """
        MERGE (p:Paper {id: $id})
        SET p.title = $title,
            p.year = $year,
            p.venue = $venue,
            p.abstract = $abstract,
            p.source = $source,
            p.last_updated = timestamp(),
            p.session_id = $session_id
            
        // If analysis exists, attach it as JSON string or properties
        // For simplicity, we attach key findings as properties
        """
        params = {
            "id": paper.paper_id,
            "title": paper.metadata.title,
            "year": paper.metadata.publication_date.year,
            "venue": paper.metadata.venue,
            "abstract": paper.metadata.abstract,
            "source": paper.source,
            "session_id": session_id,
        }

        # Add analysis properties if available
        if paper.analysis:
            query += """
            , p.research_question = $rq,
              p.methodology = $methodology,
              p.key_findings = $findings,
              p.claims = $claims
            """
            params.update(
                {
                    "rq": paper.analysis.get("research_question", ""),
                    "methodology": paper.analysis.get("methodology", ""),
                    "findings": str(paper.analysis.get("key_findings", [])),
                    "claims": str(paper.analysis.get("claims", [])),
                }
            )

        try:
            async with self._driver.session() as session:
                await session.run(query, params)
                return True
        except Exception as e:
            logger.error(f"Failed to upsert paper {paper.paper_id}: {e}")
            return False

    async def upsert_citation_edge(self, source_id: str, target_id: str):
        """Create a citation edge from source to target.
        Creates a skeleton target node if it doesn't exist."""
        query = """
        MERGE (source:Paper {id: $source_id})
        MERGE (target:Paper {id: $target_id})
        MERGE (source)-[r:CITES]->(target)
        SET r.created_at = coalesce(r.created_at, timestamp())
        """
        try:
            async with self._driver.session() as session:
                await session.run(
                    query, {"source_id": source_id, "target_id": target_id}
                )
        except Exception as e:
            logger.error(
                f"Failed to upsert citation edge {source_id}->{target_id}: {e}"
            )

    async def store_session_graph(self, session_id: str, papers: List[AnalyzedPaper]):
        """Store an entire research session's graph into Neo4j."""
        logger.info(f"Storing session {session_id} to Neo4j ({len(papers)} papers)")
        await self.setup_indexes()

        for paper in papers:
            # 1. Upsert the main paper node
            await self.upsert_paper(paper, session_id)

            # 2. Upsert edges for all its references
            for ref in paper.references:
                ref_id = ref.arxiv_id or ref.doi or ref.paper_id
                if ref_id:
                    await self.upsert_citation_edge(paper.paper_id, ref_id)

    # ─────────────────────────────────────────
    # Read Operations (For Synthesis/Chat)
    # ─────────────────────────────────────────

    async def get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        query = "MATCH (p:Paper {id: $id}) RETURN p"
        async with self._driver.session() as session:
            result = await session.run(query, {"id": paper_id})
            record = await result.single()
            if record:
                return dict(record["p"])
            return None

    async def get_session_papers(self, session_id: str) -> List[Dict[str, Any]]:
        query = "MATCH (p:Paper {session_id: $session_id}) RETURN p"
        papers = []
        async with self._driver.session() as session:
            result = await session.run(query, {"session_id": session_id})
            async for record in result:
                papers.append(dict(record["p"]))
        return papers

    async def get_citation_subgraph(self, session_id: str) -> Dict[str, Any]:
        """Fetch nodes and edges for a session's subgraph."""
        # Nodes
        query_nodes = "MATCH (p:Paper {session_id: $session_id}) RETURN p"
        # Edges where at least the source is in the session
        query_edges = """
        MATCH (s:Paper {session_id: $session_id})-[r:CITES]->(t:Paper)
        RETURN s.id AS source, t.id AS target
        """

        nodes = []
        edges = []

        async with self._driver.session() as session:
            result_nodes = await session.run(query_nodes, {"session_id": session_id})
            async for record in result_nodes:
                nodes.append(dict(record["p"]))

            result_edges = await session.run(query_edges, {"session_id": session_id})
            async for record in result_edges:
                edges.append(
                    {
                        "source": record["source"],
                        "target": record["target"],
                        "relationship": "CITES",
                    }
                )

        return {"nodes": nodes, "edges": edges}


# Global instance
neo4j_db = Neo4jBackend()
