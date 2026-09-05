from langchain_core.prompts import PromptTemplate


GRAPHDB_SENSOR_EXECUTION_REPAIR_TEMPLATE = """
You are an expert GraphDB Developer repairing a SPARQL SELECT query used to resolve a building sensor.

The previous query was syntactically valid and executed successfully, but returned zero rows.
The original objective MUST NOT change.

The objective is:
- identify the sensor associated with the requested room and measurement;
- inspect the subsensors of the sensor located in the room;
- identify the subsensor corresponding to the requested measurement;
- return the GUID of the MAIN MultiSensor;
- do not return the measured telemetry value;
- do not return the GUID of the subsensor.

The corrected query MUST return ?sensorGuid.
Use only classes, properties and relationships supported by the provided schema.
Do not invent ontology terms.
Return only the corrected SPARQL SELECT query without explanations or markdown.

Original request:
<question>
{prompt}
</question>

Schema:
<schema>
{schema}
</schema>

Previous query:
<query>
{generated_sparql}
</query>

Execution feedback:
<feedback>
{execution_feedback}
</feedback>

Corrected SPARQL:
"""


GRAPHDB_SENSOR_BULK_EXECUTION_REPAIR_TEMPLATE = """
You are an expert GraphDB Developer repairing a SPARQL SELECT query used to resolve multiple building sensor measurements for one room.

The previous query was syntactically valid and executed successfully, but returned zero rows.
The original structured sensor-resolution objective MUST NOT change.

Rules:
- Resolve the requested measurements from the specified room using the provided schema.
- The corrected query MUST return exactly ?measurement and ?sensorGuid.
- ?measurement must contain the exact canonical requested measurement name.
- ?sensorGuid must contain the GUID of the main physical sensor associated with that measurement.
- Do not return telemetry values or subsensor GUIDs.
- Do not assume all measurements share the same GUID.
- Do not assume that every requested measurement exists in the dataset.
- Use only classes, properties and relationships supported by the provided schema.
- Do not invent ontology terms.
- Return only the corrected executable SPARQL SELECT query without explanations or markdown.

Structured request:
<request>
{prompt}
</request>

Schema:
<schema>
{schema}
</schema>

Previous query:
<query>
{generated_sparql}
</query>

Execution feedback:
<feedback>
{execution_feedback}
</feedback>

Corrected SPARQL:
"""


GRAPHDB_SENSOR_EXECUTION_REPAIR_PROMPT = PromptTemplate.from_template(GRAPHDB_SENSOR_EXECUTION_REPAIR_TEMPLATE)
GRAPHDB_SENSOR_BULK_EXECUTION_REPAIR_PROMPT = PromptTemplate.from_template(GRAPHDB_SENSOR_BULK_EXECUTION_REPAIR_TEMPLATE)