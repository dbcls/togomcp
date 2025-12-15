#!/usr/bin/env python3
"""
togo_mcp パッケージを使用する例
"""

# togo_mcp パッケージからモジュールをインポート
from togo_mcp.server import mcp, SPARQL_ENDPOINT, MIE_DIR

# 特定のモジュール全体をインポート
from togo_mcp import main

def main_example():
    """togo_mcp の機能を使用する例"""
    
    # SPARQL_ENDPOINTを表示
    print("利用可能なSPARQLエンドポイント:")
    for db_name, endpoint_url in SPARQL_ENDPOINT.items():
        print(f"  {db_name}: {endpoint_url}")
    
    # MIEディレクトリのパスを表示
    print(f"\nMIEディレクトリ: {MIE_DIR}")
    
    # mcpオブジェクトの情報を表示
    print(f"\nMCPサーバー名: {mcp.name}")

if __name__ == "__main__":
    main_example()
