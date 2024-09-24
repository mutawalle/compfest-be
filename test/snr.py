import librosa
import numpy as np


def compute_snr(audio, sr, frame_length=1024, hop_length=512):
    stft = librosa.stft(audio, n_fft=frame_length, hop_length=hop_length)
    power_spec = np.abs(stft)**2
    signal_power = np.mean(power_spec, axis=0)
    noise_power = np.median(power_spec, axis=0)
    snr = 10 * np.log10(signal_power / noise_power)
    
    return snr


audio, ser = librosa.load("tes.wav", sr=None)
snr_values = compute_snr(audio, ser)
print(snr_values)