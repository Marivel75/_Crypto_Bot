Guide d'installation — Crypto Bot

 Prerequis

 - Docker + Docker Compose installes
 - Git pour cloner le repo

 Etapes

 git clone <repo_url>
 cd crypto-bot
 cp .env.example .env

 Ensuite, editer le fichier .env et remplacer toutes les valeurs CHANGE_ME :

 Variables d'environnement obligatoires

 ┌─────────────────────┬────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────────┐
 │ Variable │ Description │ Exemple │
 ├─────────────────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
 │ POSTGRES_PASSWORD │ Mot de passe TimescaleDB │ Un mot de passe fort (ex: Kx9$mP2vL!qR) │
 ├─────────────────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
 │ DATABASE_URL │ URL de connexion a la DB (doit reprendre le meme password) │ postgresql://cryptobot:<MOT_DE_PASSE>@timescaledb:5432/cryptobot │
 ├─────────────────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
 │ MINIO_ROOT_USER │ User MinIO (stockage objets) │ minioadmin (valeur par defaut OK) │
 ├─────────────────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
 │ MINIO_ROOT_PASSWORD │ Password MinIO │ Un mot de passe fort │
 ├─────────────────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
 │ API_SECRET_KEY │ Cle secrete pour signer les JWT │ Une chaine aleatoire longue (ex: openssl rand -hex 32) │
 ├─────────────────────┼────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────────┤
 │ COINGECKO_API_KEY │ Cle API CoinGecko (gratuite, plan Demo) │ S'inscrire sur coingecko.com/api → copier la cle Demo │
 └─────────────────────┴────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────────┘

 Variables optionnelles

 ┌────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ Variable │ Description │
 ├────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ OPENAI_API_KEY │ Pour le chatbot IA (page Portfolio). Sans cette cle, le chatbot repond avec un message par defaut. │
 ├────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ ANTHROPIC_API_KEY │ Alternative a OpenAI pour le chatbot │
 ├────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
 │ GF_SECURITY_ADMIN_PASSWORD │ Password Grafana (monitoring, defaut: admin) │
 └────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘

 Lancement

 docker compose up -d

 Les tables de la base de donnees sont creees automatiquement au premier demarrage de l'API.

 Acces

 ┌──────────────────────┬────────────────────────────────┐
 │ Service │ URL │
 ├──────────────────────┼────────────────────────────────┤
 │ Frontend (Streamlit) │ http://localhost:8501 │
 ├──────────────────────┼────────────────────────────────┤
 │ API (FastAPI) │ http://localhost:8000 │
 ├──────────────────────┼────────────────────────────────┤
 │ API docs (Swagger) │ http://localhost:8000/api/docs │
 ├──────────────────────┼────────────────────────────────┤
 │ Grafana (monitoring) │ http://localhost:3000 │
 ├──────────────────────┼────────────────────────────────┤
 │ MLflow (experiments) │ http://localhost:5000 │
 ├──────────────────────┼────────────────────────────────┤
 │ MinIO console │ http://localhost:9001 │
 └──────────────────────┴────────────────────────────────┘

 Notes importantes

 - Le collecteur ETL demarre automatiquement et commence a ingerer les donnees de Binance/CoinGecko. Les premieres bougies apparaissent sur le Dashboard apres ~2 minutes.
 - La cle CoinGecko est necessaire pour les donnees de marche (market cap, fear & greed). Sans elle, seules les donnees Binance sont collectees.
 - Le chatbot necessite une cle OpenAI ou Anthropic. C'est la seule fonctionnalite payante — tout le reste est gratuit.
 - Pour changer la langue (FR/EN), utiliser le selecteur "Langue" dans la sidebar.