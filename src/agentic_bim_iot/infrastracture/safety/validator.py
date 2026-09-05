from agentic_bim_iot.application.interfaces.safety import SafetyPolicyValidator
from agentic_bim_iot.domain.command import ActuationCommand, ActuationOperation, CommandAuthorizationSource
from agentic_bim_iot.domain.comfort import COMFORT_RANGES, MEASUREMENT_UNITS
from agentic_bim_iot.domain.safety import SafetyValidationResult, SafetyValidationStatus


class BuildingSafetyPolicyValidator(SafetyPolicyValidator):
    """This class represents the Sagety Policy validator which verify if designated commands can be
    executed or they are incorrect and therefore refuted/blocked"""
    
    def validate(self, commands: tuple[ActuationCommand, ...]) -> SafetyValidationResult:
        if not commands:
            return SafetyValidationResult(status=SafetyValidationStatus.BLOCKED, commands=commands, violations=("No actuation command was provided.",),
                message="The command was blocked because there is nothing to execute.",
            )
        violations: list[str] = []
        seen_targets: set[tuple[str, str]] = set()
        for command in commands:
            measurement = command.measurement.casefold()
            command_key = (command.room_reference.casefold(), measurement)
            if command_key in seen_targets:
                violations.append(f"Multiple commands target '{measurement}' in room '{command.room_reference}'.")
            seen_targets.add(command_key)
            if command.operation != ActuationOperation.SET_VALUE:
                violations.append(f"Operation '{command.operation.value}' is not supported.")
            if measurement not in COMFORT_RANGES:
                violations.append(f"Measurement '{measurement}' has no configured operating range.")
                continue
            expected_unit = MEASUREMENT_UNITS[measurement]
            if command.unit != expected_unit:
                violations.append(f"Measurement '{measurement}' requires unit '{expected_unit}', but command '{command.command_id}' uses '{command.unit}'.")
            minimum, maximum = COMFORT_RANGES[measurement]
            if not minimum <= command.target_value <= maximum:
                violations.append(f"Target {command.target_value:g} {command.unit} for '{measurement}' is outside the configured operating range {minimum:g}-{maximum:g} {expected_unit}.")
            if command.authorization_source == CommandAuthorizationSource.APPROVED_PROPOSAL and not command.proposal_id:
                violations.append(f"Command '{command.command_id}' claims proposal authorization but has no proposal ID.")
            if command.authorization_source == CommandAuthorizationSource.EXPLICIT_USER_REQUEST and command.proposal_id is not None:
                violations.append(f"Direct command '{command.command_id}' must not reference a proposal authorization.")

        if violations:
            return SafetyValidationResult(
                status=SafetyValidationStatus.BLOCKED,
                commands=commands,
                violations=tuple(violations),
                message="The actuation command was blocked by the safety policy validation.",
            )
        return SafetyValidationResult(status=SafetyValidationStatus.ALLOWED, commands=commands, violations=(), message=f"{len(commands)} actuation command(s) passed deterministic safety and policy validation and are ready for execution.",)