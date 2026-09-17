"""Markdown -> Qt rich-text HTML, tuned for QTextDocument's HTML subset."""

from __future__ import annotations

import html
import re

import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from pygments.style import Style
from pygments.token import Comment, Generic, Keyword, Literal, Name, Number, Operator, String

from . import theme


class PaperStyle(Style):
    """Low-saturation code palette that sits on the stone surface."""

    background_color = theme.SURFACE
    styles = {
        Comment: f"italic {theme.MUTED}",
        Keyword: f"bold {theme.ACCENT_HOVER}",
        Keyword.Constant: theme.ACCENT_HOVER,
        Operator: theme.FG_SOFT,
        Name.Function: "#1F5F8B",
        Name.Class: "bold #1F5F8B",
        Name.Builtin: "#1F5F8B",
        Name.Decorator: "#7A5C2E",
        Name.Tag: theme.ACCENT_HOVER,
        Name.Attribute: "#7A5C2E",
        String: "#2F6F4E",
        String.Doc: "italic #2F6F4E",
        Number: "#7A5C2E",
        Literal: "#7A5C2E",
        Generic.Heading: f"bold {theme.FG}",
        Generic.Subheading: f"bold {theme.FG}",
        Generic.Deleted: theme.ERROR,
        Generic.Inserted: theme.SUCCESS,
    }


def _make_md(nl2br: bool) -> markdown.Markdown:
    exts: list = [
        "fenced_code",
        "tables",
        "sane_lists",
        "md_in_html",
        CodeHiliteExtension(noclasses=True, pygments_style=PaperStyle, guess_lang=False, linenums=False),
    ]
    if nl2br:
        exts.append("nl2br")
    return markdown.Markdown(extensions=exts, output_format="html")


_MD = _make_md(nl2br=False)
_MD_NL2BR = _make_md(nl2br=True)

_MONO = theme.css_font_stack(theme.MONO_FAMILIES)

# Qt ignores most block-level CSS on <pre>; a single-cell table is the reliable
# way to get a filled, bordered code block.
_CODE_BLOCK_RE = re.compile(
    r'<div class="codehilite"[^>]*><pre[^>]*>(?:<span></span>)?(?:<code[^>]*>)?(?P<code>.*?)(?:</code>)?</pre></div>',
    re.DOTALL,
)
_FENCE_LANG_RE = re.compile(r"^[ \t]*(?:```|~~~)[ \t]*\{?\.?([\w+#.-]*)", re.MULTILINE)
_PLAIN_PRE_RE = re.compile(r"<pre><code(?: class=\"(?P<lang>[^\"]*)\")?>(?P<code>.*?)</code></pre>", re.DOTALL)


def _wrap_block(code_html: str, lang: str = "") -> str:
    label = ""
    if lang:
        label = (
            f'<tr><td style="padding:4px 10px 0 10px; font-family:{_MONO}; font-size:10px; '
            f'color:{theme.MUTED_2}; letter-spacing:1px;">{html.escape(lang.upper())}</td></tr>'
        )
    return (
        f'<table width="100%" cellspacing="0" cellpadding="0" border="0" '
        f'style="margin-top:8px; margin-bottom:8px;">'
        f'<tr><td style="background-color:{theme.SURFACE}; border:1px solid {theme.BORDER_STRONG};">'
        f'<table width="100%" cellspacing="0" cellpadding="0">{label}'
        f'<tr><td style="padding:8px 10px 10px 10px;">'
        f'<pre style="font-family:{_MONO}; font-size:12.5px; margin:0; '
        f'white-space:pre-wrap; color:{theme.FG};">{code_html}</pre></td></tr></table></td></tr></table>'
    )


def render(md_text: str, keep_newlines: bool = False) -> str:
    md = _MD_NL2BR if keep_newlines else _MD
    md.reset()
    # Every opening fence is followed by a closing one; keep the openers only.
    langs = _FENCE_LANG_RE.findall(md_text)[::2]
    body = md.convert(md_text)

    lang_iter = iter(langs)

    def repl_hilite(m: re.Match) -> str:
        return _wrap_block(m.group("code"), next(lang_iter, ""))

    body = _CODE_BLOCK_RE.sub(repl_hilite, body)

    def repl_plain(m: re.Match) -> str:
        lang = (m.group("lang") or "").replace("language-", "")
        return _wrap_block(m.group("code"), lang)

    body = _PLAIN_PRE_RE.sub(repl_plain, body)

    # Inline code: Qt supports background-color on spans.
    body = re.sub(
        r"<code>(.*?)</code>",
        rf'<span style="font-family:{_MONO}; font-size:12.5px; background-color:{theme.SURFACE_2}; '
        rf'color:{theme.FG};">&#8202;\1&#8202;</span>',
        body,
        flags=re.DOTALL,
    )
    # Tables: Qt needs explicit border/cellpadding attributes.
    body = body.replace(
        "<table>",
        f'<table cellspacing="0" cellpadding="7" border="1" style="border-collapse:collapse; '
        f'border-style:solid; border-color:{theme.BORDER_STRONG}; margin-top:6px; margin-bottom:10px;">',
    )
    body = body.replace("<th>", f'<th style="background-color:{theme.SURFACE}; text-align:left;">')
    body = re.sub(
        r"<blockquote>(.*?)</blockquote>",
        lambda m: (
            f'<table cellspacing="0" cellpadding="0" width="100%" style="margin-top:6px; margin-bottom:10px;">'
            f'<tr><td style="border-left:3px solid {theme.BORDER_STRONG}; padding-left:14px; '
            f'color:{theme.FG_SOFT};">{m.group(1)}</td></tr></table>'
        ),
        body,
        flags=re.DOTALL,
    )
    body = re.sub(
        r"<hr\s*/?>",
        f'<hr style="color:{theme.BORDER_STRONG}; background-color:{theme.BORDER_STRONG}; margin-top:12px; margin-bottom:12px;" />',
        body,
    )
    body = re.sub(r"<a href=", f'<a style="color:{theme.ACCENT}; text-decoration:none;" href=', body)
    return body


def document_css() -> str:
    """Default stylesheet applied to every message QTextDocument."""
    ui = theme.css_font_stack(theme.FONT_FAMILIES)
    return f"""
    body {{ font-family: {ui}; font-size: 14px; color: {theme.FG}; line-height: 1.6; }}
    p {{ margin-top: 0; margin-bottom: 10px; line-height: 1.6; }}
    h1 {{ font-size: 20px; font-weight: 600; margin-top: 14px; margin-bottom: 8px; letter-spacing: -0.4px; }}
    h2 {{ font-size: 17px; font-weight: 600; margin-top: 14px; margin-bottom: 6px; letter-spacing: -0.3px; }}
    h3 {{ font-size: 15px; font-weight: 600; margin-top: 12px; margin-bottom: 6px; }}
    h4, h5, h6 {{ font-size: 14px; font-weight: 600; margin-top: 10px; margin-bottom: 4px; }}
    ul, ol {{ margin-top: 2px; margin-bottom: 8px; -qt-list-indent: 1; }}
    li {{ margin-top: 2px; margin-bottom: 3px; line-height: 1.55; }}
    th {{ font-weight: 600; }}
    td, th {{ padding: 4px 8px; }}
    strong {{ font-weight: 600; }}
    """


def plain_to_html(text: str) -> str:
    """User messages: escape, keep line breaks, no markdown surprises."""
    return "<p>" + html.escape(text).replace("\n", "<br/>") + "</p>"
