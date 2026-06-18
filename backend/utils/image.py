from pathlib import Path

import cv2

MAX_QUERY_DIMENSION = 1280


def resize_if_needed(image_path: Path, max_dimension: int = MAX_QUERY_DIMENSION) -> Path:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    h, w = image.shape[:2]
    if max(h, w) <= max_dimension:
        return image_path

    scale = max_dimension / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    cv2.imwrite(str(image_path), resized)
    return image_path
