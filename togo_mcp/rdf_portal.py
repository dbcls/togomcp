import httpx
import os
import yaml
import sys
from typing import Annotated, List, Dict, Any
from pydantic import Field
from .server import *

# @mcp.resource("resource://boilerplate")
# def boilerplate() -> str:
#     return "Hello! I don't know why this is here. But, the server doesn't work without it."

@mcp.tool(name="TogoMCP_Usage_Guide", enabled=True)
def togomcp_usage_guide() -> str:
    """
⚠️ CALL THIS TOOL FIRST before using ANY other TogoMCP tool (SPARQL, search, or database tools). 
This guide enforces the mandatory workflow: 
    (1) Get MIE schema files to discover structured properties, 
    (2) Use search tools for exploratory examples, 
    (3) Inspect properties, 
    (4) Write comprehensive SPARQL queries. 
**CRITICAL**: 95% of query failures happen because users skip step 1 and use text search (bif:contains) 
  or API calls when structured predicates exist in the schema. Skipping this wastes 10-20 tool calls
  and produces incomplete results. 
  For comprehensive queries (counts, 'find all', 'which has most'), this guide shows you how to discover 
  structured properties (taxonomy IRIs, typed predicates, classification terms) that are 10-100x faster 
  than text search. Always call this guide first to learn the correct workflow for your specific query type.
        
    Returns:
        str: The content of the TogoMCP usage guide.
    """
    toolcall_log("togomcp_usage_guide")
    with open(TOGOMCP_USAGE_GUIDE, "r", encoding="utf-8") as file:
        prompt = file.read()
    return prompt

# --- Tools for RDF Portal --- #

@mcp.tool()
async def get_sparql_endpoints() -> Dict[str, Any]:
    """Get the available SPARQL endpoints for RDF Portal.

    Returns:
        Dict with two keys:
        - databases: Dict mapping dbname -> {url, endpoint_name, keyword_search}
        - endpoints: Dict mapping endpoint_name -> {url, databases}
    """
    toolcall_log("get_sparql_endpoints")
    return {
        "databases": SPARQL_ENDPOINT,
        "endpoints": {
            name: {
                "url": ENDPOINT_NAME_TO_URL[name],
                "databases": ENDPOINT_NAME_TO_DATABASES[name]
            }
            for name in ENDPOINT_NAMES
        }
    }

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
        description="Run a SPARQL query on an RDF database. Specify dbname for single-database queries, or endpoint_name/endpoint_url for cross-database queries on shared endpoints."
)
async def run_sparql(
    sparql_query: Annotated[str, Field(description="The SPARQL query to execute")],
    dbname: Annotated[str, Field(description=DBNAME_DESCRIPTION, default="")] = "",
    endpoint_name: Annotated[str, Field(
        description=f"Endpoint name for cross-database queries. One of: {', '.join(ENDPOINT_NAMES)}. "
                    "Use this when querying multiple databases on the same endpoint.",
        default=""
    )] = "",
    endpoint_url: Annotated[str, Field(
        description="Direct SPARQL endpoint URL. Use this for explicit control over the endpoint.",
        default=""
    )] = ""
) -> str:
    """
    Run a SPARQL query on an RDF database.

    Use `get_MIE_file()` to understand the RDF graph structure of each database.

    Args:
        sparql_query (str): The SPARQL query to execute.
        dbname (str, optional): Database name for single-database queries.
        endpoint_name (str, optional): Endpoint name for cross-database queries (e.g., 'ebi' for ChEMBL+ChEBI).
        endpoint_url (str, optional): Direct SPARQL endpoint URL.

    Note:
        Provide at least one of: dbname, endpoint_name, or endpoint_url.
        Priority: endpoint_url > endpoint_name > dbname

    Returns:
        str: CSV-formatted results of the SPARQL query.
    """
    toolcall_log("run_sparql")
    return await execute_sparql(sparql_query, dbname, endpoint_name, endpoint_url)

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
        description="**Use this before constructing any SPARQL queries for the database.** Get the MIE (Metadata Interoperability Exchange) file containing the ShEx schema, RDF and SPARQL examples of a specific RDF database."
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

