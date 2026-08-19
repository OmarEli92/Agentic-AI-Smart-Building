from agentic_bim_iot.bootstrap import create_application
from langchain_core.callbacks import UsageMetadataCallbackHandler

def main():
    with create_application() as graph:
        while True:
            user_query = input("> ").strip()
            if user_query.lower() in {"exit", "quit"}:
                break
            if not user_query:
                continue
            usage_callback = UsageMetadataCallbackHandler()
            try:
              result = graph.invoke({"user_query": user_query},config={"callbacks": [usage_callback]},)
              print(result["final_answer"])
            finally:
                print()
                print("=" * 70)
                print("LLM TOKEN USAGE")
                print("=" * 70)
                for (model, usage) in usage_callback.usage_metadata.items():
                    print(f"Model: {model}")
                    print(f"Input tokens:  {usage.get('input_tokens', 0)}")
                    print(f"Output tokens: {usage.get('output_tokens', 0)}")
                    print(f"Total tokens:  {usage.get('total_tokens', 0)}")
                    print()
                print("=" * 70)
  
            
            
            
if __name__ == "__main__":
    main()