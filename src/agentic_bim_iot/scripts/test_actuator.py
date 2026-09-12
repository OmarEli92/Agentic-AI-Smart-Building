from contextlib import ExitStack

from agentic_bim_iot.config.settings import get_settings
from agentic_bim_iot.infrastructure.llm.factory import create_chat_model
from agentic_bim_iot.infrastructure.semantic.factory import create_semantic_services


def main() -> None:
    settings = get_settings()

    semantic_model = create_chat_model(
        settings,
        reasoning_effort="none",
    )

    with ExitStack() as resources:
        semantic_services = create_semantic_services(
            settings=settings,
            chat_model=semantic_model,
            resources=resources,
        )

        actuator_resolver = semantic_services.actuator_resolver

        if actuator_resolver is None:
            raise RuntimeError(
                "Actuator resolver is not available for the selected semantic backend."
            )

        actuator = actuator_resolver.resolve(
            room_reference="Living",
            measurement="temperature",
        )

        print()
        print("=" * 70)
        print("ACTUATOR RESOLUTION RESULT")
        print("=" * 70)
        print(actuator)
        print("=" * 70)


if __name__ == "__main__":
    main()