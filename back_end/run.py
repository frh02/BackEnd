"""IMPORT FLASK INSTANCES FROM FOLDER FrontEnd"""

from back import webapp as back
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)  # Set the desired log level
logger = logging.getLogger(__name__)
if __name__ == "__main__":

    # Run the Flask application
    try:
        back.run(
            host='0.0.0.0',
            port='5001',
            debug=False,  # Disable debug mode in production
            use_reloader=False,
            use_debugger=False,
            threaded=True
        )
    except Exception as e:
        # Log any exceptions that occur during the application startup
        logger.error("An error occurred during application startup: %s", str(e))