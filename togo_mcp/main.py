from .server import *
from .rdf_portal import *
from .api_tools import *
from .togoid import togoid_mcp
from .ncbi_tools import ncbi_mcp
import asyncio

async def setup():
    await mcp.import_server(togoid_mcp, prefix="togoid")
    await mcp.import_server(ncbi_mcp, prefix="ncbi")

def run():
    asyncio.run(setup())
    mcp.run(transport="http", host="0.0.0.0", port=8000)

def run_admin():
    from .admin import generate_MIE_file, get_shex, save_MIE_file, test_MIE_file
    asyncio.run(setup())
    mcp.run()

if __name__ == "__main__":
    run()

