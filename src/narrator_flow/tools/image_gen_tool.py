"""生图工具（STUB，无框架依赖）。

当前为占位实现：真实生图后端（DALL·E / GPT-Image / Stable Diffusion 等）待定。
接口设计成"换后端只需改 run() 内部"，调用方（流水线）无需改动。

历史说明：早期曾继承 crewai.tools.BaseTool，但实际是被流水线直接 .run() 调用、
并非由 agent 自主调用，所以方案3 去 CrewAI 时改回了无依赖的普通类。
"""

from pathlib import Path


class ImageGenerationTool:
    """从英文提示词生成图像并保存到 output_path。当前为 STUB（写占位文件）。

    TODO: 把 run() 内部替换为真实生图 API，例如：
        from openai import OpenAI
        client = OpenAI()
        result = client.images.generate(model="dall-e-3", prompt=prompt, ...)
        # 下载并保存到 output_path
    """

    name = "generate_anchor_image"

    def run(self, prompt: str, output_path: str) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "[STUB IMAGE - no real image generation backend configured yet]\n"
            f"Prompt: {prompt}\n",
            encoding="utf-8",
        )
        return f"Image (stub) saved to {output_path}"
