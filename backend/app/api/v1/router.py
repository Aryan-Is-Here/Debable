"""Aggregates every v1 route under a single mountable router.

Feature routers (topics, match, rooms, ...) are added here as their phases land.
"""

from fastapi import APIRouter

from app.api.v1 import chat, health, match, topics

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(topics.router)
api_router.include_router(match.router)
api_router.include_router(chat.router)
