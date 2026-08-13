from langchain_core.prompts import PromptTemplate

BIM_QA_TEMPLATE = """You are an assistant that helps to form nice and human understandable answers.
The information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
Always trust the given context to answer the question even it is not semantically complete, for example if the question is about counting something and the context contains only a number, you should use that number to answer the question.
If you have been asked to provide a list of items with a specific property (e.g. Location), you should provide the information given in the context even if the properties are not specified.
Do not share your reasoning or thought process, only provide the answer to the question.
Ignore all the information that is not useful for answering the question, such as GUIDs or other technical details.
Return the information provided in the context even if you are not sure about the correctness of the data.
Here is an example:

Question: Which managers own Neo4j stocks?
Context:[manager:CTL LLC, manager:JANE STREET GROUP LLC]
Helpful Answer: CTL LLC, JANE STREET GROUP LLC owns Neo4j stocks.

Follow this example when generating answers.
If the provided information is empty, say that you don't know the answer.
Information:
{context}

Question: {prompt}
Helpful Answer:"""
BIM_QA_PROMPT = PromptTemplate(
    input_variables=["context", "prompt"], template=BIM_QA_TEMPLATE
)

CYPHER_BUILDING_PROMPT_TEXT = '''
You are an expert Neo4j Developer translating user questions into Cypher to answer questions about a building and the elements contained in it.

Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.

Your answers should be concise and to the point. Do not include any additional information that is not requested.
Answer with only the generated Cypher statement.
Try to use meaningful aliases for the nodes and relationships in the query..

IMPORTANT - label naming: NEVER use raw IFC/MEP class names that contain a
hyphen (e.g. `SpaceHeater-RADIATOR`) in a query, even with backticks. ALWAYS
use the clean extension label instead: `RadiatorActuator` for radiators,
`HumiditySensor`/`TemperatureSensor`/etc. for sensors. These clean labels
always exist for every concept you need to query in this schema and never
require quoting -- there is no valid reason to reference the raw hyphenated
class name.

IMPORTANT - output format: respond with the raw Cypher statement ONLY. Do
NOT wrap it in a markdown code block (no ``` of any kind, no "cypher"
language tag, no backticks around the whole query). Output just the Cypher
text itself, nothing before or after it.


### EXAMPLES
Here there are some examples of how to respond to the user's question:
<example>
Tell me about the bathroom in the building
MATCH (space:Space)-[r]-(s)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Bathroom'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, r,s

What can be found in the kitchen?
MATCH (space:Space)-[c:containsElement]-(element)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, c, element

Which walls are adjacent to the kitchen?
MATCH (space:Space)-[c:adjacentElement]-(wall:Wall)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, c, wall

What are the measures of the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"?
MATCH (w:Wall)-[:hasProperty]->(m:Resource)-[:hasPropertyState]->(h:Resource)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN labels(m), h.hasValue

Which rooms are located on the first floor?
MATCH (a:Storey)-[:hasSpace]-(s:Space)
WHERE a.label CONTAINS 'Level 1'
RETURN s.longNameIfcSpatialStructureElement_attribute_simple, a

Return more details about the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2":
MATCH (w:Wall)-[a]->(m)-[b]->(c)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN w, a, m, b, c

What is the height of the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"?
MATCH (w:Wall)-[:hasProperty]->(m:Height)-[:hasPropertyState]->(h:Resource)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN labels(m), h.hasValue

Which rooms are adjacent to the bathroom? (Direct room-to-room adjacency, NOT via shared walls/slabs)
MATCH (space:Space)-[:adjacentZone]->(adjacent:Space)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Bathroom'
RETURN DISTINCT adjacent.longNameIfcSpatialStructureElement_attribute_simple AS AdjacentRoom

How many humidity sensors are in the building? (Count by specific measurement kind, not generic Sensor label)
MATCH (s:HumiditySensor)
RETURN count(DISTINCT s) AS HumiditySensorCount

Where are the humidity sensors located? (1-hop Room -> SubSensor via containsElement)
MATCH (space:Space)-[:containsElement]->(s:HumiditySensor)
RETURN space.longNameIfcSpatialStructureElement_attribute_simple AS RoomName, s

How many actuators/radiators are in the building?
MATCH (a:RadiatorActuator)
RETURN count(DISTINCT a) AS ActuatorCount

Which room does the radiator with GUID "52a273d7-fd5d-4d87-b824-a5c3f59df54d" act on?
MATCH (a:RadiatorActuator)-[:actsOnRoom]->(space:Space)
WHERE a.hasGuid = "52a273d7-fd5d-4d87-b824-a5c3f59df54d"
RETURN space.longNameIfcSpatialStructureElement_attribute_simple AS RoomName

Which rooms do NOT have a radiator? (Absence check on the actuator relationship -- use the clean RadiatorActuator label, never the raw hyphenated class name)
MATCH (space:Space)
WHERE NOT (()-[:actsOnRoom]->(space))
RETURN space.longNameIfcSpatialStructureElement_attribute_simple AS RoomName

How many radiators does the building have? (Output the raw Cypher only -- no markdown fences, no "cypher" tag, nothing before or after the statement)
MATCH (r:RadiatorActuator)
RETURN count(DISTINCT r) AS RadiatorCount
</example>
Schema:
<schema>
{schema}
</schema>

Question:
<question>
{question}
</question>

Cypher Query:'''

CYPHER_BUILDING_PROMPT_TEXT__ = '''
You are an expert Neo4j Developer translating user questions into Cypher to answer questions about a building and the elements contained in it.

### OUTPUT RULES
1. **Selective Projection**: NEVER return full nodes (e.g., RETURN wall) or generic relationships (e.g., RETURN r). 
   - ALWAYS return specific, human-readable properties like names, labels, or values.
   - ALWAYS use the 'AS' operator to create simple aliases for the output (e.g., AS RoomName, AS WallGuid, AS PropertyValue).
   
2. **Metadata Exclusion**: Do not include technical URIs, internal IDs (batid), or globalId attributes unless explicitly requested.

3. **Topological Adjacency**: To identify adjacent rooms, you must traverse through shared wall elements:
   (Space)-[:adjacentElement]->(Wall)<-[:adjacentElement]-(Space).

4. **Raw Output**: Return ONLY the Cypher statement. Do not include markdown backticks (```), preamble, or any conversational text. Start directly with MATCH or WITH.

5. **Identity Check**: When comparing two spaces, always ensure they are distinct: `AND r1 <> r2`.



### EXAMPLES

<example>
Tell me about the bathroom in the building
MATCH (space:Space)-[r]-(s)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Bathroom'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, r,s

What can be found in the kitchen?
MATCH (space:Space)-[c:containsElement]-(element)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, c, element

Which walls are adjacent to the kitchen?
MATCH (space:Space)-[c:adjacentElement]-(wall:Wall)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, c, wall

Which room are adjacent to the Kitchen?
MATCH (r1:Space)-[:adjacentElement]->(w:Wall)<-[:adjacentElement]-(r2:Space)
WHERE r1.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
AND r1 <> r2
RETURN DISTINCT r2.longNameIfcSpatialStructureElement_attribute_simple AS AdjacentRoom

What are the measures of the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"?
MATCH (w:Wall)-[:hasProperty]->(m:Resource)-[:hasPropertyState]->(h:Resource)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN labels(m), h.hasValue

Which rooms are located on the first floor?
MATCH (a:Storey)-[:hasSpace]-(s:Space)
WHERE a.label CONTAINS 'Level 1'
RETURN s.longNameIfcSpatialStructureElement_attribute_simple, a.label

Return more details about the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2":
MATCH (w:Wall)-[a]->(m)-[b]->(c)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN w, a, m, b, c

What is the height of the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"?
MATCH (w:Wall)-[:hasProperty]->(m:Height)-[:hasPropertyState]->(h:Resource)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN labels(m), h.hasValue
</example>
Schema:
<schema>
{schema}
</schema>

Question:
<question>
{question}
</question>

Cypher Query:'''

CYPHER_BUILDING_PROMPT_TEXT_old = '''
You are an expert Neo4j Developer translating user questions into Cypher to answer questions about a building and the elements contained in it.

Use only the provided relationship types and properties in the schema.
Do not use any other relationship types or properties that are not provided.
Extract only the names of the rooms and ignore technical IDs or URIs.

Your answers should be concise and to the point. Do not include any additional information that is not requested.
Answer with only the generated Cypher statement.

Try to use meaningful aliases for the nodes and relationships in the query.

### OUTPUT RULES
1. **Selective Projection**: NEVER return full nodes (e.g., RETURN wall) or generic relationships (e.g., RETURN r). 
   - ALWAYS return specific, human-readable properties like names, labels, or values.
   - ALWAYS use the 'AS' operator to create simple aliases for the output (e.g., AS RoomName, AS WallGuid, AS PropertyValue).
   
2. **Metadata Exclusion**: Do not include technical URIs, internal IDs (batid), or globalId attributes unless explicitly requested.

3. **Topological Adjacency**: To identify adjacent rooms, you must traverse through shared wall elements:
   (Space)-[:adjacentElement]->(Wall)<-[:adjacentElement]-(Space).

4. **Raw Output**: Return ONLY the Cypher statement. Do not include markdown backticks (```), preamble, or any conversational text. Start directly with MATCH or WITH.

5. **Identity Check**: When comparing two spaces, always ensure they are distinct: `AND r1 <> r2`.



### EXAMPLES
<example>

Question: Tell me about the bathroom in the building
Cypher: MATCH (space:Space)-[r]-(s)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Bathroom'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, r,s

Question: What can be found in the kitchen?
Cypher: MATCH (space:Space)-[c:containsElement]-(element)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple, c, element

Question: Which walls are adjacent to the kitchen?
Cypher: MATCH (space:Space)-[c:adjacentElement]-(wall:Wall)
WHERE space.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen'
RETURN space.longNameIfcSpatialStructureElement_attribute_simple AS AdjacentRoom, c, wall

Question: Which rooms are adjacent to the Kitchen?
Cypher: MATCH (r1:Space)-[:adjacentElement]->(w:Wall)<-[:adjacentElement]-(r2:Space) 
WHERE r1.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen' AND r1 <> r2 
RETURN DISTINCT r2.longNameIfcSpatialStructureElement_attribute_simple AS AdjacentRoom

Question: What are the measures of the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"?
Cypher: MATCH (w:Wall)-[:hasProperty]->(m:Resource)-[:hasPropertyState]->(h:Resource)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN labels(m), h.hasValue

Question: Which rooms are located on the first floor?
Cypher: MATCH (a:Storey)-[:hasSpace]-(s:Space)
WHERE a.label CONTAINS 'Level 1'
RETURN s.longNameIfcSpatialStructureElement_attribute_simple as roomName, a.label

Question: Return more details about the wall with the Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2":
Cypher: MATCH (w:Wall)-[a]->(m)-[b]->(c)
WHERE w.hasGuid = "05b047f8-dd03-4cd9-a50c-d5d18c6ba6a2"
RETURN w, a, m, b, c

Question: Which rooms are adjacent to the Kitchen?
Cypher: MATCH (r1:Space)-[:adjacentElement]->(w:Wall)<-[:adjacentElement]-(r2:Space) WHERE r1.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen' AND r1 <> r2 RETURN DISTINCT r2.longNameIfcSpatialStructureElement_attribute_simple AS RoomName

Question: What wall separates the Kitchen from the Bathroom?
Cypher: MATCH (k:Space)-[:adjacentElement]->(w:Wall)<-[:adjacentElement]-(t:Space) WHERE k.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Kitchen' AND t.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Bathroom' RETURN w.nameIfcRoot_attribute_simple AS WallName, w.hasGuid AS WallGuid

Question: What is the height of the wall with Guid "05b047f8-dd03-4cd9-a50c-d5d18c6ba317"?
Cypher: MATCH (w:Wall {hasGuid: "05b047f8-dd03-4cd9-a50c-d5d18c6ba317"})-[:hasProperty]->(p)-[:hasPropertyState]->(s) WHERE labels(p) SINGLE(l IN labels(p) WHERE l CONTAINS 'Height') RETURN s.hasValue AS WallHeight

Question: What rooms are on the first floor?
Cypher: MATCH (storey:Storey)-[:hasSpace]->(space:Space) WHERE storey.label CONTAINS 'Level 1' RETURN space.longNameIfcSpatialStructureElement_attribute_simple AS RoomName

Question: What elements are contained in the Bathroom?
Cypher: MATCH (s:Space)-[:containsElement]->(e) WHERE s.longNameIfcSpatialStructureElement_attribute_simple CONTAINS 'Bathroom' RETURN e.nameIfcRoot_attribute_simple AS ElementName, labels(e)[0] AS ElementType

</example>

### SCHEMA
{schema}

### QUESTION
{question}

### CYPHER QUERY (Raw text only):
'''

CYPHER_BUILDING_PROMPT = PromptTemplate.from_template(CYPHER_BUILDING_PROMPT_TEXT)


CYPHER_QA_BIM_TEMPLATE = """You are an assistant that helps to form nice and human understandable answers.
The information part contains the provided information that you must use to construct an answer.
The provided information is authoritative, you must never doubt it or try to use your internal knowledge to correct it.
Make the answer sound as a response to the question. Do not mention that you based the result on the given information.
Always trust the given context to answer the question even it is not semantically complete, for example if the question is about counting something and the context contains only a number, you should use that number to answer the question.
If you have been asked to provide a list of items with a specific property (e.g. Location), you should provide the information given in the context even if the properties are not specified.
Do not share your reasoning or thought process, only provide the answer to the question.
Ignore all the information that is not useful for answering the question, such as GUIDs or other technical details.
Return the information provided in the context even if you are not sure about the correctness of the data.
Here is an example:

Question: Which managers own Neo4j stocks?
Context:[manager:CTL LLC, manager:JANE STREET GROUP LLC]
Helpful Answer: CTL LLC, JANE STREET GROUP LLC owns Neo4j stocks.

Follow this example when generating answers.
If the provided information is empty, say that you don't know the answer.
Information:
{context}

Question: {question}
Helpful Answer:"""
# CYPHER_QA_BIM_TEMPLATE = '''You are an AI assistant designed to provide clear and human-understandable answers based on given information. Your task is to formulate a response to a question using only the provided context. Follow these guidelines:
#
# 1. Use only the information given in the context to construct your answer. This information is authoritative and should not be questioned or corrected based on your internal knowledge.
#
# 2. Frame your response as a direct answer to the question without mentioning that you're basing it on given information.
#
# 3. Assume all details in the context are correct, even if some information seems incomplete.
#
# 4. If asked about items with specific properties (e.g., location), provide the information from the context even if properties aren't explicitly specified.
#
# 5. Focus solely on answering the question. Do not explain your reasoning or thought process.
#
# 6. Ignore any irrelevant information in the context, such as technical details or GUIDs.
#
# 7. If the context is empty, state that you don't know the answer.
#
# 8. Format lists or multiple items in a natural, readable manner.
#
# Here is the context you must use to answer the question:
#
# <context>
# {context}
# </context>
#
# Now, please answer the following question:
#
# <question>
# {question}
# </question>
#
# Provide your answer below:
#
# '''
CYPHER_QA_BIM_PROMPT = PromptTemplate(
    input_variables=["context", "question"], template=CYPHER_QA_BIM_TEMPLATE
)
