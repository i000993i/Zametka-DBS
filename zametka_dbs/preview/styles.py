import re

def _preview_css(dark: bool = True) -> str:
    if dark:
        bg = "#11111b"; fg = "#cdd6f4"; fg2 = "#a6adc8"; border = "#313244"
        code_bg = "#313244"; code_fg = "#fab387"; pre_bg = "#181825"
        block_border = "#89b4fa"; block_fg = "#a6adc8"; block_bg = "rgba(137, 180, 250, 0.03)"
        link = "#89b4fa"; link_hover = "#b4befe"
        del_fg = "#6c7086"
        tag_fg = "#fab387"; tag_bg = "rgba(250, 179, 135, 0.1)"
        wl_fg = "#b4befe"; wl_bg = "rgba(180, 190, 254, 0.08)"; wl_bg_hover = "rgba(180, 190, 254, 0.18)"
        callout_border = "#89b4fa"; callout_bg = "rgba(137, 180, 250, 0.06)"; callout_title = "#89b4fa"
        th_bg = "#313244"; th_fg = "#a6adc8"; td_fg = "#cdd6f4"
        empty_fg = "#585b70"
    else:
        bg = "#ffffff"; fg = "#333333"; fg2 = "#666666"; border = "#e0e0e0"
        code_bg = "#f0f0f0"; code_fg = "#c7254e"; pre_bg = "#f8f8f8"
        block_border = "#4a9eff"; block_fg = "#666666"; block_bg = "rgba(74, 158, 255, 0.04)"
        link = "#4a9eff"; link_hover = "#2563eb"
        del_fg = "#aaaaaa"
        tag_fg = "#c7254e"; tag_bg = "rgba(199, 37, 78, 0.08)"
        wl_fg = "#4a9eff"; wl_bg = "rgba(74, 158, 255, 0.08)"; wl_bg_hover = "rgba(74, 158, 255, 0.18)"
        callout_border = "#4a9eff"; callout_bg = "rgba(74, 158, 255, 0.04)"; callout_title = "#4a9eff"
        th_bg = "#f0f0f0"; th_fg = "#666666"; td_fg = "#333333"
        empty_fg = "#aaaaaa"

    return f"""<style>
  body {{
    font-family: "Segoe UI Variable Display", "Segoe UI", -apple-system, sans-serif;
    font-size: 14px;
    line-height: 1.7;
    color: {fg};
    background-color: {bg};
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
  }}
  h1 {{ font-size: 26px; font-weight: 700; color: {fg}; margin: 0 0 8px 0; padding-bottom: 6px; border-bottom: 1px solid {border}; }}
  h2 {{ font-size: 20px; font-weight: 600; color: {fg}; margin: 20px 0 6px 0; }}
  h3 {{ font-size: 16px; font-weight: 600; color: {fg2}; margin: 16px 0 4px 0; }}
  h4 {{ font-size: 14px; font-weight: 600; color: {fg2}; margin: 12px 0 4px 0; }}
  p {{ margin: 0 0 10px 0; }}
  strong {{ color: {fg}; font-weight: 700; }}
  em {{ color: {fg2}; font-style: italic; }}
  code {{
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 13px;
    background: {code_bg};
    color: {code_fg};
    padding: 2px 6px;
    border-radius: 4px;
  }}
  pre {{
    background: {pre_bg};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 14px;
    overflow-x: auto;
    margin: 10px 0;
  }}
  pre code {{
    background: transparent;
    padding: 0;
    border-radius: 0;
    color: {code_fg};
  }}
  blockquote {{
    border-left: 3px solid {block_border};
    margin: 10px 0;
    padding: 6px 16px;
    color: {block_fg};
    background: {block_bg};
    border-radius: 0 4px 4px 0;
  }}
  ul, ol {{ padding-left: 24px; margin: 6px 0; }}
  li {{ margin: 2px 0; }}
  a {{ color: {link}; text-decoration: underline; }}
  a:hover {{ color: {link_hover}; }}
  hr {{ border: none; border-top: 1px solid {border}; margin: 16px 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
  th, td {{ border: 1px solid {border}; padding: 6px 12px; text-align: left; }}
  th {{ background: {th_bg}; color: {th_fg}; font-weight: 600; }}
  td {{ color: {td_fg}; }}
  del {{ color: {del_fg}; text-decoration: line-through; }}
  .tag {{
    color: {tag_fg};
    font-size: 12px;
    padding: 1px 6px;
    background: {tag_bg};
    border-radius: 10px;
  }}
  .wikilink {{
    color: {wl_fg};
    background: {wl_bg};
    padding: 1px 6px;
    border-radius: 4px;
    text-decoration: none;
  }}
  .wikilink:hover {{ background: {wl_bg_hover}; }}
  .callout {{
    border-left: 3px solid {callout_border};
    background: {callout_bg};
    border-radius: 4px;
    padding: 10px 14px;
    margin: 12px 0;
  }}
  .callout-title {{ font-weight: 600; font-size: 13px; margin-bottom: 4px; color: {callout_title}; }}
  img {{ max-width: 100%; border-radius: 4px; }}
</style>"""


PREVIEW_CSS = _preview_css(dark=True)


def empty_preview(dark: bool = True):
    empty_fg = "#585b70" if dark else "#aaaaaa"
    return _preview_css(dark) + (
        f'<p style="color: {empty_fg}; text-align: center; '
        'margin-top: 40px;">Open a note to preview</p>'
    )


def process_tags(html: str) -> str:
    return re.sub(
        r"(?:^|(?<=[\s\(>]))#([\w\-/]+)",
        r'<span class="tag">#\1</span>',
        html,
        flags=re.MULTILINE,
    )


def process_callouts(html: str) -> str:
    html = re.sub(
        r'<blockquote>\s*<p>\[!(\w+)\]\s*(.*?)</p></blockquote>',
        lambda m: f'<div class="callout"><div class="callout-title">{m.group(1)}</div><p>{m.group(2)}</p></div>',
        html,
    )
    return html
