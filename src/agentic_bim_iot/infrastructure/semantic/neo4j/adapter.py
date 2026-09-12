from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from agentic_bim_iot.infrastructure.semantic.prompts.building import BIM_QA_PROMPT
from agentic_bim_iot.infrastructure.semantic.prompts.neo4j_building import CYPHER_BUILDING_PROMPT_TEXT
from neo4j_graphrag.exceptions import Neo4jGraphRagError
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.schema import get_schema
from agentic_bim_iot.application.interfaces.semantic import BIMQueryServiceError
from agentic_bim_iot.domain.semantic import SemanticQueryResult


class Neo4jBIMQueryAdapter:
    """
    BIMQueryService implementation  ofr Neo4J storage."""

    def __init__(self,chat_model: BaseChatModel,driver: Driver,database: str = "neo4j",) -> None:
        self._database = database
        try:
            schema = get_schema(driver=driver,database=database,)
            self._retriever = Text2CypherRetriever(
                driver=driver,
                llm=chat_model,
                neo4j_schema=schema,
                custom_prompt=CYPHER_BUILDING_PROMPT_TEXT,
                neo4j_database=database,
            )
        except (Neo4jGraphRagError,Neo4jError,DriverError,) as exc:
            raise BIMQueryServiceError("Could not initialize the Neo4j BIM semantic backend.") from exc
        self._answer_chain = (BIM_QA_PROMPT| chat_model| StrOutputParser())

    def answer(self,natural_language_query: str) -> SemanticQueryResult:
        question = natural_language_query.strip()
        if not question:
            raise BIMQueryServiceError("The BIM query cannot be empty.")
        try:
            retrieval_result = self._retriever.search(query_text=question)
            context = "\n".join(str(item.content) for item in retrieval_result.items)
            answer = self._answer_chain.invoke(
                {
                    "context": context,
                    "prompt": question,
                }
            ).strip()

        except (Neo4jGraphRagError,Neo4jError,DriverError) as exc:
            raise BIMQueryServiceError("The Neo4j semantic pipeline could not complete the BIM query.") from exc

        if not answer:
            raise BIMQueryServiceError("The Neo4j semantic pipeline returned an empty answer.")

        return SemanticQueryResult(answer=answer)