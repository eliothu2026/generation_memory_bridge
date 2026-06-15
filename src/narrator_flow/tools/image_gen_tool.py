"""Pluggable image-generation tool.

This is a STUB implementation. The actual image generation backend
(DALL-E / GPT-Image / Stable Diffusion / etc.) is TBD. The interface is
designed so that swapping in a real backend only requires rewriting the
body of `_run` -- callers (the Flow) don't need to change.
"""

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ImageGenInput(BaseModel):
    prompt: str = Field(..., description="English image-generation prompt")
    output_path: str = Field(..., description="Where to save the generated image")


class ImageGenerationTool(BaseTool):
    """Generates an image from a text prompt.

    TODO: replace the stub `_run` body with a real call to an image
    generation API, e.g.:

        from openai import OpenAI
        client = OpenAI()
        result = client.images.generate(model="dall-e-3", prompt=prompt, ...)
        # download/save result to output_path

    or a Stable Diffusion pipeline / other provider.
    """

    name: str = "generate_anchor_image"
    description: str = (
        "Generates an image from an English text prompt describing a "
        "narrative anchor object, and saves it to output_path. "
        "Currently a STUB -- the real image-generation backend is TBD."
    )
    args_schema: type[BaseModel] = ImageGenInput

    def _run(self, prompt: str, output_path: str) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "[STUB IMAGE - no real image generation backend configured yet]\n"
            f"Prompt: {prompt}\n",
            encoding="utf-8",
        )
        return f"Image (stub) saved to {output_path}"
