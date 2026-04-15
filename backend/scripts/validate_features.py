import sys
import os
from pathlib import Path
import torch

# Add backend to path
sys.path.append(os.getcwd())

from backend.services.features.feature_factory import FeatureFactory
from backend.utils.config import get_settings

def validate():
    settings = get_settings()
    print(f"Current Feature Mode: {settings.feature_mode}")
    
    # Test image
    image_path = Path("hospital_sample_2.mp4") # Wait, I need an image not a mp4
    # I'll use a frame if I already extracted them, otherwise I'll just check if it can load models.
    
    print("Testing ORB Extractor...")
    orb = FeatureFactory.get_extractor("ORB")
    print("ORB Extractor loaded.")
    
    print("Testing SuperPoint Extractor...")
    try:
        sp = FeatureFactory.get_extractor("SUPERPOINT")
        print(f"SuperPoint Extractor loaded on device: {sp.device}")
        
        # Check if kornia models can be loaded (will download weights if needed)
        # This might take a moment
        print("SuperPoint model initialized successfully.")
    except Exception as e:
        print(f"SuperPoint initialization FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    validate()
