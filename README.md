# Wallet Referee (V1)

Assistant de trading **spot** moyen terme.  
Chaque jour, un workflow GitHub exécute `script/generate_signal.py` qui produit `public/signal.json`.  
La webapp (Vite + React) lit ce JSON et affiche les recommandations BUY/SELL/HOLD.

## Config
- Modifie `PORTFOLIO_IDS` dans `script/generate_signal.py` pour tes tokens.
- (Optionnel) ajoute un secret `COINPAPRIKA_API_KEY` dans GitHub (`Settings > Secrets > Actions`) si tu as une clé.

## Lancer en local
```bash
npm install
npm run dev
# Dans un autre terminal
python -m pip install -r requirements.txt
python script/generate_signal.py
