from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from langchain_core.runnables import Runnable
from agentic_bim_iot.application.graph.builder import build_agent_graph
from agentic_bim_iot.application.graph.dependencies import GraphDependencies
from agentic_bim_iot.config.settings import Settings,get_settings
from agentic_bim_iot.infrastracture.llm.factory import create_chat_model
from agentic_bim_iot.infrastracture.llm.supervisor import LLMSupervisor
from agentic_bim_iot.infrastracture.semantic.factory import create_bim_query_service



@contextmanager
def create_application(settings: Settings | None = None) -> Iterator[Runnable]:
    """
    Build the application and manage all its components directlty here from the bootsrap.
    """
    resolved_settings = (settings if settings is not None else get_settings())
    with ExitStack() as resources:
        chat_model = create_chat_model(resolved_settings)
        supervisor = LLMSupervisor(chat_model=chat_model)
        bim_query_service = create_bim_query_service(settings=resolved_settings,chat_model=chat_model,resources=resources,)
        dependencies = GraphDependencies(supervisor=supervisor,bim_query_service=bim_query_service,)
        graph = build_agent_graph(dependencies=dependencies)
        yield graph