"""Business rules. Services orchestrate repositories, own transaction boundaries, and raise
``AppError`` subclasses rather than HTTP exceptions.
"""
