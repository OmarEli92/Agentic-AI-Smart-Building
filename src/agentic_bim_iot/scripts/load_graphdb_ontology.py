import argparse
from pathlib import Path
from rdflib.contrib.graphdb.client import GraphDBClient
from agentic_bim_iot.config.settings import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ONTOLOGY_PATH = (PROJECT_ROOT / "resources" /"ontology" / "openSmartHome_Donkers_v2.ttl")

def _build_auth() -> tuple[str, str] | None:
    settings = get_settings()
    if( settings.graphdb_username is None or settings.graphdb_password is None):
        return None
    username = settings.graphdb_username.strip()
    password = settings.graphdb_password.get_secret_value().strip()
    if not username or not password:
        return None
    return username, password


def load_onotolgy(*, replace: bool ):
    settings = get_settings()
    if not ONTOLOGY_PATH.is_file():
        raise FileNotFoundError(f"Ontology file not found in the path: {ONTOLOGY_PATH}")
    auth = _build_auth()
    with GraphDBClient(base_url=settings.graphdb_url, auth=auth,timeout=settings.graphdb_timeout_seconds) as client:
        repository = client.repositories.get(settings.graphdb_repository)
        current_size = repository.size()
        print(f"Repository: {settings.graphdb_repository}")
        print(f"Current statements: {current_size}")
        print(f"Ontology path: {ONTOLOGY_PATH}")
        if current_size > 0 and not replace:
            raise RuntimeError("The GraphDB repository is not empty. Run again with --replace only if you want to replace its current content.")
        with ONTOLOGY_PATH.open("rb") as ontology_file:
            if replace:
                repository.overwrite(data = ontology_file, content_type="text/turtle")
            else:
                repository.upload(data = ontology_file, content_type="text/turtle")
            final_size = repository.size()
            print(f"Import completed. Statements: {final_size}")
        
def main():
    parser = argparse.ArgumentParser(description=("Load the smart building ontology into GraphDB"))
    parser.add_argument("--replace", action="store_true", help="Replace all current repository data with the ontology")
    args = parser.parse_args()
    load_onotolgy(replace=args.replace)
    
    
if __name__ == "__main__":
    main()