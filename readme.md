Run the Project

1. Clone the repository

git clone LINK_DELLA_REPO
cd Agentic-AI-Smart-Building

2. Create and activate a virtual environment

python -m venv .venv
.\.venv\Scripts\Activate.ps1

3. Install the project

python -m pip install --upgrade pip
pip install -e .

The project dependencies are defined in pyproject.toml.

4. Configure the required environment variables
COPY THE CONTENT OF THE FILE .env.example INTO .env 
For example:

$env:OPENAI_API_KEY="..."

Configure any additional credentials required by the project, such as ThingsBoard connection settings.

5. Load the ontologies
GRAPHDB/NEO4j
python scripts/load_graphdb_ontology.py
python scripts/load_neo4j_ontology.py

6. Create the devices in ThingsBoard

python scripts/add_device_thingsboard.py

7. Populate ThingsBoard with telemetry data

python scripts/populate_thingsboard.py

8. Run the project

python src/agentic_bim_iot/main.py