# Contexte projet (pour l'agent de developpement)

Regles du depot (cf. README) :
- Les calculs numeriques font autorite et sont DETERMINISTES (src/bondalorians/pricing,
  matching) : jamais le LLM n'invente un spread ni ne calcule.
- Les agents ne communiquent que via l'orchestrateur, pas entre eux.
- Objectif : 3 a 5 appels LLM par valorisation ; filtrer en Python avant.
- Tout rapport passe par la piste d'audit (outil enregistrer_audit).
- Ne jamais committer de cle (.env ignore) ni de donnees privees.
- pytest -q doit passer sans reseau ni cle API.
