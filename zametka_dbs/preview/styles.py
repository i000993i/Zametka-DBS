import re

PREVIEW_CSS = """
<style>
  body {
    font-family: "Segoe UI Variable Display", "Segoe UI", -apple-system, sans-serif;
    font-size: 14px;
    line-height: 1.7;
    color: #cdd6f4;
    background-color: #11111b;
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
  }
  h1 { font-size: 26px; font-weight: 700; color: #cdd6f4; margin: 0 0 8px 0; padding-bottom: 6px; border-bottom: 1px solid #313244; }
  h2 { font-size: 20px; font-weight: 600; color: #cdd6f4; margin: 20px 0 6px 0; }
  h3 { font-size: 16px; font-weight: 600; color: #a6adc8; margin: 16px 0 4px 0; }
  h4 { font-size: 14px; font-weight: 600; color: #a6adc8; margin: 12px 0 4px 0; }
  p { margin: 0 0 10px 0; }
  strong { color: #cdd6f4; font-weight: 700; }
  em { color: #a6adc8; font-style: italic; }
  code {
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 13px;
    background: #313244;
    color: #fab387;
    padding: 2px 6px;
    border-radius: 4px;
  }
  pre {
    background: #181825;
    border: 1px solid #313244;
    border-radius: 6px;
    padding: 14px;
    overflow-x: auto;
    margin: 10px 0;
  }
  pre code {
    background: transparent;
    padding: 0;
    border-radius: 0;
    color: #fab387;
  }
  blockquote {
    border-left: 3px solid #89b4fa;
    margin: 10px 0;
    padding: 6px 16px;
    color: #a6adc8;
    background: rgba(137, 180, 250, 0.03);
    border-radius: 0 4px 4px 0;
  }
  ul, ol { padding-left: 24px; margin: 6px 0; }
  li { margin: 2px 0; }
  a { color: #89b4fa; text-decoration: underline; }
  a:hover { color: #b4befe; }
  hr { border: none; border-top: 1px solid #313244; margin: 16px 0; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; }
  th, td { border: 1px solid #313244; padding: 6px 12px; text-align: left; }
  th { background: #313244; color: #a6adc8; font-weight: 600; }
  td { color: #cdd6f4; }
  del { color: #6c7086; text-decoration: line-through; }
  .tag {
    color: #fab387;
    font-size: 12px;
    padding: 1px 6px;
    background: rgba(250, 179, 135, 0.1);
    border-radius: 10px;
  }
  .wikilink {
    color: #b4befe;
    background: rgba(180, 190, 254, 0.08);
    padding: 1px 6px;
    border-radius: 4px;
    text-decoration: none;
  }
  .wikilink:hover { background: rgba(180, 190, 254, 0.18); }
  .callout {
    border-left: 3px solid #89b4fa;
    background: rgba(137, 180, 250, 0.06);
    border-radius: 4px;
    padding: 10px 14px;
    margin: 12px 0;
  }
  .callout-title { font-weight: 600; font-size: 13px; margin-bottom: 4px; color: #89b4fa; }
  img { max-width: 100%; border-radius: 4px; }
</style>
"""


def empty_preview():
    return PREVIEW_CSS + (
        '<p style="color: #585b70; text-align: center; '
        'margin-top: 40px;">Open a note to preview</p>'
    )


def process_tags(html: str) -> str:
    return re.sub(
        r"(?<=[\s\(])#([\w\-/]+)",
        r'<span class="tag">#\1</span>',
        html,
    )


def process_callouts(html: str) -> str:
    html = re.sub(
        r'<blockquote>\s*<p>\[!(\w+)\]\s*(.*?)</p>',
        r'<div class="callout"><div class="callout-title">\1</div><p>\2</p>',
        html,
    )
    html = html.replace("</blockquote>", "</div>")
    return html
