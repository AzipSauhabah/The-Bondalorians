"""MCP boundary: synthetic adapter for local development, replace with CDC MCP clients later."""
from bondalorians.data.repository import load_comparables


class DemoMarketDataAdapter:
    name = "DEMO DATA (not CDC / not Murex / not BlackRock)"

    def search_bonds(self):
        return load_comparables()

    def describe(self) -> str:
        return "Returns a local synthetic bond universe. Replace this adapter with the official MCP tools after receiving CDC documentation and access."
