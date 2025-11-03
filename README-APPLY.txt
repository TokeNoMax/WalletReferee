WalletReferee — Patch V1 (exécutable)
====================================

Contenu du patch :
- requirements.txt
- .github/workflows/generate-signals.yml
- script/generate_signal.py
- src/types/signal.ts
- src/components/Signals.tsx

Comment appliquer (méthode rapide via GitHub UI) :
1) Ouvre ton dépôt : https://github.com/TokeNoMax/WalletReferee
2) Crée une nouvelle branche : patch/walletreferee-v1
3) Upload les fichiers de ce zip aux emplacements indiqués (respecte l'arborescence).
4) Commit puis ouvre une Pull Request vers main.
5) Dans l'onglet "Actions", lance manuellement le workflow "Generate signals" (workflow_dispatch).
6) Vérifie :
   - L'artefact "generation-logs" est présent.
   - Le fichier public/signal.json est commit par le bot (ou a changé).
   - L'app lit bien les nouvelles propriétés (status, generatedAt, entries[*]).

Comment appliquer (en local) :
1) Dézippe ce fichier dans la racine du projet.
2) `pip install -r requirements.txt`
3) `python script/generate_signal.py` (génère public/signal.json)
4) `npm install && npm run dev`
5) Ouvre l'app et vérifie l'affichage des signaux.

Notes :
- Le workflow est planifié quotidiennement à 05:10 UTC (~06:10 Europe/Paris).
- Le script produit un JSON valide même en cas d'erreurs partielles (status=degraded).
- Tu peux éditer la liste PORTFOLIO dans script/generate_signal.py.

Généré le 2025-11-03T14:00:57.946339Z
