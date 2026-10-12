"""Do not log user inputs, article bodies or screenshot contents."""
import logging


def get_logger(name):
    return logging.getLogger(name)
