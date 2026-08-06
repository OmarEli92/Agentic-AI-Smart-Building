from enum import StrEnum


class Intent(StrEnum):
    """
    The Intent class represents what the Facility Manager wants
    Whenever the Supervisor LLM receives a request from the Facility
    Managaer it recognises one of the following objectives
    """
    BIM_INFORMATION = "bim_information"
    TELEMETRY_INFORMATION = "telemetry_information"
    COMFORT_ANALYSIS = "comfort_analysis"
    ACTION_RECOMMENDATION = "action_recommendation"
    DIRECT_ACTUATION = "direct_actuation"
    #Related to a proposal
    MODIFY_PROPOSAL = "modify_proposal"
    APPROVE_PROPOSAL = "approve_proposal"
    REJECT_PROPOSAL = "reject_proposal"
    #Related to an action
    EXECUTION_STATUS = "execution_status"
    UNSUPPORTED = "unsupported"


class Route(StrEnum):
    """
    It describes who has to work after the supervisor,
    so it's the next component selected by the supervisor 
    to take care of the request.
    The LLM can comprehend the Facility manager request,
    but it can only select one of the routes, in order to avoid 
    unnecessary hallucinations or confusions.
    """
    BIM_AGENT = "bim_agent"
    TELEMETRY_AGENT = "telemetry_agent"
    COMFORT_ENGINE = "comfort_engine"
    PLANNING_AGENT = "planning_agent"
    COMMAND_STRUCTURING = "command_structuring"
    APPROVAL_HANDLER = "approval_handler"
    EXECUTION_STATUS = "execution_status"
    REQUEST_CLARIFICATION = "request_clarification"
    RESPOND_UNSUPPORTED = "respond_unsupported"
