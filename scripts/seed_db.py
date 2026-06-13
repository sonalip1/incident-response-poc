import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.memory import seed_memory

def main():
    print("Initializing and seeding ChromaDB memory...")
    try:
        seed_memory()
        print("Database seeding completed successfully.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
