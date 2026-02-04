#!/usr/bin/env python3
"""Setup script for tsrkit-types package."""

from setuptools import Extension, setup

extensions = [Extension("tsrkit_types._native", sources=["tsrkit_types/_native.c"])]

# Use pyproject.toml for configuration
setup(ext_modules=extensions)
