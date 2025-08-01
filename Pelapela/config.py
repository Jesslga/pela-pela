import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'language-concept-nodes.c5wimqww00fl.us-east-2.rds.amazonaws.com'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'dbname': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'jessg'),
    'password': os.getenv('DB_PASSWORD', 'pelapela!'),  # Fallback for backward compatibility
    'sslmode': os.getenv('DB_SSLMODE', 'require')
}

def get_db_connection_params():
    """Get database connection parameters from environment variables or config"""
    return DB_CONFIG.copy() 