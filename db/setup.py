"""Database setup and connection management for SnipVault."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "snipvault")

# Pinecone configuration for Gemini text-embedding-004 (768 dimensions)
EMBEDDING_DIMENSION = 768


def get_db_connection():
    """Get a PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        raise Exception(f"Failed to connect to PostgreSQL: {e}")


def initialize_postgres():
    """Initialize PostgreSQL database with schema."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Read and execute bootstrap SQL
        bootstrap_path = Path(__file__).parent / "bootstrap.sql"
        with open(bootstrap_path, 'r') as f:
            sql = f.read()
            cursor.execute(sql)

        conn.commit()
        cursor.close()
        conn.close()

        print("✓ PostgreSQL database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize PostgreSQL: {e}")
        return False


def get_pinecone_client():
    """Get Pinecone client instance."""
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)
        return pc
    except Exception as e:
        raise Exception(f"Failed to initialize Pinecone client: {e}")


def initialize_pinecone():
    """Initialize Pinecone index for vector storage."""
    try:
        pc = get_pinecone_client()

        # Check if index exists
        existing_indexes = pc.list_indexes()
        index_names = [index.name for index in existing_indexes]

        if PINECONE_INDEX_NAME not in index_names:
            # Create new index with serverless spec
            # For free tier, use us-east-1 AWS or auto-detect
            print(f"Creating Pinecone index '{PINECONE_INDEX_NAME}'...")

            # Try different serverless configurations
            serverless_configs = [
                {'cloud': 'aws', 'region': 'us-east-1'},
                {'cloud': 'gcp', 'region': 'us-central1'},
            ]

            created = False
            last_error = None

            for config in serverless_configs:
                try:
                    pc.create_index(
                        name=PINECONE_INDEX_NAME,
                        dimension=EMBEDDING_DIMENSION,
                        metric='cosine',
                        spec=ServerlessSpec(
                            cloud=config['cloud'],
                            region=config['region']
                        )
                    )
                    print(f"✓ Created Pinecone index: {PINECONE_INDEX_NAME} ({config['cloud']}/{config['region']})")
                    created = True
                    break
                except Exception as e:
                    last_error = e
                    continue

            if not created:
                raise Exception(f"Failed to create index. Last error: {last_error}")
        else:
            print(f"✓ Pinecone index already exists: {PINECONE_INDEX_NAME}")

        return True
    except Exception as e:
        print(f"✗ Failed to initialize Pinecone: {e}")
        return False


def get_pinecone_index():
    """Get Pinecone index instance."""
    try:
        pc = get_pinecone_client()
        index = pc.Index(PINECONE_INDEX_NAME)
        return index
    except Exception as e:
        raise Exception(f"Failed to get Pinecone index: {e}")


def initialize_all():
    """Initialize both PostgreSQL and Pinecone."""
    print("Initializing SnipVault databases...")

    postgres_ok = initialize_postgres()
    pinecone_ok = initialize_pinecone()

    if postgres_ok and pinecone_ok:
        print("\n✓ All databases initialized successfully!")
        return True
    else:
        print("\n✗ Database initialization failed")
        return False


if __name__ == "__main__":
    initialize_all()
