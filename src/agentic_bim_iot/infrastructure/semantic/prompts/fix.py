from langchain_core.prompts import PromptTemplate


GRAPHDB_SPARQL_FIX_PROMPT_TEMPLATE = """
This following SPARQL query is invalid:
{generated_sparql}

The error message is:
{error_message}

Please provide a corrected version of the SPARQL query.
Check for common issues like missing prefixes, incorrect syntax, or undefined variables.
Corrected SPARQL:
"""


GRAPHDB_SPARQL_FIX_PROMPT = PromptTemplate(
    input_variables=[
        "generated_sparql",
        "error_message",
    ],
    template=GRAPHDB_SPARQL_FIX_PROMPT_TEMPLATE,
)