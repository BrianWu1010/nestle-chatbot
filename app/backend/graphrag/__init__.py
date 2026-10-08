"""Lightweight GraphRAG module: entity graph built from scraped pages, used to expand retrieval."""

from .schema import Edge, KnowledgeGraph, Node

__all__ = ["Edge", "KnowledgeGraph", "Node"]
