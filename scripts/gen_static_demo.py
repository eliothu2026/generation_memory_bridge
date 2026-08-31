"""把 demo 数据内联进静态模板,生成 0 依赖、可双击打开的 静态demo_快速体验.html。

产物 静态demo_快速体验.html 完全自包含:数据内联(不 fetch)、无 CDN、无构建、无后端——
镜像完整前端的"离线大槐树"流程,给人在装完整项目前先快速感受交互。

依赖 frontend/public/demo_script.json(由 scripts/gen_demo_script.py 生成)。
用法:python scripts/gen_static_demo.py
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "scripts" / "demo.template.html"
DEMO_JSON = REPO_ROOT / "frontend" / "public" / "demo_script.json"
PIC = REPO_ROOT / "scripts" / "startup_pic.jpg"
OUT = REPO_ROOT / "静态demo_快速体验.html"
PLACEHOLDER = "__DEMO_DATA__"


def main() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    data = json.loads(DEMO_JSON.read_text(encoding="utf-8"))
    # 紧凑内联;转义 </script> 以防提前闭合(数据里目前没有,防御性处理)
    inline = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    if PLACEHOLDER not in template:
        raise SystemExit(f"模板缺少占位符 {PLACEHOLDER}")
    html = template.replace(PLACEHOLDER, inline)
    # 内联启动图(压缩版 JPEG → data URI),保持 0 依赖单文件
    if "__STARTUP_PIC__" in html:
        if PIC.exists():
            b64 = base64.b64encode(PIC.read_bytes()).decode("ascii")
            html = html.replace("__STARTUP_PIC__", "data:image/jpeg;base64," + b64)
        else:
            html = html.replace("__STARTUP_PIC__", "")
            print(f"⚠️  未找到 {PIC.name},启动图占位已置空")
    OUT.write_text(html, encoding="utf-8")

    kb = OUT.stat().st_size / 1024
    print(f"✅ 写出 {OUT.relative_to(REPO_ROOT)}  ({kb:.1f} KB, 内联 {len(data['steps'])} 步)")
    print("   双击打开即可(无需 npm / 后端 / 网络)。")


if __name__ == "__main__":
    main()
