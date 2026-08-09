from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from agentic_bim_iot.application.supervisor.prompt import SUPERVISOR_SYSTEM_PROMPT
from agentic_bim_iot.domain.models import SupervisorDecision


class LLMSupervisor:
    """The LLMSupervisor class rappresent the implementation of the Supervisor contract.
    This component is provider agnostic , any LangChain/LangGraph BaseChatModel that support 
    structured output can be used """
    
    def __init__(self, chat_model: BaseChatModel, system_prompt: str = SUPERVISOR_SYSTEM_PROMPT):
        self._system_prompt = system_prompt
        self.structured_model = chat_model.with_structured_output(SupervisorDecision)
    
    def decide(self, user_query: str) -> SupervisorDecision:
        """The Supervisor interpret the Facility managaer request and produce
        a valid SupervisorDecision object """
        normalized_query = user_query.strip()
        if not normalized_query:
            raise ValueError("User query cannot be empty!")
        
        messages = [SystemMessage(content=self._system_prompt), HumanMessage(content=normalized_query)]
        result = self.structured_model.invoke(messages)
        return SupervisorDecision.model_validate(result)
        