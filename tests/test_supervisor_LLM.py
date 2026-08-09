from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.infrastracture.llm.supervisor import LLMSupervisor
from agentic_bim_iot.infrastracture.llm.factory import create_chat_model

def main() -> None:
    settings = get_settings()
    chat_model = create_chat_model(settings)
    supervisor = LLMSupervisor(chat_model)
    query = "Analyze the comfort in the Kitchen."
    decision = supervisor.decide(query)
    print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    main()