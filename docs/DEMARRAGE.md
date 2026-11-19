# Demarrage rapide

## 0. Ce que fait la pile

```
[GUI Streamlit :8501]  --deposés un job-->  [data/jobs.db]  <--consomme--  [Worker]
        \                                                        |
         \--show Home.py : pricing---------                [Orchestrateur
         \--page Agent & File : jobs/audit                  (revue + explication Mistral)]
                                                                   |
                                                                   v
                                              [Serveur MCP :8000/mcp]
                                              outils deterministes :
                                              univers, comparables, pricing, audit
```

Deux transports equivalents : `make mcp` (poste dev) ou `docker compose up`
(tout en containers, la config cible du hackathon).

## 1. Variables d'environnement (fichier .env, deja present)

| Variable | Role | Exemple |
|---|---|---|
| MISTRAL_API_KEY | cle LLM Mistral (equipe) | xxxx |
| MISTRAL_MODEL | modele | mistral-small-latest |
| MCP_URL | URL du notre serveur MCP | http://localhost:8000/mcp |
| HACKATHON_MCP_URL | API metier CDC (VM) | https://apim-hackathon-internal.azure-api.net/uc3/mcp |
| TEAM_KEY | cle d'equipe (header Ocp-Apim-Subscription-Key) | xxxx |

Ajoutez-y MCP_URL et TEAM_KEY si absents. Sans MISTRAL_API_KEY, tout tourne
sauf la revue et l'explication (marquees NON_EXECUTE).

## 2. En local sans Docker (lire le code)

```bash
source .venv/bin/activate
make test              # le socle quantitatif, sans reseau
make mcp               # terminal 1 : serveur MCP sur :8000
make gui               # terminal 2 : GUI sur :8501 (Home + Agent & File)
make worker            # terminal 3 : le worker prend les jobs deposés
```

Ou complet avec Docker : `make up` (compose : GUI + MCP + worker).

## 3. Test rapide de la chaine MCP

```bash
# outils listes par le serveur :
curl -s -X POST http://localhost:8000/mcp \
  -H 'content-type: application/json' \
  -H 'accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## 4. Git (votre depot GitHub)

```bash
git init && git add -A && git commit -m "Socle : MCP, agent Mistral, worker, Docker, docs"
git remote add origin https://github.com/AzipSauhabah/The-Bondalorians.git
git push -u origin main
```

## 5. Passage au hackathon (VM, API metier uc3)

1. Dans le .env de la VM : `MCP_URL=https://apim-hackathon-internal.azure-api.net/uc3/mcp`, `TEAM_KEY=<clé>`.
2. Adapter les outils du serveur aux schemas reels de l'API (map : donner
   les colonnes BP2S/EUROCLEAR/SIX/BLOOMBERG → notre BondRequest), dans
   `src/bondalorians/integrations/mcp_adapter.py` (le point d'entree prevu).
3. Les erreurs connues (401/404/405/504) et leur solution sont dans
   `docs/reference/03-FAQ-DEPANNAGE.pdf` ; le client envoie deja
   `Ocp-Apim-Subscription-Key` et ne fait que du POST.
