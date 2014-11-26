""" Logging module
"""
import os
import sys
import logging

def minimal_logger(namespace, debug=False):
    """Make and return a minimal console logger. Optionally write to a file as well.

    :param str namespace: Namespace of logger
    :param bool debug: Log in DEBUG level or not

    :return: A logging.Logger object
    :rtype: logging.Logger
    """
    log_level = logging.DEBUG if debug else logging.INFO
    log = logging.getLogger(namespace)
    log.setLevel(log_level)

    # Logs to console
    s_h = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    s_h.setFormatter(formatter)
    s_h.setLevel(log_level)
    log.addHandler(s_h)
    return log