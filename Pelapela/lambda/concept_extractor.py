import logging
try:
    import numpy
    logging.info(f"Numpy version in Lambda: {numpy.__version__}")
except ImportError as e:
    logging.warning(f"Numpy not available: {e}") 