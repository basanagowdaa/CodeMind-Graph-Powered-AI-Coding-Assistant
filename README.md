# CodeMind — Graph-Powered AI Coding Assistant
## Hack Hydra 2026, Track 2B: Code Graphs for IDE Assistants

CodeMind helps developers understand the impact of changing code inside a repository. Its hero feature is **"Before You Change It"** — select a function, class, file, or API, and instantly trace what other parts of the codebase could be affected.

The architecture fundamentally depends on **HydraDB as a core context layer**, using the official **Bring Your Own Graph (BYOG)** API to ingest deterministic code relationships and traverse multi-hop dependency paths at query time.

---

## 🚀 Key Features

* **Deterministic Static AST Parsing**: Pure Python AST parsing that extracts files, functions, classes, imports, FastAPI/Flask api endpoints, and test definitions. **Never executes repository code.**
* **True HydraDB BYOG Integration**: Leverages the official `hydradb-sdk >=2,<3` to ingest code entities as `app_knowledge` items, mapping relationships explicitly using the `graph_payload` payload.
* **Blast Radius Impact Analysis**: Performs BFS/DFS traversals over the structural code graph combined with HydraDB `graph_context.query_paths` to identify affected callers, tests, and API routes.
* **Grounded AI Q&A**: Grounds Gemini AI chat prompts in code snippets and dependency paths retrieved from HydraDB, citing sources with line numbers and file paths.
* **Retrieval Benchmarking**: Compares vector similarity search (Baseline) vs HydraDB graph retrieval (CodeMind) on evaluation queries, logging latency and completeness metrics.
* **Interactive Code Map UI**: Reactive Dark Purple-themed IDE panel using React Flow to visualize entities and trace paths.

---

## 📁 Repository Structure

```
codemind/
├── analyzer/             # Repository scanner and AST Parser
│   ├── extractors/       # Entity & Relationship extractors
│   ├── graph/            # CodeGraph builder & HydraDB BYOG mapper
│   └── parsers/          # Pure Python AST parser (no execution)
│
├── backend/              # FastAPI Python Web Backend
│   ├── api/              # API Route controllers
│   ├── hydra/            # HydraDB client, ingestion & retrieval wrapper
│   ├── models/           # Pydantic & Data graph models
│   └── services/         # Analysis, Impact, AI & Benchmark logic
│
├── frontend/             # React + TypeScript + Tailwind UI
│   ├── src/
│   │   ├── components/   # React Flow Canvas, Detail Panels & Badge indicators
│   │   └── pages/        # Dashboard, Map, Chat, Impact, Search & Benchmark pages
│   └── vite.config.ts
│
├── demo-repository/      # A sample Python codebase to evaluate multi-hop logic
└── tests/                # 23 complete unit and integration tests
```

---

## ⚙️ Setup & Installation

### 1. Configure Environment Variables
Copy `.env.example` to `.env` in the root folder:
```bash
cp .env.example .env
```
Fill in the following variables:
* `HYDRA_DB_API_KEY`: Your official HydraDB token (from [app.hydradb.com](https://app.hydradb.com)).
* `GOOGLE_API_KEY`: Your Gemini API key (for grounded AI reasoning).

### 2. Install Backend Dependencies
Requires **Python 3.10+**:
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
Requires **Node.js**:
```bash
cd frontend
npm install
```

---

## 🏃 Running the Application

### 1. Start the FastAPI Backend
From the root folder, launch the backend uvicorn process on port `8000`:
```bash
python -m uvicorn backend.main:app --reload --port 8000
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the Swagger API docs.

### 2. Start the React Frontend
In a new terminal window, launch the Vite development server on port `3000`:
```bash
cd frontend
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to load the CodeMind web workspace.

---

## 🧪 Verification & Testing

Verify that the AST parser, graph builder, impact calculations, and API controllers are fully functional by running the test suite:
```bash
python -m pytest tests/ -v
```

All 23 backend tests should pass successfully.

---

## 📖 Using the Demo flow

1. Go to the **Overview** dashboard and ingest the local demo repository by entering:
   `C:\HACK PROJECTS\Codemind\demo-repository`
2. Once ingestion reaches `ready`, go to the **Repository Map** page.
3. Click on the `authenticate_user` node, and select **BEFORE YOU CHANGE IT** in the sidebar.
4. Traced downstream impact paths, affected API endpoints (`/login`), and coverages (`test_auth.py`) will load automatically under the **Impact Analysis** tab.
5. Ask grounded questions in the **Ask CodeMind** console such as `"What calls authenticate_user?"`.
