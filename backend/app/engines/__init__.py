"""Pluggable AI execution engines.

Keep this package initializer import-free.  Engine modules depend on shared
types from this package, so eagerly importing the service here creates a
circular import when execution-token helpers are used by standalone workers.
"""
