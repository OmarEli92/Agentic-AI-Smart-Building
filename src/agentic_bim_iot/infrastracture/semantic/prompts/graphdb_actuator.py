from langchain_core.prompts import PromptTemplate


SPARQL_ACTUATOR_PROMPT_TEXT = """
You are an expert GraphDB Developer translating a structured actuator-resolution request into one SPARQL SELECT query.

The request contains one room reference and one or more canonical controlled measurements.

Your output must ONLY be the generated SPARQL statement.
Do not include markdown, backticks, explanations, comments, or conversational text.
Start directly with PREFIX or SELECT.

The objective is to find the physical actuators that can control the requested measurements in the requested room.

The query MUST return exactly these variables:
?measurement
?actuatorGuid
?actuatorType

?measurement must contain the exact canonical measurement name provided in the request.
?actuatorGuid must contain the GUID of the physical actuator.
?actuatorType must contain an actuator ontology class that identifies the actuator capability.

Use the ontology schema to resolve the actuator.
The ontology represents the relation between an actuator and a room through bop:actsOnRoom.
The ontology represents the controlled quantity through bop:actsOn.
The resource linked through bop:actsOn is classified with rdf:type according to the controlled quantity kind.
The actuator GUID is available through bot:hasGuid.
Specific actuator classes can be subclasses of bop:Actuator.

Resolve each requested measurement independently.
Do not assume that every requested measurement has an actuator.
Do not invent actuators when the graph does not contain one.
Do not assume that one actuator controls every measurement.
Do not hardcode room instances, actuator instances, or GUIDs.
Use only classes, properties, and relationships supported by the provided schema.

Example request:
Room reference: Living
Requested measurements: temperature

Example query:
PREFIX bop: <https://w3id.org/bop#>
PREFIX bot: <https://w3id.org/bot#>
PREFIX props: <https://w3id.org/props#>
PREFIX qudt: <http://qudt.org/vocab/quantitykind/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?measurement ?actuatorGuid ?actuatorType
WHERE {{
  ?room props:longNameIfcSpatialStructureElement_attribute_simple ?roomName .
  FILTER(CONTAINS(LCASE(STR(?roomName)), "living")) .
  ?actuator bop:actsOnRoom ?room .
  ?actuator bop:actsOn ?quantity .
  ?actuator bot:hasGuid ?actuatorGuid .
  ?actuator a ?actuatorType .
  ?actuatorType rdfs:subClassOf* bop:Actuator .
  FILTER(?actuatorType != bop:Actuator) .
  ?quantity a qudt:Temperature .
  BIND("temperature" AS ?measurement)
}}

Schema:
<schema>
{schema}
</schema>

Structured actuator-resolution request:
<request>
{prompt}
</request>

SPARQL Query:
"""

SPARQL_ACTUATOR_PROMPT = PromptTemplate(
    input_variables=["schema", "prompt"],
    template=SPARQL_ACTUATOR_PROMPT_TEXT,
)