# smoke_vlm.py
import time, torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

MODEL = "HuggingFaceTB/SmolVLM-256M-Instruct"
device = "cuda" if torch.cuda.is_available() else "cpu"
dtype = torch.bfloat16 if device == "cuda" else torch.float32

processor = AutoProcessor.from_pretrained(MODEL)
model = AutoModelForImageTextToText.from_pretrained(MODEL, torch_dtype=dtype).to(device)

image = Image.open("test.jpg").convert("RGB")
messages = [{"role": "user", "content": [
    {"type": "image"},
    {"type": "text", "text": "Describe what people are doing in this image in one sentence."},
]}]
prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
inputs = processor(text=prompt, images=[image], return_tensors="pt").to(device)

start = time.time()
out = model.generate(**inputs, max_new_tokens=60)
latency = time.time() - start

print(processor.batch_decode(out, skip_special_tokens=True)[0])
print(f"Latency: {latency:.2f}s on {device}")