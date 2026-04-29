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


@mcp.tool(
    name="save_MIE_file",
    description="Save the provided MIE content to a file named after the database.",
)
def save_MIE_file(
    database: Annotated[
        str, Field(description=DATABASE_DESCRIPTION, default="")
    ] = "",
    mie_content: Annotated[
        str, Field(description="The content of the MIE file to save.", default="#empty MIE file")
    ] = "#empty MIE file",
    dbname: str = "",
    db: str = "",
) -> str:
    """
    Saves the provided MIE content to a file named after the database.

    Args:
        database (str): The database name. Accepts aliases `dbname` and `db`.
        mie_content (str): The content of the MIE file to save.
        dbname (str, optional): Alias for `database`.
        db (str, optional): Alias for `database`.

    Returns:
        str: A confirmation message indicating the result of the save operation.
    """
    database = database or dbname or db
    if not database:
        return "Error: Missing required argument `database` (aliases: `dbname`, `db`)."
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
