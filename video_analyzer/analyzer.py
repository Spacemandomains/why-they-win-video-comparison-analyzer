"""Vision LLM integration. Supports Gemini, OpenAI, Anthropic, and Ollama."""

import base64
import json
import os
import time
from typing import Optional


class VisionAnalyzer:
    """Analyze video frames using vision LLMs. Supports 4 providers."""

    SUPPORTED_PROVIDERS = ["gemini", "openai", "anthropic", "ollama"]

    def __init__(self, provider: str = "gemini", api_key: str = "", model: Optional[str] = None):
        self.provider = provider.lower()
        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Unknown provider: {self.provider}. "
                f"Supported: {', '.join(self.SUPPORTED_PROVIDERS)}"
            )

        self.api_key = api_key
        self.model = model
        self._init_provider()

    def _init_provider(self):
        """Initialize the selected provider client."""
        if self.provider == "gemini":
            self.model = self.model or "gemini-2.0-flash"
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai
            self._model = genai.GenerativeModel(self.model)

        elif self.provider == "openai":
            self.model = self.model or "gpt-4o"
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)

        elif self.provider == "anthropic":
            self.model = self.model or "claude-sonnet-4-20250514"
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)

        elif self.provider == "ollama":
            self.model = self.model or "llava:13b"
            import ollama
            self._client = ollama

    def analyze_frame(self, image_path: str, prompt: str, context: str = "") -> str:
        """Analyze a single frame with optional context from previous frames."""
        full_prompt = prompt
        if context:
            full_prompt = (
                f"Previous context from earlier in the video:\n{context}\n\n"
                f"Now analyze this frame:\n{prompt}"
            )

        dispatch = {
            "gemini": self._call_gemini,
            "openai": self._call_openai,
            "anthropic": self._call_anthropic,
            "ollama": self._call_ollama,
        }
        return dispatch[self.provider](image_path, full_prompt)

    def _call_gemini(self, image_path: str, prompt: str) -> str:
        import PIL.Image
        img = PIL.Image.open(image_path)
        response = self._model.generate_content([prompt, img])
        return response.text

    def _call_openai(self, image_path: str, prompt: str) -> str:
        b64 = _image_to_base64(image_path)
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, image_path: str, prompt: str) -> str:
        b64 = _image_to_base64(image_path)
        media_type = "image/jpeg"
        response = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        return response.content[0].text

    def _call_ollama(self, image_path: str, prompt: str) -> str:
        b64 = _image_to_base64(image_path)
        response = self._client.chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": prompt,
                "images": [b64],
            }],
        )
        return response["message"]["content"]

    def analyze_batch(
        self,
        frames: list[dict],
        prompt: str,
        context_window: int = 3,
        delay: float = 1.0,
        progress_callback=None,
    ) -> list[dict]:
        """
        Analyze multiple frames with rolling context memory.

        Args:
            frames: List of frame dicts (from extractor)
            prompt: Analysis prompt
            context_window: Number of previous frame analyses to include as context
            delay: Seconds between API calls (rate limiting)
            progress_callback: fn(current, total, result) called after each frame

        Returns:
            List of dicts with frame info + analysis
        """
        results = []
        context_history = []

        for i, frame in enumerate(frames):
            # Build rolling context
            context = ""
            if context_history:
                recent = context_history[-context_window:]
                context = "\n".join(
                    f"[{h['timestamp']:.1f}s] {h['analysis'][:200]}"
                    for h in recent
                )

            ts = frame.get("timestamp", 0)
            frame_prompt = f"Video timestamp: {ts:.1f}s (frame {i+1}/{len(frames)})\n\n{prompt}"

            try:
                analysis = self.analyze_frame(frame["path"], frame_prompt, context)
            except Exception as e:
                analysis = f"[Error: {type(e).__name__}: {e}]"

            result = {**frame, "analysis": analysis, "index": i}
            results.append(result)
            context_history.append({"timestamp": ts, "analysis": analysis})

            if progress_callback:
                progress_callback(i + 1, len(frames), result)

            # Rate limiting (skip for local Ollama)
            if i < len(frames) - 1 and delay > 0 and self.provider != "ollama":
                time.sleep(delay)

        return results


def summarize_frames(frame_analyses: list[dict], analyzer: VisionAnalyzer) -> str:
    """Generate a coherent video summary from frame analyses."""
    if not frame_analyses:
        return "No frames to summarize."

    analysis_text = "\n\n".join(
        f"[{a.get('timestamp', 0):.1f}s] {a['analysis']}"
        for a in frame_analyses
    )

    summary_prompt = f"""You are analyzing a video based on frame-by-frame descriptions.
Create a comprehensive, well-structured summary of the video content.

Frame analyses:
{analysis_text}

Provide:
1. **Title/Topic**: What the video is about
2. **Summary**: 3-5 paragraph narrative summary
3. **Key Moments**: Important timestamps and what happens
4. **Visual Style**: Description of the visual style/quality
5. **Key Takeaways**: Main points or messages

Write in a clear, engaging style."""

    return analyzer.analyze_frame(
        frame_analyses[0]["path"], summary_prompt
    )


def detect_chapters(frame_analyses: list[dict], analyzer: VisionAnalyzer) -> list[dict]:
    """Detect video chapters/sections from frame analyses."""
    if len(frame_analyses) < 3:
        return [{"start": 0, "title": "Full Video", "description": "Too few frames for chapter detection"}]

    analysis_text = "\n".join(
        f"[{a.get('timestamp', 0):.1f}s] {a['analysis'][:150]}"
        for a in frame_analyses
    )

    chapter_prompt = f"""Analyze these frame descriptions from a video and identify distinct chapters/sections.

Frame descriptions:
{analysis_text}

Return a JSON array of chapters. Each chapter should have:
- "start": timestamp in seconds
- "end": timestamp in seconds
- "title": short chapter title
- "description": one-line description

Return ONLY valid JSON, no markdown code blocks."""

    result = analyzer.analyze_frame(frame_analyses[0]["path"], chapter_prompt)

    # Parse JSON from response
    text = result.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return [{"start": 0, "end": 0, "title": "Parse Error", "description": text[:200]}]


def _image_to_base64(image_path: str) -> str:
    """Read image file and return base64 encoded string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()
