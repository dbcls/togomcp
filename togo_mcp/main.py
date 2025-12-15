from .server import *
from .rdf_portal import *
from .api_tools import *
from .togoid import convertId, countId, getAllDataset, getDataset, getAllRelation, getRelation, getDescription

def run():
    mcp.run(transport="http", host="0.0.0.0", port=8000)

def run_admin():
    from .admin import generate_MIE_file, get_shex, save_MIE_file, test_MIE_file
    mcp.run()

if __name__ == "__main__":
    run()

