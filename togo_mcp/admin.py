import httpx
import json
import os
import yaml
import sys
from typing import Annotated, List, Dict, Any
from pydantic import Field
from .server import *

@mcp.tool(enabled=True, name="Generate_MIE_file", description="Instructions for generating an MIE (Metadata Interoperability Exchange) file")
def generate_MIE_file(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
) -> str:
    f"""
    Explore a specific RDF database to generate an MIE file for SPARQL queries.

    Args:
        dbname (str): The name of the database to explore. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: The prompt for generating the MIE file for the database.
    """
    with open(MIE_PROMPT, "r", encoding="utf-8") as file:
        mie_prompt = file.read()

    return mie_prompt.replace("__DBNAME__", dbname)

@mcp.tool(enabled=True)
async def get_shex(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
) -> str:
    """
    Get the ShEx schema for a specific RDF database.

    Args:
        dbname(str): The name of the database for which to retrieve the ShEx schema. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: The ShEx schema in ShEx format.
    """
    shex_file = "shex/" + dbname + ".shex"
    if not os.path.exists(shex_file):
        return f"Error: The shex file for '{dbname}' was not found."
    try:
        with open(shex_file, "r", encoding="utf-8") as file:
            content = file.read()
            return content
    except Exception as e:
        return f"Error reading shex file for '{dbname}': {e}"

@mcp.prompt(enabled=True, name="Generate RDF-Config file")
def generate_rdf_config(
        dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
) -> str:
    f"""
    Generate the RDF-Config file for a specific RDF database.

    Args:
        dbname (str): The name of the database for which to generate examples. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: The generated examples in YAML format.
    """
    with open(RDF_CONFIG_TEMPLATE, "r", encoding="utf-8") as file:
        template = file.read()
    return (
    f"Study the RDF Schema of {dbname} by exploring the database."
    "Try to make biologically relevant SPARQL queries to explore the database structure."
    "The results should be saved in YAML format."
    "The YAML file should be based on the following template:"
    "\n\n"
   f"{template}"
    "\n\n"
    "Use `get_sparql_endpoints` to find available SPARQL endpoints."
    "Then, use `get_graph_list` to explore relevant named graphs, classes, and properties in the database."
 
    )

@mcp.tool(enabled=True, name="save_MIE_file", description="Save the provided MIE content to a file named after the database.")
def save_MIE_file(
    dbname: Annotated[str,Field(description=DBNAME_DESCRIPTION)],
    mie_content: Annotated[str,Field(description="The content of the MIE file to save.", default="#empty MIE file")]
    ) -> str:
    """ 
    Saves the provided MIE content to a file named after the database.

    Returns:
        str: A confirmation message indicating the result of the save operation.
    """
    try:
        # Ensure the MIE directory exists
        os.makedirs(MIE_DIR, exist_ok=True)

        file_path = os.path.join(MIE_DIR, f"{dbname}.yaml")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(mie_content)
        return f"Successfully saved MIE file to {file_path}."
    except (IOError, OSError) as e:
        return f"Error: Could not save MIE file for '{dbname}'. Reason: {e}"

@mcp.tool(enabled=True, name="test_MIE_file", description="Testing a MIE file")
def test_MIE_file(
    dbname: Annotated[str,Field(description=DBNAME_DESCRIPTION)]
    ) -> str:
    """ 
    Istructions for testing a MIE file.

    Returns:
        str: a prompt
    """
    return f"""
1. Get the {dbname} MIE file using `get_MIE_file({dbname})`
2. Study the instructions in `generate_MIE_file({dbname})`
3. Test all the examples in the following sections, and fix them if necessary based on the instructions.
  - `rdf_example_entries`
  - `sparql_query_examples`
  - `cross_references`
4. Save the fixed MIE file using `save_MIE_file({dbname})`. Note the following.
  - make sure to use the **Literal Style** (with |) for multiline strings, rather than double-quotes,
  - make it **as concise as possible** while strictly adhering to the instructions in `generate_MIE_file({dbname})`.
"""
