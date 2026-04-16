from pathlib import Path
from typing import Annotated

from pydantic import Field

from .server import *


@mcp.prompt(
    name="Generate_MIE_file",
    description="Instructions for generating an MIE (Metadata Interoperability Exchange) file",
)
def generate_MIE_file(database: Annotated[str, Field(description=DATABASE_DESCRIPTION)]) -> str:
    f"""
    Explore a specific RDF database to generate an MIE file for SPARQL queries.

    Args:
        database (str): The name of the database to explore. Supported values are {", ".join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: The prompt for generating the MIE file for the database.
    """
    with open(MIE_PROMPT, encoding="utf-8") as file:
        mie_prompt = file.read()

    return mie_prompt.replace("__DBNAME__", database)


@mcp.tool(name="get_shex", description="Get the ShEx schema for a specific RDF database.")
async def get_shex(database: Annotated[str, Field(description=DATABASE_DESCRIPTION)]) -> str:
    """
    Get the ShEx schema for a specific RDF database.

    Args:
        database(str): The name of the database for which to retrieve the ShEx schema. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: The ShEx schema in ShEx format.
    """
    shex_file = Path("shex").joinpath(f"{database}.shex")
    if not shex_file.exists():
        return f"Error: The shex file for '{database}' was not found."
    try:
        with open(shex_file, encoding="utf-8") as file:
            content = file.read()
            return content
    except Exception as e:
        return f"Error reading shex file for '{database}': {e}"


@mcp.tool(
    description="Get an example SPARQL query for a specific RDF database.",
    name="get_sparql_example",
)
def get_sparql_example(
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION, default="")
    ] = "",
    dbname: str = "",
    db: str = "",
) -> str:
    """
    Read the file in SPARQL_EXAMPLES/{database}.rq and return the content.

    Args:
        database (str): The name of the database for which to retrieve the SPARQL example.
            Accepts aliases `dbname` and `db`.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.

    Returns:
        str: The content of the SPARQL example file, or an error message if not found.
    """
    toolcall_log("get_sparql_example")
    database = database or dbname or db
    if not database:
        return (
            "Error: Missing required argument `database` (aliases: `dbname`, `db`)."
        )
    example_file = Path(SPARQL_EXAMPLES).joinpath(f"{database}.rq")
    if not example_file.exists():
        return f"Error: The SPARQL example file for '{database}' was not found at '{example_file}'."
    try:
        with open(example_file, encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return f"Error reading SPARQL example file for '{database}': {e}"


@mcp.tool(
    name="save_MIE_file",
    description="Save the provided MIE content to a file named after the database.",
)
def save_MIE_file(
    database: Annotated[str, Field(description=DATABASE_DESCRIPTION)],
    mie_content: Annotated[
        str, Field(description="The content of the MIE file to save.", default="#empty MIE file")
    ],
) -> str:
    """
    Saves the provided MIE content to a file named after the database.

    Returns:
        str: A confirmation message indicating the result of the save operation.
    """
    try:
        # Ensure the MIE directory exists
        mie_dir = Path(MIE_DIR)
        mie_dir.mkdir(parents=True, exist_ok=True)

        file_path = mie_dir.joinpath(f"{database}.yaml")
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(mie_content)
        return f"Successfully saved MIE file to {file_path}."
    except OSError as e:
        return f"Error: Could not save MIE file for '{database}'. Reason: {e}"
