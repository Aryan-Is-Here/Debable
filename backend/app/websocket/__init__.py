"""WebSocket transport for debate chat.

``registry`` tracks who is connected to which room; ``auth`` turns a socket's first frame
into an authenticated user. The endpoint that uses both lives in ``app/api/v1/chat.py``.
"""
