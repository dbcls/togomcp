import os
from typing import Annotated
from pydantic import Field
from .server import *

@mcp.prompt(name="Generate_MIE_file", description="Instructions for generating an MIE (Metadata Interoperability Exchange) file")
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

@mcp.tool(name="get_shex", description="Get the ShEx schema for a specific RDF database.")
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

@mcp.tool(
        description="Get an example SPARQL query for a specific RDF database.",
        name="get_sparql_example"
)
def get_sparql_example(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
) -> str:
    """
    Read the file in SPARQL_EXAMPLES/{dbname}.rq and return the content.

    Args:
        dbname (str): The name of the database for which to retrieve the SPARQL example.

    Returns:
        str: The content of the SPARQL example file, or an error message if not found.
    """
    toolcall_log("get_sparql_example")
    example_file = os.path.join(SPARQL_EXAMPLES, f"{dbname}.rq")
    if not os.path.exists(example_file):
        return f"Error: The SPARQL example file for '{dbname}' was not found at '{example_file}'."
    try:
        with open(example_file, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading SPARQL example file for '{dbname}': {e}"

@mcp.tool(name="save_MIE_file", description="Save the provided MIE content to a file named after the database.")
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
