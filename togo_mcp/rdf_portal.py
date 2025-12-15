import httpx
import os
import yaml
import sys
from typing import Annotated, List, Dict, Any, Literal
from pydantic import Field
from .server import *

@mcp.resource("resource://boilerplate")
def boilerplate() -> str:
    return "Hello! I don't know why this is here. But, the server doesn't work without it."

@mcp.tool(name="RDF_Portal_Guide",
            description="A general guideline for using the RDF Portal.")
def rdf_portal_guide() -> str:
    """
    A general guideline for using the RDF Portal.
    Always use this before constructing any SPARQL queries for the database,
    and strictly follow the instructions provided there.

    Returns:
        str: The content of the RDF Portal Guide.
    """
    toolcall_log("rdf_portal_guide")
    with open(RDF_PORTAL_GUIDE, "r", encoding="utf-8") as file:
        prompt = file.read()
    return prompt

# --- Tools for RDF Portal --- #

@mcp.tool()
async def get_sparql_endpoints() -> Dict[str,str]:
    """ Get the available SPARQL endpoints for RDF Portal. 
    Returns:
        Dict[str,str]: Dictionary of dbname-URL pairs.
    """
    toolcall_log("get_sparql_endpoints")
    return SPARQL_ENDPOINT

@mcp.tool(enabled=False)
async def get_void(
    graph_uri: Annotated[str,Field(description="Graph URI to explore. Use `get_graph_list` to get appropriate graph URI.")]
) -> list:
    """ Get VoID data for the given graph URI.
    Args:
        graph_uri (str): Graph URI to explore. Use `get_graph_list` to get appropriate graph URI.
    Returns:
        str: A JSON-formatted string containing the VoID data.
    """
    toolcall_log("get_void")
    query=f"""
PREFIX void: <http://rdfs.org/ns/void#>
PREFIX sd: <http://www.w3.org/ns/sparql-service-description#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?total_count ?class_count ?property_count ?class_name ?class_triple_count ?property_name ?property_triple_count
WHERE {{
  VALUES ?gname {{ <{graph_uri}> }}
  [
    a sd:Service ;
    sd:defaultDataset [
       a sd:Dataset ;
       sd:namedGraph [
         sd:name ?gname ;
         a sd:NamedGraph ;
         sd:endpoint ?ep_url ;
         sd:graph [
           a void:Dataset ;
           void:triples ?total_count ;
           void:classes ?class_count ;
           void:properties ?property_count ;
           void:distinctObjects ?uniq_object_count ;
           void:distinctSubjects ?uniq_subject_count ;
           void:classPartition [
             void:class ?class_name ;
             void:entities ?class_triple_count
           ] ;
           void:propertyPartition [
             void:property ?property_name ;
             void:triples ?property_triple_count
           ]
         ]
       ]
     ]
  ] .
}}
"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://plod.dbcls.jp/repositories/RDFPortal_VoID2",
            data={"query": query},
            headers={"Accept": "application/sparql-results+json"}
        )
    response.raise_for_status()
    bindings = response.json()["results"]["bindings"]
    if not bindings:
        return []
    results = [{key: binding[key]["value"] for key in binding} for binding in bindings]
    return results

@mcp.tool(
        enabled=True,
        name="run_sparql",
        description="Run a SPARQL query on a specific RDF database."
)
async def run_sparql(
    sparql_query: Annotated[str, Field(description="The SPARQL query to execute")],
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
) -> str:
    """
    Run a SPARQL query on a specific RDF database. Use `get_MIE_file()` to understand the RDF graph structure of the database.

    Args:
        sparql_query (str): The SPARQL query to execute.
        dbname (str): The name of the database to query. Supported values are {', '.join(SPARQL_ENDPOINT_KEYS)}.

    Returns:
        str: CSV-formatted results of the SPARQL query.
    """
    toolcall_log("run_sparql")
    return await execute_sparql(sparql_query, dbname)

# --- Tools for exploring RDF databases ---
@mcp.tool(
        enabled=False,
        name="get_class_list",
        description="Get a list of classes in the RDF database that match the given URI."
)
async def get_class_list(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)],
    uri: Annotated[str, Field(description="The URI to match classes. `http://...`")]
) -> str:
    f"""
    Get a list of classes in the RDF database that match the given URI.

    Args:
        dbname (str): The name of the database to query. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.
        uri (str): The URI to match classes.

    Returns:
        list: The list of classes.
    """
    toolcall_log("get_class_list")
    sparql_query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT DISTINCT ?class
    WHERE {{
        ?class a owl:Class .
        FILTER STRSTARTS(STR(?class), "{uri}")
    }} LIMIT 100
    """
    return await execute_sparql(sparql_query, dbname)

@mcp.tool(
        enabled=False,
        name="get_property_list",
        description="Get a list of properties in the RDF database that match the given URI."
)
async def get_property_list(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)],
    uri: Annotated[str, Field(description="The URI to match properties. `http://...`")]
) -> str:
    f"""
    Get a list of properties in the RDF database that match the given URI.

    Args:
        dbname (str): The name of the database to query. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.
        uri (str): The URI to match properties.

    Returns:
        list: The list of properties.
    """
    toolcall_log("get_property_list")
    sparql_query = f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT DISTINCT ?property 
    WHERE {{
        ?property a ?proptype .
        ?proptype rdfs:subClassOf rdf:Property .
        FILTER STRSTARTS(STR(?property), "{uri}")
    }} LIMIT 100
    """
    return await execute_sparql(sparql_query, dbname)

@mcp.tool(
        enabled=True,
        name="get_graph_list",
        description="Get a list of named graphs in a specific RDF database."
)
async def get_graph_list(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
    ) -> str:
    f"""
    Get a list of named graphs in a specific RDF database.

    Args:
        dbname (str): The name of the database for which to retrieve the named graphs. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}.

    Returns:
        str: CSV-formatted list of named graphs.
    """
    toolcall_log("get_graph_list")
    sparql_query = '''
SELECT DISTINCT ?graph WHERE {
  GRAPH ?graph {
    ?s ?p ?o .
  }
}'''
    return await execute_sparql(sparql_query, dbname)

@mcp.tool(
        enabled=True,
        name="get_MIE_file",
        description="Get the MIE file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database. Use this before constructing any SPARQL queries for the database."
)
async def get_MIE_file(
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION)]
    ) -> str:
    f"""
    Get the MIE file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database in YAML format, which can be used as a hint to build SPARQL queries.

    Args:
        dbname (str): The name of the database for which to retrieve the shape expression. Supported values are {', '.join(SPARQL_ENDPOINT.keys())}."

    Returns:
        str: The MIE file containing the RDF schema information in YAML format.
    """
    toolcall_log("get_MIE_file")
    mie_file = MIE_DIR + "/" + dbname + ".yaml"
    drop_keys = [] 
#    drop_keys += ["data_statistics", "architectural_notes"]
#    drop_keys += ["validation_notes"]
    if not os.path.exists(mie_file):
        return f"Error: The MIE file for '{dbname}' was not found."
    try:
        with open(mie_file, "r", encoding="utf-8") as file:
            content = yaml.safe_load(file)
            content2 = {}
            if isinstance(content, dict):
                for key, value in content.items():
                    if key not in drop_keys:
                        content2[key] = value
                yaml_dump = yaml.dump(content2, sort_keys=False)
            else:
                # If not a dictionary, just dump the original content
                yaml_dump = yaml.dump(content, sort_keys=False)
            
            response_text = f"""Content-type: application/yaml; charset=utf-8
{yaml_dump}"""
            return response_text
    except Exception as e:
        return f"Error reading MIE file for '{dbname}': {e}"

@mcp.tool(
    enabled=True, 
    name="list_databases",
    description="List available databases and their descriptions."
)
def list_databases() -> List[Dict[str, Any]]:
    """
    Reads all YAML files in a given directory and extracts the title and
    description from the 'schema_info' section.

    Returns:
        A list of dictionaries, each containing schema info for a file.
    """
    toolcall_log("list_databases")
    resources_dir = MIE_DIR
    if not os.path.isdir(resources_dir):
        print(f"Error: Directory '{resources_dir}' not found.", file=sys.stderr)
        return []

    all_schemas_info = []
    for db_name in sorted(SPARQL_ENDPOINT.keys()):
        filename = db_name + ".yaml"
        file_path = os.path.join(resources_dir, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise yaml.YAMLError("YAML file is not a dictionary.")
            
            schema_info = data.get("schema_info")
            if not isinstance(schema_info, dict):
                raise yaml.YAMLError("'schema_info' section not found or not a dictionary.")

            title = schema_info.get("title")
            description = schema_info.get("description")

            all_schemas_info.append({
                "database": db_name,
                "title": title or "No title found.",
                "description": description or "No description found.",
            })

        except yaml.YAMLError as e:
            all_schemas_info.append(
                {
                    "database": db_name,
                    "title": "No title found.",
                    "description": f"Error processing YAML file: {e}",
                })
        except (IOError, OSError) as e:
            all_schemas_info.append(
                {
                    "database": db_name,
                    "title": "No title found.",
                    "description": f"Error reading file: {e}",
                })
    return all_schemas_info

@mcp.tool(
        enabled=True,
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
