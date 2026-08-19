from langchain_core.prompts import PromptTemplate


GRAPHDB_SENSOR_EXECUTION_REPAIR_TEMPLATE = """
You are an expert GraphDB Developer repairing a SPARQL SELECT query
used to resolve a building sensor.

The previous query was syntactically valid and executed successfully,
but returned zero rows.

The original objective MUST NOT change.

The objective is:
- identify the sensor associated with the requested room and measurement;
- inspect the subsensors of the sensor located in the room;
- identify the subsensor corresponding to the requested measurement;
- return the GUID of the MAIN MultiSensor;
- do not return the measured telemetry value;
- do not return the GUID of the subsensor.

The corrected query MUST return:

?sensorGuid

Do not change the task into retrieving temperature,
humidity, brightness or another measured value.

Use only classes, properties and relationships supported
by the provided schema.

Do not invent ontology terms.

Return only the corrected SPARQL SELECT query.
Do not include explanations or markdown.

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


GRAPHDB_SENSOR_EXECUTION_REPAIR_PROMPT = (
    PromptTemplate.from_template(
        GRAPHDB_SENSOR_EXECUTION_REPAIR_TEMPLATE
    )
)