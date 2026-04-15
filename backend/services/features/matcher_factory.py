from __future__ import annotations
import abc
import numpy as np
import torch
import kornia.feature as KF

from backend.utils.config import get_settings


class BaseMatcher(abc.ABC):
    @abc.abstractmethod
    def match(self, desc1: np.ndarray, desc2: np.ndarray, kpts1: np.ndarray | None = None, kpts2: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Returns (matches_idx1, matches_idx2)"""
        pass


class RatioMatcher(BaseMatcher):
    def __init__(self, ratio: float = 0.85):
        self.ratio = ratio

    def match(self, desc1: np.ndarray, desc2: np.ndarray, kpts1: np.ndarray | None = None, kpts2: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        import faiss
        if desc1.shape[0] == 0 or desc2.shape[0] == 0:
            return np.empty(0, dtype=int), np.empty(0, dtype=int)
        
        index = faiss.IndexFlatL2(desc2.shape[1])
        index.add(desc2.astype(np.float32))
        distances, indices = index.search(desc1.astype(np.float32), 2)
        
        valid = []
        for i, dists in enumerate(distances):
            if dists[0] < self.ratio * dists[1]:
                valid.append(i)
        
        idx1 = np.array(valid, dtype=int)
        idx2 = indices[valid, 0]
        return idx1, idx2


class LightGlueMatcher(BaseMatcher):
    def __init__(self):
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        # Initialize LightGlue for DISK
        self.matcher = KF.LightGlue(features='disk').to(self.device).eval()

    def match(self, desc1: np.ndarray, desc2: np.ndarray, kpts1: np.ndarray | None = None, kpts2: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        if desc1.shape[0] == 0 or desc2.shape[0] == 0:
            return np.empty(0, dtype=int), np.empty(0, dtype=int)
        
        # LightGlue expects features in a specific format
        # Normally (B, N, D)
        d1 = torch.from_numpy(desc1).unsqueeze(0).to(self.device)
        d2 = torch.from_numpy(desc2).unsqueeze(0).to(self.device)
        k1 = torch.from_numpy(kpts1).unsqueeze(0).to(self.device)
        k2 = torch.from_numpy(kpts2).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.matcher(
                {'keypoints': k1, 'descriptors': d1},
                {'keypoints': k2, 'descriptors': d2}
            )
            matches = output['matches'][0].cpu().numpy()  # (M, 2)
        
        if matches.shape[0] == 0:
            return np.empty(0, dtype=int), np.empty(0, dtype=int)
            
        return matches[:, 0].astype(int), matches[:, 1].astype(int)


class MatcherFactory:
    @staticmethod
    def get_matcher(mode: str) -> BaseMatcher:
        mode = mode.upper()
        if mode == "SUPERPOINT":
            return LightGlueMatcher()
        else:
            return RatioMatcher()
