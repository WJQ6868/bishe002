from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "generated" / "thesis_assets"


def recolor_nonwhite_to_black(src: Path, dest: Path, white_threshold: int = 248) -> None:
    img = Image.open(src).convert("RGB")
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if r >= white_threshold and g >= white_threshold and b >= white_threshold:
                pixels[x, y] = (255, 255, 255)
            else:
                pixels[x, y] = (0, 0, 0)

    img.save(dest, quality=95)


def main() -> None:
    src = ASSET_DIR / "fig_2_1_system_architecture.png"
    dest = ASSET_DIR / "fig_2_1_system_architecture_black_v2.png"
    recolor_nonwhite_to_black(src, dest)
    print(dest)


if __name__ == "__main__":
    main()
