"""Download Noto fonts used by PDF multilingual rendering."""
from __future__ import annotations

import os
import sys
import urllib.request


FONT_BASE_URL = "https://github.com/notofonts/noto-fonts/raw/main/hinted/ttf"
FONT_PATHS = {
    "NotoSans-Regular.ttf": "NotoSans/NotoSans-Regular.ttf",
    "NotoSansDevanagari-Regular.ttf": "NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    "NotoSansBengali-Regular.ttf": "NotoSansBengali/NotoSansBengali-Regular.ttf",
    "NotoSansGujarati-Regular.ttf": "NotoSansGujarati/NotoSansGujarati-Regular.ttf",
    "NotoSansGurmukhi-Regular.ttf": "NotoSansGurmukhi/NotoSansGurmukhi-Regular.ttf",
    "NotoSansTamil-Regular.ttf": "NotoSansTamil/NotoSansTamil-Regular.ttf",
    "NotoSansTelugu-Regular.ttf": "NotoSansTelugu/NotoSansTelugu-Regular.ttf",
    "NotoSansKannada-Regular.ttf": "NotoSansKannada/NotoSansKannada-Regular.ttf",
    "NotoSansMalayalam-Regular.ttf": "NotoSansMalayalam/NotoSansMalayalam-Regular.ttf",
    "NotoSansOriya-Regular.ttf": "NotoSansOriya/NotoSansOriya-Regular.ttf",
    "NotoSansSinhala-Regular.ttf": "NotoSansSinhala/NotoSansSinhala-Regular.ttf",
    "NotoSansArabic-Regular.ttf": "NotoSansArabic/NotoSansArabic-Regular.ttf",
    "NotoSansHebrew-Regular.ttf": "NotoSansHebrew/NotoSansHebrew-Regular.ttf",
    "NotoSansThai-Regular.ttf": "NotoSansThai/NotoSansThai-Regular.ttf",
    "NotoSansLao-Regular.ttf": "NotoSansLao/NotoSansLao-Regular.ttf",
    "NotoSansMyanmar-Regular.ttf": "NotoSansMyanmar/NotoSansMyanmar-Regular.ttf",
    "NotoSansKhmer-Regular.ttf": "NotoSansKhmer/NotoSansKhmer-Regular.ttf",
}


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    fonts_dir = os.path.join(repo_root, "lambda", "prescription_pdf_generator", "fonts")
    os.makedirs(fonts_dir, exist_ok=True)

    for filename, rel_path in FONT_PATHS.items():
        out_path = os.path.join(fonts_dir, filename)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            continue
        url = f"{FONT_BASE_URL}/{rel_path}"
        print(f"Downloading {filename} ...")
        urllib.request.urlretrieve(url, out_path)

    print(f"Fonts ready in: {fonts_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
