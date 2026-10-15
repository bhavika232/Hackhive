import platform, sys, torch

print("OS:", platform.platform())
print("Python:", sys.version.split()[0])
print("Torch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print("GPU:", p.name)
    print("VRAM (GB):", round(p.total_memory / 1e9, 1))
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    print("Apple MPS available")
else:
    print("No GPU backend, CPU only")