from rdflib.plugins.sparql import prepareQuery


class InvalidSPARQLQuery(ValueError):
    """Raised when generated SPARQL is invalid or not allowed."""


def validate_select_query(generated_query: str) -> str:
    """
    Validate an LLM generated SPARQL query.The BIM information pipeline currently allows only
    syntactically valid SPARQL SELECT queries.
    """

    query = _clean_llm_output(generated_query)
    if not query:
        raise InvalidSPARQLQuery("The generated SPARQL query is empty.")
    try:
        prepared_query = prepareQuery(query)
    except Exception as exc:
        raise InvalidSPARQLQuery(f"Invalid SPARQL syntax: {exc}") from exc
    query_type = getattr(prepared_query.algebra,"name",None,)
    if query_type != "SelectQuery":
        raise InvalidSPARQLQuery("Only SPARQL SELECT queries are allowed.")
    return query


def _clean_llm_output(generated_query: str) -> str:
    """
    Remove an optional Markdown code around the query. The prompt already instructs the LLM not to produce fences;
    this is just an extra normalization.
    """
    query = generated_query.strip()
    if not query.startswith("```"):
        return query
    lines = query.splitlines()
    first_line = lines[0].strip().lower()
    if first_line not in { "```","```sparql",}:
        return query
    lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()