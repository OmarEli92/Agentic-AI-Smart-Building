from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from rdflib.term import Identifier
from agentic_bim_iot.application.interfaces.semantic import BIMQueryServiceError
from agentic_bim_iot.domain.semantic import SemanticQueryResult
from agentic_bim_iot.infrastructure.observability.tracing import llm_run_config
from agentic_bim_iot.infrastructure.semantic.graphdb.graph_store import GraphStoreError, SPARQLGraphStore, SPARQLResult
from agentic_bim_iot.infrastructure.semantic.graphdb.query_pipeline import GraphDBQueryPipeline
from agentic_bim_iot.infrastructure.semantic.graphdb.query_validation import InvalidSPARQLQuery, validate_select_query
from agentic_bim_iot.infrastructure.semantic.prompts.building import BIM_QA_PROMPT
from agentic_bim_iot.infrastructure.semantic.prompts.fix import GRAPHDB_SPARQL_FIX_PROMPT
from agentic_bim_iot.infrastructure.semantic.prompts.graphdb_building import SPARQL_BUILDING_PROMPT




class GraphDBBIMQueryAdapter:
    """
    The adapter for the BIMQueryService implementation"""

    def __init__(self,chat_model: BaseChatModel,graph_store: SPARQLGraphStore,max_repair_retries: int = 2,) -> None:
        self._graph_store = graph_store
        self._max_repair_retries = max_repair_retries
        output_parser = StrOutputParser()
        self._query_pipeline = GraphDBQueryPipeline(chat_model=chat_model,graph_store=graph_store,generation_prompt=SPARQL_BUILDING_PROMPT,
                                                    max_repair_retries=max_repair_retries,component="bim_text_to_sparql")
        self._generation_chain = (SPARQL_BUILDING_PROMPT| chat_model| output_parser)
        self._repair_chain = (GRAPHDB_SPARQL_FIX_PROMPT| chat_model| output_parser)
        self._answer_chain = (BIM_QA_PROMPT| chat_model| output_parser)

    def answer(self,natural_language_query: str) -> SemanticQueryResult:
        """
        Answer a BIM information request through the
        GraphDB Text to SPARQL pipeline.
        """
        question = natural_language_query.strip()
        if not question:
            raise BIMQueryServiceError("The BIM query cannot be empty.")
        try:
            records = self._query_pipeline.execute(question)
        except (GraphStoreError,InvalidSPARQLQuery) as exc:
            raise BIMQueryServiceError("The GraphDB semantic pipeline could not complete the BIM query.") from exc
        
        context = self._format_result_context(records)
        answer = self._answer_chain.invoke(
            {
                "context": context,
                "prompt": question,
            },   
        config=llm_run_config(
        component="bim_answer",
        operation="answer_generation",
    )
        ).strip()

        if not answer:
            raise BIMQueryServiceError("The semantic subsystem returned an empty answer.")
        return SemanticQueryResult(answer=answer)

    def _validate_with_repair(self,generated_query: str,) -> str:
        """
        Validate generated SPARQL and reuse the existing
        LLM repair prompt when syntax validation fails.
        """
        current_query = generated_query
        for attempt in range(self._max_repair_retries + 1):
            try:
                return validate_select_query(current_query)
            except InvalidSPARQLQuery as exc:
                if attempt >= self._max_repair_retries:
                    raise
                current_query = self._repair_chain.invoke(
                    {
                        "generated_sparql": current_query,
                        "error_message": str(exc),
                    }
                )
        raise InvalidSPARQLQuery("SPARQL validation failed.")

    @staticmethod
    def _format_result_context(records: SPARQLResult,) -> str:
        """
        Convert RDFLib terms into a compact textual representation
        while preserving RDF semantics.
        """

        formatted_records: list[str] = []
        for record in records:
            formatted_values = [
                f"{variable}={GraphDBBIMQueryAdapter._format_term(term)}"
                for variable, term in record.items()
            ]
            formatted_records.append("{"+ ", ".join(formatted_values)+ "}")
        return "\n".join(
            formatted_records
        )

    @staticmethod
    def _format_term(term: Identifier) -> str:
        """
        Use RDFLib's native N3 serialization"""
        return term.n3()