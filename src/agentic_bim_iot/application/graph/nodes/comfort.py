from agentic_bim_iot.application.graph.state import AgentState
from agentic_bim_iot.application.interfaces.comfort import  ComfortEngine, ComfortEngineError
from agentic_bim_iot.domain.comfort import ComfortAssessment, ParameterComfortAssessment


class ComfortEngineNode:
    """LangGraph node responsible for room comfort assessment."""
    def __init__(self,comfort_engine: ComfortEngine,):
        self._comfort_engine = comfort_engine

    def __call__(self, state: AgentState,) -> dict:
        decision = state["supervisor_decision"]
        room_reference = decision.room_reference
        if not room_reference:
            return {"final_answer": ( "Which room would you like me to analyze?")}
        try:
            assessment = self._comfort_engine.assess(room_reference)
        except ComfortEngineError as exc:
            return {
                "error": str(exc),
                "final_answer": ("I could not evaluate the comfort conditions for the requested room."),
            }

        return {
            "comfort_assessment": assessment,
            "final_answer": self._format_assessment(assessment)
        }

    @staticmethod
    def _format_assessment(assessment: ComfortAssessment) -> str:
        parameter_messages = [
            ComfortEngineNode._format_parameter(parameter)
            for parameter in assessment.parameters.values()
        ]
        warning_text = "."
        if not assessment.data_complete:
            missing = ", ".join(assessment.missing_measurements)
            warning_text = f", but the assessment is based on incomplete data. Missing measurements: {missing}."
        params_text = " ".join(parameter_messages)
        return (
            f"The comfort assessment for {assessment.room_reference} is {assessment.label.value} "
            f"with a score of {assessment.total_score:+d}/3{warning_text} {params_text}"
        )

    @staticmethod
    def _format_parameter(parameter: ParameterComfortAssessment) -> str:
        if parameter.value is None:
            return (f"{parameter.measurement.capitalize()}: unavailable.")
        if parameter.within_range:
            condition = "within the comfort range"
        elif parameter.value < parameter.minimum:
            condition = "below the comfort range"
        else:
            condition = "above the comfort range"
        return (
            f"{parameter.measurement.capitalize()}: "
            f"{parameter.value:g} {parameter.unit} "
            f"({condition}, expected "
            f"{parameter.minimum:g}-"
            f"{parameter.maximum:g} "
            f"{parameter.unit})."
        )