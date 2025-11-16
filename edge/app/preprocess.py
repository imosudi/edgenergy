import numpy as np
from scipy import signal

def extract_features_from_ct(ct_samples, sample_rate=50, n_fft=128):
    arr = np.array(ct_samples, dtype=np.float32)
    if arr.size == 0:
        return np.zeros(64, dtype=np.float32)

    if arr.size >= n_fft:
        window = arr[:n_fft]
    else:
        window = np.pad(arr, (0, n_fft - arr.size))

    f = np.abs(np.fft.rfft(window))[:64]
    stats = np.array([window.mean(), window.std(), window.max(), window.min()], dtype=np.float32)
    feat = np.concatenate([f, stats])
    feat = (feat - feat.mean()) / (feat.std() + 1e-6)
    return feat.astype(np.float32)
