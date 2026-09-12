CYPHER_SENSOR_EXECUTION_REPAIR_PROMPT_TEXT = """
You are an expert Neo4j Developer repairing a Cypher query used to resolve a building sensor.

The previous Cypher query was syntactically valid and executed successfully, but it returned zero records.
Use the original natural-language request, the Neo4j schema, the previous Cypher query and the execution feedback to generate a corrected Cypher query.

The objective is still to retrieve the GUID of the main MultiSensor associated with the requested room and measurement.
Every Room has a MultiSensor containing subsensors that observe different measurements.
Always return the GUID of the main MultiSensor, not the subsensor.
Use only labels, relationship types and properties available in the provided schema.
Do not invent graph elements.
Always expose the GUID using the alias sensorGuid.
Return only the corrected Cypher query without explanations or markdown.

Schema:
<schema>
{schema}
</schema>

Original request:
<question>
{query_text}
</question>

Previous Cypher:
<previous_cypher>
{previous_cypher}
</previous_cypher>

Execution feedback:
<execution_feedback>
{execution_feedback}
</execution_feedback>

Corrected Cypher:
"""


CYPHER_SENSOR_BULK_EXECUTION_REPAIR_PROMPT_TEXT = """
You are an expert Neo4j Developer repairing a Cypher query used to resolve multiple building sensor measurements for one room.

The previous Cypher query was syntactically valid and executed successfully, but it returned zero records.
The original structured sensor-resolution objective MUST NOT change.

Rules:
- Resolve the requested measurements from the specified room using the provided schema.
- The corrected query MUST return exactly the aliases measurement and sensorGuid.
- measurement must contain the exact canonical requested measurement name.
- sensorGuid must contain the GUID of the main physical sensor associated with that measurement.
- Do not return telemetry values or subsensor GUIDs.
- Do not assume all measurements share the same GUID.
- Do not assume that every requested measurement exists in the dataset.
- Use only labels, relationship types and properties supported by the provided schema.
- Do not invent graph elements.
- Return only the corrected executable Cypher query without explanations or markdown.

Schema:
<schema>
{schema}
</schema>

Structured request:
<request>
{query_text}
</request>

Previous Cypher:
<previous_cypher>
{previous_cypher}
</previous_cypher>

Execution feedback:
<execution_feedback>
{execution_feedback}
</execution_feedback>

Corrected Cypher:
"""