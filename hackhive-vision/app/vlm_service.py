# app/vlm_service.py
import os
import time
from typing import Optional

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText

MODEL_ID = os.getenv("VLM_MODEL", "HuggingFaceTB/SmolVLM-256M-Instruct")
MAX_IMAGE_SIDE = 384

_processor = None
_model = None
_device = "cuda" if torch.cuda.is_available() else "cpu"
latencies_s: list[float] = []  # every successful call, for the evaluation report


def _load():
    global _processor, _model
    if _model is None:
        _processor = AutoProcessor.from_pretrained(MODEL_ID, do_image_splitting=False)
        dtype = torch.bfloat16 if _device == "cuda" else torch.float32
        _model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, dtype=dtype).to(_device)
        _model.eval()


def _generate(frame_path: str, prompt: str, max_new_tokens: int) -> str:
    _load()
    image = Image.open(frame_path).convert("RGB")
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    messages = [{"role": "user", "content": [
        {"type": "image"},
        {"type": "text", "text": prompt},
    ]}]
    text = _processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = _processor(text=text, images=[image], return_tensors="pt").to(_device)
    start = time.time()
    with torch.no_grad():
        out = _model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
    latencies_s.append(time.time() - start)
    new_tokens = out[:, inputs["input_ids"].shape[1]:]
    return _processor.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()


def describe_frame(frame_path: str,
                   prompt: str = "Describe what people are doing in this image in one sentence."
                   ) -> Optional[str]:
    """One-sentence scene description, or None if the VLM failed."""
    try:
        return _generate(frame_path, prompt, max_new_tokens=60)
    except Exception as e:
        print(f"[vlm_service] describe_frame failed: {e}")
        return None


# One yes/no question per category. Small VLMs are far more reliable at
# yes/no than at free-form JSON.
VERIFY_QUESTIONS = {
    "person_down": "Is there a person lying on the ground or floor? Answer yes or no.",
    "crowd_incident": "Is there a large crowd of people gathered closely together? Answer yes or no.",
    "tailgating": "Are two people passing through a doorway or gate together, one right behind the other? Answer yes or no.",
}


def verify_event(frame_path: str, category: str) -> Optional[bool]:
    """True/False = VLM agrees/disagrees with the rule. None = VLM failed or unclear."""
    question = VERIFY_QUESTIONS.get(category)
    if question is None:
        return None
    try:
        answer = _generate(frame_path, question, max_new_tokens=5).lower()
    except Exception as e:
        print(f"[vlm_service] verify_event failed: {e}")
        return None
    if answer.startswith("yes"):
        return True
    if answer.startswith("no"):
        return False
    return None