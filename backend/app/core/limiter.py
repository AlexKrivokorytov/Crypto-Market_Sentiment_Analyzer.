"""
Rate limiter configuration for the Market Sentiment Analyzer.

Exposes a slowapi Limiter singleton keyed by client remote address.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiters are keyed by the remote client IP address
limiter = Limiter(key_func=get_remote_address)
