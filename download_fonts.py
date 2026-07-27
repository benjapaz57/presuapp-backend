"""
Descarga las fuentes Roboto necesarias para la generación de PDFs.
Ejecutar una sola vez: python download_fonts.py
"""
import os
import urllib.request

FONTS_DIR = os.path.join(os.path.dirname(__file__), "app", "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

FONTS = {
    "Roboto-Regular.ttf": "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
    "Roboto-Bold.ttf":    "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "Roboto-Italic.ttf":  "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Italic.ttf",
}

for filename, url in FONTS.items():
    path = os.path.join(FONTS_DIR, filename)
    if os.path.exists(path):
        print(f"  ✓ {filename} ya existe")
    else:
        print(f"  ↓ Descargando {filename}...")
        urllib.request.urlretrieve(url, path)
        print(f"  ✓ {filename} descargado")

print("\nFuentes listas en app/fonts/")
