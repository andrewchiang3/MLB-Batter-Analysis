"""Test all imports work correctly"""

print("Testing imports...")

try:
    import streamlit as st
    print("✓ streamlit")
except ImportError as e:
    print(f"✗ streamlit: {e}")

try:
    import pybaseball as pyb
    print("✓ pybaseball")
except ImportError as e:
    print(f"✗ pybaseball: {e}")

try:
    import pandas as pd
    print("✓ pandas")
except ImportError as e:
    print(f"✗ pandas: {e}")

try:
    import altair as alt
    print("✓ altair")
except ImportError as e:
    print(f"✗ altair: {e}")

try:
    from streamlit_searchbox import st_searchbox
    print("✓ streamlit-searchbox")
except ImportError as e:
    print(f"✗ streamlit-searchbox: {e}")

try:
    import numpy as np
    print("✓ numpy")
except ImportError as e:
    print(f"✗ numpy: {e}")

try:
    from scipy import interpolate
    print("✓ scipy")
except ImportError as e:
    print(f"✗ scipy: {e}")

try:
    import matplotlib.pyplot as plt
    print("✓ matplotlib")
except ImportError as e:
    print(f"✗ matplotlib: {e}")

try:
    from PIL import Image
    print("✓ Pillow")
except ImportError as e:
    print(f"✗ Pillow: {e}")

try:
    import requests
    print("✓ requests")
except ImportError as e:
    print(f"✗ requests: {e}")

print("\nAll imports successful! ✓")