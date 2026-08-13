from agentic_bim_iot.bootstrap import create_application

def main():
    with create_application() as graph:
        while True:
            user_query = input("> ").strip()
            if user_query.lower() in {"exit", "quit"}:
                break
            if not user_query:
                continue
            result = graph.invoke(
                {
                "user_query": user_query
            })
            print(result.get("final_answer", "No response was produced"))
            
            
            
if __name__ == "__main__":
    main()