---
trigger: always_on
---

### **Module 5: Database Layer (`db/`)**

**Purpose:** Abstract database operations for flexibility and easy testing.

**Responsibilities:**

- Provide clean interfaces for all DB operations
- Support transactions and batch operations
- Enable easy migration between DB backends

**Key Classes:**

```python
class DatabaseBackend(ABC):
    """Abstract interface for any DB backend"""
    @abstractmethod
    async def add_node(self, node: GraphNode) -> str:
        pass

    @abstractmethod
    async def query_nodes(self, filters: Dict[str, Any]) -> List[GraphNode]:
        pass

    # ... etc for all operations

class Neo4jBackend(DatabaseBackend):
    """Neo4j implementation"""
    pass

class PostgresBackend(DatabaseBackend):
    """PostgreSQL implementation"""
    pass

class DatabaseFactory:
    """Factory for creating appropriate backend"""
    @staticmethod
    def create(backend_type: str) -> DatabaseBackend:
        if backend_type == "neo4j":
            return Neo4jBackend(...)
        elif backend_type == "postgres":
            return PostgresBackend(...)
```

**Configuration:**

```yaml
# config.yaml
database:
  backend: "neo4j" # or "postgres"

neo4j:
  uri: "bolt://localhost:7687"
  user: "neo4j"
  password: "password"

postgres:
  host: "localhost"
  port: 5432
  user: "postgres"
  password: "password"
  database: "research_graph"
```

---
