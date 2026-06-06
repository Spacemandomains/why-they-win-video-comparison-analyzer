"""Vision LLM integration. Supports Gemini (free) and OpenAI for frame analysis."""

import base64
import os
import time
from pathlib import Path
from typing import Optional


class VisionAnalyzer:
    """Analyze video frames using vision LLMs."""

    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None, model: Optional[str] = None):
        self.provider = provider.lower()
        
        if self.provider == "gemini":
            self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
            self.model = model or "gemini-2.0-flash"
            self._init_gemini()
        elif self.provider == "openai":
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
            self.model = model or "gpt-4o"
            self._init_openai()
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'gemini' or 'openai'.")

    def _init_gemini(self):
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        self._genai = genai
        self._model = genai.GenerativeModel(self.model)

    def _init_openai(self):
        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key)

    def analyze_frame(self, image_path: str, prompt: str, context: str = "") -> str:
        """Analyze a single frame with optional context from previous frames."""
        full_prompt = prompt
        if context:
            full_prompt = f"Previous context from earlier in the video:\n{context}\n\nNow analyze this frame:\n{prompt}"

        if self.provider == "gemini":
            return self._analyze_gemini(image_path, full_prompt)
        elif self.provider == "openai":
            return self._analyze_openai(image_path, full_prompt)

    def _analyze_gemini(self, image_path: str, prompt: str) -> str:
        import PIL.Image
        img = PIL.Image.open(image_path)
        response = self._model.generate_content([prompt, img])
        return response.text

    def _analyze_openai(self, image_path: str, prompt: str) -> str:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }],
            max_tokens=1024,
        )
        return response.choices[0].message.content

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
            # Build context from previous analyses
            context = ""
            if context_history:
                recent = context_history[-context_window:]
                context = "\n".join(
                    f"[{h['timestamp']:.1f}s] {h['analysis'][:200]}"
                    for h in recent
                )

            # Add timestamp info to prompt
            ts = frame.get("timestamp", 0)
            frame_prompt = f"Video timestamp: {ts:.1f}s (frame {i+1}/{len(frames)})\n\n{prompt}"

            try:
                analysis = self.analyze_frame(frame["path"], frame_prompt, context)
            except Exception as e:
                analysis = f"[Error: {e}]"

            result = {
                **frame,
                "analysis": analysis,
                "index": i,
            }
            results.append(result)
            context_history.append({"timestamp": ts, "analysis": analysis})

            if progress_callback:
                progress_callback(i + 1, len(frames), result)

            # Rate limiting
            if i < len(frames) - 1 and delay > 0:
                time.sleep(delay)

        return results


def summarize_frames(frame_analyses: list[dict], provider: str = "gemini", api_key: str = "", model: str = None) -> str:
    """Generate a coherent video summary from frame analyses."""
    if not frame_analyses:
        return "No frames to summarize."

    # Build analysis text
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

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model or "gemini-2.0-flash")
        response = model_obj.generate_content(summary_prompt)
        return response.text
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model or "gpt-4o",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=2048,
        )
        return response.choices[0].message.content


def detect_chapters(frame_analyses: list[dict], provider: str = "gemini", api_key: str = "", model: str = None) -> list[dict]:
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

Return ONLY valid JSON, no markdown."""

    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model or "gemini-2.0-flash")
        response = model_obj.generate_content(chapter_prompt)
        text = response.text
    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model or "gpt-4o",
            messages=[{"role": "user", "content": chapter_prompt}],
            max_tokens=1024,
        )
        text = response.choices[0].message.content

    # Parse JSON from response
    import json
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    
    try:
        chapters = json.loads(text)
        return chapters
    except json.JSONDecodeError:
        return [{"start": 0, "end": 0, "title": "Parse Error", "description": text[:200]}]
