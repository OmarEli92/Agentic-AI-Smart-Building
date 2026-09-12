from langchain_core.prompts import PromptTemplate


GRAPHDB_EXECUTION_REPAIR_TEMPLATE = """
You are an expert GraphDB Developer repairing a SPARQL SELECT query.

The query was generated from a natural-language request.
The query is syntactically valid and was executed successfully,
but it returned zero results.

Use the original request, the provided RDF schema, the generated query,
and the execution feedback to determine whether the query contains a
semantic mismatch.

Correct the query only using classes, properties and relationships
available in the provided schema.

Do not invent ontology terms.
Do not hard-code identifiers that are not supported by the request or schema.
Return only a SPARQL SELECT query.
Do not include explanations or markdown.

Original request:
<question>
{prompt}
</question>

Schema:
<schema>
{schema}
</schema>

Previous SPARQL query:
<query>
{generated_sparql}
</query>

Execution feedback:
<feedback>
{execution_feedback}
</feedback>

Corrected SPARQL Query:
"""


GRAPHDB_EXECUTION_REPAIR_PROMPT = PromptTemplate.from_template(GRAPHDB_EXECUTION_REPAIR_TEMPLATE)