import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check if OPENAI_API_KEY is set
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("ERROR: OPENAI_API_KEY not found in environment variables or .env file")
    print("Please set your OpenAI API key before running this demo.")
    exit(1)

print("=== GraphRAG Demo Comparison ===\n")
print("This script will compare the in-memory GraphRAG approach with the Neo4j-based approach.\n")

# Check if Neo4j is configured
neo4j_password = os.getenv("NEO4J_PASSWORD")

if neo4j_password:
    print("Neo4j credentials found in .env file. Both demos can be run.\n")
    print("1. Run In-Memory GraphRAG Demo")
    print("2. Run Neo4j-based GraphRAG Demo")
    print("3. Run both demos and compare results")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        print("\nRunning In-Memory GraphRAG Demo...\n")
        from graphrag_demo import run_demo
        run_demo()
    elif choice == "2":
        print("\nRunning Neo4j-based GraphRAG Demo...\n")
        from graphrag_neo4j_demo import run_neo4j_demo
        run_neo4j_demo()
    elif choice == "3":
        print("\n=== In-Memory GraphRAG Demo ===\n")
        from graphrag_demo import run_demo
        run_demo()
        
        print("\n\n=== Neo4j-based GraphRAG Demo ===\n")
        from graphrag_neo4j_demo import run_neo4j_demo
        run_neo4j_demo()
    else:
        print("Invalid choice. Please run the script again.")
else:
    print("Neo4j credentials not found in .env file.")
    print("Only the in-memory GraphRAG demo will be available.\n")
    
    print("Running In-Memory GraphRAG Demo...\n")
    from graphrag_demo import run_demo
    run_demo()
    
    print("\nTo run the Neo4j-based demo, please set up Neo4j and update your .env file.")
    print("See the README.md for instructions.")


print("\n=== Comparison of GraphRAG Approaches ===\n")
print("1. In-Memory GraphRAG:")
print("   - Pros: Simple setup, no external dependencies, easy to understand")
print("   - Cons: Limited scalability, no persistence, basic functionality")
print("   - Best for: Learning GraphRAG concepts, small demos, prototyping\n")

print("2. Neo4j-based GraphRAG:")
print("   - Pros: Scalable, persistent storage, complex graph operations")
print("   - Cons: More complex setup, requires Neo4j knowledge")
print("   - Best for: Production systems, large document collections, complex relationships\n")

print("Key differences:")
print("1. Storage: In-memory vs. persistent graph database")
print("2. Scalability: Limited vs. high")
print("3. Query capabilities: Basic vs. advanced graph traversal")
print("4. Community detection: Simplified vs. algorithm-based")
print("5. Integration: Standalone vs. LlamaIndex ecosystem\n")

print("For more information, see the GraphRAG documentation:")
print("https://docs.llamaindex.ai/en/stable/examples/cookbooks/GraphRAG_v2/") 