"""Módulo de datos - Acceso a datos ISTAC y almacenamiento local."""

from .istac_client import ISTACClient, get_client

__all__ = ['ISTACClient', 'get_client']
