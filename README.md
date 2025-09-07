# Prometheus Framework
_An agentic framework to autonomously transform enterprise data into an intelligent, queryable digital twin._

![High-Level Diagram](https://github.com/kodox45/Prometheus-Framework/blob/e2e180ea7421b594b5dd11d04c63323c55496018/img/Screenshot%202025-09-04%20094329.png)

---

### **⚠️ Disclaimer & Personal Note**

Welcome to Prometheus!

This project is an ambitious exploration into the world of automated knowledge engineering and agentic AI. Please be aware that Prometheus is currently a **functional prototype** and is **not production-ready**. While the core workflow has been validated, there is still much work to be done on robust logging, error handling, and testing.

All development and testing so far have been conducted using an **Odoo ERP** database on PostgreSQL. Although designed to be database-agnostic, many of the current heuristics are tailored for such schemas.

On a personal note, this is my first major programming project. I began my coding journey about three months ago, and Prometheus is the result of my passion and dedication to solving complex data problems. I am incredibly open to feedback, suggestions, and contributions from the community. Thank you for checking it out!

---

### **The Fundamental Problem: The Enterprise "Data Chasm"**

In every modern enterprise, a massive "chasm" exists between the raw data stored in databases and the business insights required by decision-makers.

1.  **The Knowledge Chasm:** Databases are "dumb." They don't know that `res_partner` actually means "Customer," or that `state = 'sale'` represents a successful sales process. Humans must constantly translate this hidden business logic.
2.  **The Reasoning Chasm:** Business questions are abstract. "How can we improve customer retention?" cannot be answered by a single SQL query. It requires a deep understanding of how different parts of the business are interconnected.

Prometheus aims to bridge this chasm with a fundamental approach: **it builds understanding first**, rather than just translating queries.

### **The Prometheus Solution: The Genesis Engine**

The current core of Prometheus is the **Genesis Engine**, an end-to-end workflow that autonomously transforms a complex enterprise database into an **intelligent and accessible Knowledge Graph (KG)** in Neo4j.

**The Genesis Engine doesn't just copy your schema. It builds a "digital twin" of your data by:**
1.  **Performing Deep Schema Extraction:** Analyzing tables, columns, data types, Primary Keys, Foreign Keys (including their behavioral rules), indexes, and even detecting *Junction Tables*.
2.  **Gathering Multi-Faceted Evidence:** Acting like a data detective, it assembles an "evidence dossier" for each entity from multiple sources: the schema, relational context within the graph, ERP naming conventions, and statistics from the actual data itself.
3.  **Executing AI-Powered Semantic Synthesis:** Using a Large Language Model (LLM) to synthesize all evidence into a concise, structured understanding, including the entity's functional purpose, hidden business logic, and stereotype.
4.  **Discovering Implicit Relations:** Leveraging vector similarity search to find and validate hidden business relationships that are not defined by Foreign Keys.
5.  **Creating a High-Performance Vector Index:** Storing the semantic understanding as *vector embeddings* and automatically building a native vector index in Neo4j, making the entire KG ready for high-speed semantic search by future AI systems.

![Nodes](https://github.com/kodox45/Prometheus-Framework/blob/e2e180ea7421b594b5dd11d04c63323c55496018/img/Screenshot%202025-09-04%20094601.png)

### **Getting Started: A Guide for Developers**

Interested in trying it out? Here’s how to get Prometheus up and running.

#### **Prerequisites**
-   Docker & Docker Compose
-   Python 3.10+
-   Poetry (for dependency management)
-   An OpenAI Account & API Key

#### **1. Project Installation**

```bash
# 1. Clone the repository
git clone https://github.com/kodox45/Prometheus-Framework.git
cd Prometheus-Framework

# 2. Install dependencies with Poetry
poetry install

# 3. Set up your configuration file
cp .env.example .env
```

#### **2. Environment Configuration**

Open the newly created `.env` file and fill in all the values:
-   `POSTGRES_*`: Connection details for your PostgreSQL database.
-   `NEO4J_*`: Credentials for your Neo4j database.
-   `OPENAI_API_KEY`: Your personal OpenAI API key.
-   Adjust the LLM models and pricing if needed.

#### **3. Launch Docker Services**

The Odoo and Neo4j environment is managed by Docker Compose.

```bash
# 1. Navigate to the environment directory
cd environment

# 2. IMPORTANT: Open docker-compose.yml and set your NEO4J_AUTH password.
#    Ensure this password matches the one you set in your .env file.
#    Example: NEO4J_AUTH=neo4j/mysecretpassword

# 3. Launch all services in the background
docker-compose up -d
```

#### **4. Set Up the Odoo Database with Demo Data**

-   Open Odoo in your browser: `http://localhost:8069`.
-   You will see the Odoo database setup screen.
-   Enter a master password, a new database name (e.g., `odoo_demo`), an admin email, and a password.
-   **CRITICAL:** Check the **"Demonstration data"** checkbox. The Genesis Engine needs data to analyze.
-   Click "Create database". This process will take 5-10 minutes.
-   Once complete, make sure to update `POSTGRES_DB` in your `.env` file with the new database name you just created.

#### **5. Run the Genesis Engine**

You are now ready to run Prometheus!

```bash
# From the project's root directory

# Run the full process on a random sample of 20 entities
poetry run python -m scripts.run_enrichment_poc -- --sample-size 20
```
-   You will be prompted to confirm the estimated cost before the LLM calls begin. Type `yes` and press Enter to proceed.
-   After the process completes, you can inspect the results in your Neo4j Browser at `http://localhost:7474`.

### **Roadmap & Contributing**
This project is under active development. The next major steps include:
-   **Building the Reasoning Engine (V2.0):** Creating the agentic AI that uses this Knowledge Graph to answer questions.
-   **Adding More Stock Analyzers:** Implementing `NumericAnalyzer`, `DateTimeAnalyzer`, etc.
-   **Productionizing:** Adding robust logging, automated tests, and a clean Command-Line Interface (CLI).

Contributions, ideas, and feedback are highly welcome! Please feel free to open an **Issue** to discuss bugs, suggest features, or ask questions
