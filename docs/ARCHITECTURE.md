# Architecture decisions

## Why a deterministic pricing core?

The language model should interpret user intent, select tools and explain evidence. It should not invent market observations or perform unverified arithmetic. Bond matching and valuation are deterministic Python functions with test coverage.

## Why an adapter boundary?

The CDC MCP interfaces are not yet available in this local starter. `DemoMarketDataAdapter` makes the app runnable now while isolating the future Murex / BlackRock MCP integration. Replace the adapter only after reviewing the official tool schemas, permissions and data dictionary.

## Why LangGraph?

The current graph is deliberately small and sequential: retrieve → rank → price → explain. It provides a working base for conditional panel expansion, human approval, retries and alternative pricing branches.

## Next increments

1. Inspect CDC MCP tool schemas and map them to typed application functions.
2. Replace the synthetic CSV with authorized data retrieval.
3. Add issuer/group graph relationships and document RAG only where useful.
4. Add Mistral tool calling through LangGraph.
5. Calibrate similarity weights and spread model on a time-consistent train/test split.
6. Add bond conventions, accrued interest, option-adjusted spread and complex cashflows as required by the test cases.
