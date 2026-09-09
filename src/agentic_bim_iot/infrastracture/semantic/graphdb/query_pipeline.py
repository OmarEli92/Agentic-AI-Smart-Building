from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import BasePromptTemplate
from agentic_bim_iot.infrastracture.observability.tracing import llm_run_config
from agentic_bim_iot.infrastracture.semantic.graphdb.graph_store import SPARQLGraphStore, SPARQLResult
from agentic_bim_iot.infrastracture.semantic.graphdb.query_validation import InvalidSPARQLQuery, validate_select_query
from agentic_bim_iot.infrastracture.semantic.prompts.fix import GRAPHDB_SPARQL_FIX_PROMPT


class GraphDBQueryPipeline:
    """Common pipeline is used in several places for generation,validation, reparation and execution
    So in simple terms it goes from :
    Natural Language -> SPARQL -> Validation/Repoair -> SPARQLResult
    Currently implemented in the graphdb adapter(used for retrieving bim information), and
    implemented in the SensorResolver to catch the sensor GUID"""

    def __init__(self, *, chat_model: BaseChatModel, graph_store: SPARQLGraphStore, generation_prompt: BasePromptTemplate,
                 execution_repair_prompt: BasePromptTemplate | None = None, max_repair_retries: int = 2,
                 component: str = "graphdb_text_to_sparql"):
        self._graph_store = graph_store
        self._max_repair_retries = max_repair_retries
        self._component = component
        output_parser = StrOutputParser()
        self._generation_chain = generation_prompt | chat_model | output_parser
        self._repair_chain = GRAPHDB_SPARQL_FIX_PROMPT | chat_model | output_parser
        if execution_repair_prompt is not None:
            self._execution_repair_chain = execution_repair_prompt | chat_model | output_parser
        else:
            self._execution_repair_chain = None

    def execute_once(self, question: str) -> SPARQLResult:
        schema = self._graph_store.get_schema()
        generated_query = self._generate_query(schema=schema, question=question)
        print("\n")
        print("=" * 70)
        print("GRAPHDB QUERY PIPELINE")
        print("=" * 70)
        print(f"QUESTION: {question}")
        print("MODE: SINGLE SHOT")
        print("\nGENERATED SPARQL:")
        print(generated_query)
        try:
            validated_query = validate_select_query(generated_query)
        except InvalidSPARQLQuery as exc:
            print("\nSPARQL VALIDATION: FAILED")
            print(f"ERROR: {exc}")
            print("=" * 70)
            print()
            raise
        print("\nSPARQL VALIDATION: OK")
        print("\nVALIDATED SPARQL:")
        print(validated_query)
        records = self._graph_store.execute_select(validated_query)
        print("\nGRAPHDB RESULT:")
        print(records)
        print(f"\nNUMBER OF RECORDS: {len(records)}")
        print("=" * 70)
        print()
        return records

    def execute(self, question: str, *, repair_on_empty: bool = False) -> SPARQLResult:
        """This method is resposible for the execution of the pipeline, i introduced a feedback
        repair mechanism that try to rebuild the generated query in the specifc case related to The telemetry device
        it could happen that the query was semanthically correct but still doesn't give the result like the GUID of the sensor,
        it happens with weak LLM models so in this why it will try to build the query again.
        THIS MECHANISM IS NOT IMPLEMENTED IN THE NORMAL BIM QUERIES, JUST FOR getting the GUID of the sensor"""
        schema = self._graph_store.get_schema()
        generated_query = self._generate_query(schema=schema, question=question)
        print("\n")
        print("=" * 70)
        print("GRAPHDB QUERY PIPELINE")
        print("=" * 70)
        print(f"QUESTION: {question}")
        print(f"REPAIR ON EMPTY: {repair_on_empty}")
        for attempt in range(self._max_repair_retries + 1):
            print("\n")
            print(f"---------- ATTEMPT {attempt + 1} OF {self._max_repair_retries + 1} ----------")
            print("\nGENERATED / CURRENT SPARQL:")
            print(generated_query)
            try:
                validated_query = validate_select_query(generated_query)
            except InvalidSPARQLQuery as exc:
                print("\nSPARQL VALIDATION: FAILED")
                print(f"ERROR: {exc}")
                if attempt >= self._max_repair_retries:
                    print("NO MORE REPAIR ATTEMPTS.")
                    raise
                print("\nREQUESTING SYNTAX REPAIR FROM LLM...")
                generated_query = self._repair_chain.invoke({"generated_sparql": generated_query,"error_message": str(exc)}
                                                            ,config=llm_run_config(component=self._component, operation="syntax_repair", repair_attempt=True,)).strip()
                continue
            print("\nSPARQL VALIDATION: OK")
            print("\nVALIDATED SPARQL:")
            print(validated_query)
            records = self._graph_store.execute_select(validated_query)
            print("\nGRAPHDB RESULT:")
            print(records)
            print(f"\nNUMBER OF RECORDS: {len(records)}")
            if records:
                print("\nQUERY EXECUTION: SUCCESS")
                print("=" * 70)
                print()
                return records
            print("\nQUERY EXECUTION: VALID QUERY BUT ZERO RESULTS")
            if not repair_on_empty or self._execution_repair_chain is None:
                print("EXECUTION REPAIR DISABLED FOR THIS QUERY.")
                print("=" * 70)
                print()
                return records
            if attempt >= self._max_repair_retries:
                print("NO MORE EXECUTION REPAIR ATTEMPTS.")
                print("=" * 70)
                print()
                return records
            generated_query = self._execution_repair_chain.invoke(
                {
                    "schema": schema,
                    "prompt": question,
                    "generated_sparql": validated_query,
                    "execution_feedback": "The SPARQL query was syntactically valid and executed successfully, but returned zero records.",
                },
                config=llm_run_config(component=self._component, operation="execution_repair", repair_attempt=True)
            ).strip()
        return []

    def _generate_query(self, *, schema: str, question: str) -> str:
        query = self._generation_chain.invoke({"schema": schema, "prompt": question},
                                              config=llm_run_config(component=self._component, operation="generation",))
        return query.strip()