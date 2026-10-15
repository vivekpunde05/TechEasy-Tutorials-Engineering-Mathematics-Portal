import sys
import os

# Add root project folder to sys.path so all imports (app, config, database, routes) work seamlessly
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import app

# Export WSGI application object for Vercel Serverless Function
handler = app
