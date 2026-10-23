from langchain_core.tools import tool
from memory.vector_store import vector_memory


@tool
def search_previous_paths(query: str, n_results: int = 3) -> str:
    """Search for previously generated learning paths similar to the user's goal.
    Returns past roadmaps that can be used as reference."""
    results = vector_memory.search_similar_paths(query, n_results)
    if not results:
        return "No similar paths found yet. This is the first generation for this goal."
    formatted = []
    for r in results:
        m = r["metadata"]
        formatted.append(f"Goal: {m.get('goal', 'N/A')}\n{r['content'][:500]}...")
    return "\n\n---\n\n".join(formatted)


@tool
def save_learning_path(goal: str, path_content: str) -> str:
    """Save a generated learning path to memory so it can be referenced later by other users."""
    doc_id = vector_memory.save_path(goal, path_content)
    return f"Path saved with ID: {doc_id}"


@tool
def get_recent_paths(n: int = 5) -> str:
    """Get recently generated learning paths to see what others have been learning."""
    results = vector_memory.get_recent_paths(n)
    if not results:
        return "No paths generated yet."
    formatted = []
    for r in results:
        m = r["metadata"]
        formatted.append(f"- **{m.get('goal', 'N/A')}** ({m.get('created_at', '')})")
    return "\n".join(formatted)
