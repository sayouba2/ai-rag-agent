# AI RAG Agent

Application de **Retrieval-Augmented Generation** permettant d'interroger vos propres documents en langage naturel.

Uploadez des fichiers PDF, Word, Markdown, CSV ou texte — posez des questions — obtenez des réponses sourcées générées par GPT-4o Mini, avec historique de conversation et réponses en streaming.

---

## Aperçu

```
┌─────────────────────────────────────────────────┐
│                   Navigateur                    │
│              React + Vite (port 5173)           │
└─────────────────────┬───────────────────────────┘
                      │ HTTP / SSE
┌─────────────────────▼───────────────────────────┐
│               FastAPI (port 8000)               │
│  POST /upload   POST /ask   POST /ask/stream    │
│  GET  /history  DELETE /history                 │
└──────────┬─────────────────────┬────────────────┘
           │                     │
    ┌──────▼──────┐       ┌──────▼──────┐
    │  ChromaDB   │       │  OpenAI API │
    │ (vecteurs)  │       │ GPT-4o Mini │
    └─────────────┘       └─────────────┘
```

---

## Fonctionnalités

- **Upload multi-fichiers** — PDF, TXT, DOCX, Markdown, CSV
- **Indexation incrémentale** — seuls les fichiers nouveaux ou modifiés sont réindexés (détection par hash SHA-256)
- **Chat avec historique** — les questions de suivi sont comprises grâce au contexte des échanges précédents
- **Streaming** — la réponse s'affiche token par token via Server-Sent Events
- **Sources citées** — chaque réponse indique les documents et pages utilisés
- **Sécurité** — validation de l'extension et de la taille côté serveur, protection contre le path traversal

---

## Stack technique

| Couche | Technologies |
|---|---|
| Frontend | React 19, Vite 5 |
| Backend | FastAPI, Python 3.12 |
| LLM | LangChain, OpenAI GPT-4o Mini |
| Mémoire vectorielle | ChromaDB |
| Loaders | PyPDF, docx2txt, LangChain Community |

---

## Prérequis

- Python 3.10+
- Node.js 18+
- Une clé API OpenAI

---

## Installation

### 1. Cloner le projet

```bash
git clone <url-du-repo>
cd ai-rag-agent
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Édite `.env` et renseigne ta clé OpenAI :

```env
OPENAI_API_KEY=sk-...
```

### 3. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate       # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Frontend

```bash
cd frontend
npm install
```

---

## Démarrage

Ouvre **deux terminaux**.

**Terminal 1 — Backend**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm run dev
```

Ouvre [http://localhost:5173](http://localhost:5173) dans ton navigateur.

> **Vérification** : [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) doit retourner `{"status": "ok"}`

---

## Utilisation

1. **Uploader des documents** — clique sur *Choisir des fichiers*, sélectionne un ou plusieurs fichiers, puis *Uploader & Indexer*
2. **Poser une question** — tape ta question dans le chat et appuie sur **Entrée** (Maj+Entrée pour sauter une ligne)
3. **Consulter les sources** — chaque réponse affiche un lien dépliable vers les passages utilisés
4. **Nouvelle conversation** — le bouton *Nouvelle conversation* efface l'historique côté client et serveur

---

## Structure du projet

```
ai-rag-agent/
├── .env                        # Variables d'environnement (non versionné)
├── .env.example                # Modèle de configuration
│
├── backend/
│   ├── app/
│   │   ├── config.py           # Chargement de la configuration
│   │   ├── schemas.py          # Modèles Pydantic (requêtes / réponses)
│   │   ├── ingest.py           # Chargement, découpage et indexation des documents
│   │   ├── rag_chain.py        # Chaîne RAG avec historique et streaming
│   │   └── main.py             # Routes FastAPI et lifespan
│   ├── tests/
│   │   └── test_endpoints.py   # Tests des endpoints
│   ├── requirements.txt
│   └── pytest.ini
│
└── frontend/
    ├── src/
    │   ├── App.jsx             # Interface chat principale
    │   ├── api.js              # Appels API (fetch + streaming SSE)
    │   └── App.css             # Styles globaux
    ├── vite.config.js
    └── package.json
```

---

## API

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Vérification du statut |
| `POST` | `/upload` | Upload et indexation de fichiers |
| `POST` | `/ingest` | Ré-indexation des fichiers déjà présents |
| `POST` | `/ask` | Question / réponse (synchrone) |
| `POST` | `/ask/stream` | Question / réponse en streaming SSE |
| `GET` | `/history/{id}` | Historique d'une session |
| `DELETE` | `/history/{id}` | Suppression d'une session |

Documentation interactive disponible sur [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## Tests

```bash
cd backend
source venv/bin/activate
pytest -v
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Clé API OpenAI (obligatoire) |
| `CHROMA_DIR` | `chroma_db` | Répertoire de la base vectorielle |
| `DATA_DIR` | `data` | Répertoire des documents uploadés |
| `CORS_ORIGINS` | `http://localhost:5173` | Origines CORS autorisées (virgule-séparées) |
| `MAX_FILE_SIZE_MB` | `50` | Taille maximale d'un fichier uploadé (Mo) |
| `VITE_API_URL` | `http://127.0.0.1:8000` | URL de l'API appelée par le frontend |

---

## Licence

MIT
