import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.emotion_model import _find_emotion_weights, get_emotion_model

wp = _find_emotion_weights()
print("Weights found:", wp if wp else "NOT FOUND")

em = get_emotion_model()
print("Demo mode:", em.demo_mode)
print("Weights loaded:", getattr(em, 'weights_loaded', False) if hasattr(em, 'weights_loaded') else not em.demo_mode)

# Also check if emotion_cnn.pth exists anywhere
import glob
found = glob.glob("C:/Users/acer/**/*emotion*.pth", recursive=True) + \
        glob.glob("C:/Users/acer/**/emotion_cnn.pth", recursive=True)
print("emotion_cnn.pth locations:", found if found else "NOT FOUND ANYWHERE")
