# ==============================================================================
# File:      api/app/config/__init__.py
# Purpose:   Package init for config. Re-exports Config for convenient
#            importing.
# Callers:   Any module importing from app.config
# Callees:   config/settings.py
# Modified:  2026-06-01
# ==============================================================================
from .settings import Config

__all__ = ['Config']
