# Le lien avec Mistral Studio

## A quoi sert Studio ici

Studio (console.mistral.ai) definit **les profils d'agents** (revue des
risques, explicabilite) et **le workflow orchestre** (etapes, transferts,
conditions d'arret), et donne l'observabilite (traces, tokens).

## Repartition du travail

| Sert a | Vit dans |
|---|---|
| Prompts de revue et d'explication | `src/bondalorians/agent/orchestreteur.py` (PROMPT_REVUE, PROMPT_EXPLICABILITE) : version autonome |
| Les memes agents en version managée | Studio : ces memes prompts + nos outils MCP en "tools" |
| Orchestration sequentielle | local : `valoriser()` ; Studio : Workflows |
| Calculs (comparables, pricing, audit) | Toujours notre serveur MCP Python, jamais Studio |
| Traces | local : `data/audit/*.json` ; Studio : Observability |

## Tester l'architecture dans Studio (apres le webinaire du 13/11)

1. Agents "Revue des risques" et "Explicabilite" avec nos prompts, modele
   mistral-small-latest.
2. Connecter le serveur MCP (URL + cle) : Studio doit voir lister_univers,
   chercher_comparables, pricer_cible, enregistrer_audit.
3. Workflow : chercher_comparables -> pricer_cible -> revue -> explicabilite
   -> enregistrer_audit.
4. Comparer appels et tokens version locale vs Studio (critere README :
   3 a 5 appels LLM par valorisation).

Point a valider : l'acces de l'environnement Studio du hackathon a un
serveur MCP distant (HTTPS + auth) - le README du depot le signale.
