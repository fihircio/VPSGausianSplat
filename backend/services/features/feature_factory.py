from __future__ import annotations
import abc
from pathlib import Path

import cv2
import numpy as np
import torch
import kornia.feature as KF
from kornia.color import rgb_to_grayscale

from backend.utils.config import get_settings


class BaseExtractor(abc.ABC):
    @abc.abstractmethod
    def extract(self, image_path: Path) -> tuple[np.ndarray, np.ndarray]:
        """Returns (keypoints_xy, descriptors)"""
        pass


class ORBExtractor(BaseExtractor):
    def extract(self, image_path: Path) -> tuple[np.ndarray, np.ndarray]:
        settings = get_settings()
        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise RuntimeError(f"Unable to read image: {image_path}")
        orb = cv2.ORB_create(nfeatures=settings.orb_nfeatures)
        keypoints, descriptors = orb.detectAndCompute(image, None)
        if descriptors is None or not keypoints:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 32), dtype=np.uint8)
        keypoints_xy = np.array([kp.pt for kp in keypoints], dtype=np.float32)
        return keypoints_xy, descriptors.astype(np.uint8)


class DISKExtractor(BaseExtractor):
    def __init__(self):
        settings = get_settings()
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        self.extractor = KF.DISK.from_pretrained('depth').to(self.device).eval()

    def extract(self, image_path: Path) -> tuple[np.ndarray, np.ndarray]:
        image_cv = cv2.imread(str(image_path))
        if image_cv is None:
            raise RuntimeError(f"Unable to read image: {image_path}")
        
        # Preprocess: RGB -> Tensor -> Normalize
        image_rgb = cv2.cvtColor(image_cv, cv2.COLOR_BGR2RGB)
        img_tensor = torch.from_numpy(image_rgb).permute(2, 0, 1).float() / 255.0
        img_tensor = img_tensor.unsqueeze(0).to(self.device)

        with torch.no_grad():
            # DISK returns Keypoints and Descriptors
            output = self.extractor(img_tensor, n=get_settings().sp_max_keypoints)
            # output is a list of Features objects (one per batch)
            features = output[0]
            keypoints = features.keypoints.cpu().numpy()  # (N, 2)
            descriptors = features.descriptors.cpu().numpy()  # (N, 128)
            
        return keypoints, descriptors


class FeatureFactory:
    _extractors: dict[str, BaseExtractor] = {}

    @staticmethod
    def get_extractor(mode: str) -> BaseExtractor:
        mode = mode.upper()
        if mode not in FeatureFactory._extractors:
            if mode == "SUPERPOINT" or mode == "DISK":
                FeatureFactory._extractors[mode] = DISKExtractor()
            else:
                FeatureFactory._extractors[mode] = ORBExtractor()
        return FeatureFactory._extractors[mode]
