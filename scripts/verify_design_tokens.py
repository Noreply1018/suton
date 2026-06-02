from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GLOBALS = ROOT / "frontend" / "app" / "globals.css"
TAILWIND = ROOT / "frontend" / "tailwind.config.ts"
PAGE = ROOT / "frontend" / "app" / "page.tsx"
PACKAGE = ROOT / "frontend" / "package.json"

TOKENS = {
    "--color-page-bg": "#f7f6f1",
    "--color-paper-bg": "#fffefa",
    "--color-text-main": "#1f2933",
    "--color-text-muted": "#667085",
    "--color-text-subtle": "#8a9488",
    "--color-line": "#d8ddd2",
    "--color-accent": "#2f6f4e",
    "--color-accent-hover": "#285f43",
    "--color-accent-soft": "#e7f0e8",
    "--color-warning": "#b54708",
    "--color-danger": "#b42318",
    "--color-info": "#3b5b7a",
}

FONT_CLASSES = {
    "page-title": ("22px", "30px"),
    "section-title": ("16px", "24px"),
    "body": ("14px", "22px"),
    "assist": ("12px", "18px"),
    "label": ("11px", "16px"),
}

FORBIDDEN_UI_LIBS = {
    "@mui/material",
    "@chakra-ui/react",
    "antd",
    "semantic-ui-react",
    "react-bootstrap",
    "@mantine/core",
    "@nextui-org/react",
}

REQUIRED_COMPONENTS = {
    "Button": "按钮组件",
    "IconButton": "图标按钮组件",
    "TextInput": "单行输入组件",
    "Textarea": "多行输入组件",
    "Select": "选择器组件",
    "SegmentedControl": "分段控件组件",
    "StatusPill": "状态标签组件",
    "EmptyState": "空状态组件",
    "Dialog": "对话框组件",
    "Sheet": "抽屉/阅读面板组件",
    "ListRow": "列表行组件",
    "Toolbar": "工具栏组件",
    "ProgressRail": "进度轨组件",
    "SourceResult": "来源结果组件",
    "PdfReaderShell": "PDF 阅读壳组件",
}


def fail(message: str) -> None:
    print(f"design token verification failed: {message}", file=sys.stderr)
    raise SystemExit(1)


def read(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def check_globals(css: str) -> None:
    for name, value in TOKENS.items():
        pattern = rf"{re.escape(name)}\s*:\s*{re.escape(value)}\s*;"
        if not re.search(pattern, css):
            fail(f"{name} must be exposed as {value} in frontend/app/globals.css")
    if "background: var(--color-page-bg);" not in css:
        fail("body background must use --color-page-bg")
    if "font-family: Inter, ui-sans-serif, system-ui" not in css:
        fail("body must use the fixed system sans font stack")
    if re.search(r"font-size\s*:\s*[^;]*(vw|vh|vmin|vmax)", css):
        fail("font-size must not use viewport units")


def check_tailwind(config: str) -> None:
    for name in TOKENS:
        if f"var({name})" not in config:
            fail(f"tailwind config must map {name}")
    for class_name, (size, line_height) in FONT_CLASSES.items():
        quoted_key = re.escape(f'"{class_name}"')
        bare_key = re.escape(class_name)
        pattern = rf"(?:{quoted_key}|{bare_key})\s*:\s*\[\s*\"{re.escape(size)}\"\s*,\s*\"{re.escape(line_height)}\"\s*\]"
        if not re.search(pattern, config):
            fail(f"tailwind fontSize {class_name} must be {size}/{line_height}")
    if "var(--radius-control)" not in config or "var(--radius-card)" not in config:
        fail("tailwind border radius tokens must use CSS custom properties")
    if "var(--shadow-floating)" not in config:
        fail("tailwind floating shadow token must use CSS custom property")


def check_page(page: str) -> None:
    if 'from "lucide-react"' not in page:
        fail("page must use lucide-react icons")
    if re.search(r"<svg[\s>]", page):
        fail("hand-written svg icons are not allowed")
    forbidden_font_classes = re.findall(r"\btext-\[(?:[^\]]*(?:vw|vh|vmin|vmax)[^\]]*)\]", page)
    if forbidden_font_classes:
        fail("font size must not use viewport units in page.tsx")
    icon_sizes = {int(match) for match in re.findall(r"size=\{(\d+)\}", page)}
    invalid_sizes = sorted(size for size in icon_sizes if size not in {16, 18})
    if invalid_sizes:
        fail(f"lucide icon sizes must be 16 or 18 px, got {invalid_sizes}")
    sized_icon_tags = re.findall(r"<[A-Z][A-Za-z0-9]*\b[^>]*\bsize=\{(?:16|18)\}[^>]*/?>", page)
    missing_stroke_width = [tag for tag in sized_icon_tags if "strokeWidth={1.75}" not in tag]
    if missing_stroke_width:
        fail("lucide icons with fixed size must set strokeWidth={1.75}")
    for component, description in REQUIRED_COMPONENTS.items():
        definition_pattern = rf"(?:function\s+{re.escape(component)}\b|const\s+{re.escape(component)}\s*=)"
        if not re.search(definition_pattern, page):
            fail(f"missing {description}: {component}")
        usage_pattern = rf"<{re.escape(component)}(?:\s|>|/)"
        if not re.search(usage_pattern, page):
            fail(f"{description} must be used in page.tsx: {component}")


def check_package() -> None:
    package = json.loads(read(PACKAGE))
    dependencies = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))
    forbidden = sorted(dependencies & FORBIDDEN_UI_LIBS)
    if forbidden:
        fail(f"main UI component libraries are not allowed: {', '.join(forbidden)}")


def main() -> None:
    check_globals(read(GLOBALS))
    check_tailwind(read(TAILWIND))
    check_page(read(PAGE))
    check_package()
    print("v0.2.0 design token source verification passed")


if __name__ == "__main__":
    main()
