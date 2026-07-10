#!/usr/bin/env python3
"""
Main entry point for the Flask API
Security-enhanced with comprehensive middleware integration
"""

import os
import logging
from app import create_app, db

# Configure main application logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the Flask application with security middleware
app = create_app()

# Log application startup
logger.info("API starting with security middleware enabled")
logger.info(f"Security features: Rate limiting, JWT auth, Security headers, CORS protection")

if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
