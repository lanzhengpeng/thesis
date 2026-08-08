#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert extracted thesis PDF text to Markdown and LaTeX with improved formatting.
Output files share the same document structure.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXTRACTED_JSON = BASE_DIR / "extracted_text.json"
OUTPUT_MD = BASE_DIR / "thesis.md"
OUTPUT_TEX = BASE_DIR / "thesis.tex"

# Chapter starts observed in the PDF after cropping page headers
CHAPTER_INSERTIONS = {
    11: "1 绪论",
    25: "2 相关理论与技术",
    34: "3 认知对齐增强和多视角共识推理方法",
    51: "4 基于动态强化学习的检索增强生成方法",
    73: "5 多智能体协同的NL2SQL框架",
    98: "6 总结与展望",
    100: "参考文献",
    115: "致谢",
}

# Special one-line headings that should not be merged with surrounding text
STANDALONE_HEADINGS = {
    "摘要", "摘 要", "ABSTRACT", "目录", "目 录",
    "参考文献", "致谢", "攻读学位期间取得的研究成果",
}


def load_pages():
    with open(EXTRACTED_JSON, "r", encoding="utf-8") as f:
        pages = json.load(f)
    for page in pages:
        pnum = page.get("page", 0)
        if pnum in CHAPTER_INSERTIONS:
            heading = CHAPTER_INSERTIONS[pnum]
            text = page.get("text", "")
            first_lines = "\n".join(text.splitlines()[:3])
            if heading not in first_lines:
                page["text"] = heading + "\n" + text
    return pages


def strip_header_footer(text: str, page_num: int) -> str:
    """Remove standalone roman-numeral page numbers only."""
    lines = text.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if re.fullmatch(r"[IVXLC]+", s):
            continue
        out.append(line)
    return "\n".join(out)


def merge_heading_fragments(lines: list[str]) -> list[str]:
    """Merge heading fragments split across lines by PDF extraction."""
    out = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if s == "摘" and nxt == "要":
                out.append("摘要")
                i += 2
                continue
            if s == "目" and nxt == "录":
                out.append("目录")
                i += 2
                continue
            if re.match(r"^\d{1,2}\.\d{1,2}(\.\d{1,2})?$", s) and len(s) < 10 and "%" not in s:
                if re.match(r"^[一-龥A-Z]", nxt):
                    out.append(s + " " + nxt)
                    i += 2
                    continue
            if re.match(r"^\d$", s) and nxt in {
                "绪论", "相关理论与技术", "认知对齐增强和多视角共识推理方法",
                "基于动态强化学习的检索增强生成方法", "多智能体协同的NL2SQL框架",
                "多智能体协同的NL2SQL 框架", "总结与展望"
            }:
                out.append(s + " " + nxt)
                i += 2
                continue
        out.append(lines[i])
        i += 1
    return out


def split_into_blocks(pages: list[dict]) -> list[tuple[int, str]]:
    """Split each page into paragraph blocks and tag with page number."""
    result = []
    for page in pages:
        pnum = page.get("page", 0)
        text = strip_header_footer(page.get("text", ""), pnum)
        if not text.strip():
            continue
        lines = text.splitlines()
        lines = merge_heading_fragments(lines)

        # Group lines into blocks separated by blank lines
        blocks = []
        buf = []
        for line in lines:
            if line.strip() == "":
                if buf:
                    blocks.append("\n".join(buf))
                    buf = []
            else:
                buf.append(line)
        if buf:
            blocks.append("\n".join(buf))

        for b in blocks:
            result.append((pnum, b))
    return result


def classify_block(block: str, page_num: int) -> tuple[str, str]:
    """Return (type, content) for a block."""
    s = block.strip()
    if not s:
        return ("empty", "")

    lines = s.splitlines()
    first = lines[0].strip()

    # Cover / statement pages (early pages)
    if page_num <= 3:
        return ("cover", s)

    # Standalone special headings
    if first in STANDALONE_HEADINGS or first.replace(" ", "") in STANDALONE_HEADINGS:
        return ("heading", first.replace(" ", ""))

    # Table of contents page
    if "目 录" in first or "目录" in first or re.search(r"\.{4,}", s):
        toc_like = sum(1 for line in lines if re.search(r"\.{4,}", line))
        if toc_like >= 3 or "目录" in first:
            return ("toc", s)

    # Statement pages
    if "学位论文原创性声明" in s or "学位论文独创性声明" in s or "学位论文使用授权声明" in s or "诚信承诺书" in s:
        return ("statement", s)

    # Headings
    if re.match(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\s+(.+)$", first):
        m = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\s+(.+)$", first)
        return ("heading", "### " + m.group(2).strip())
    if re.match(r"^(\d{1,2}\.\d{1,2})\s+(.+)$", first):
        m = re.match(r"^(\d{1,2}\.\d{1,2})\s+(.+)$", first)
        return ("heading", "## " + m.group(2).strip())
    if re.match(r"^(\d+)\s+(.+)$", first):
        m = re.match(r"^(\d+)\s+(.+)$", first)
        title = m.group(2).strip()
        if len(title) < 40 and not title.startswith("("):
            return ("heading", "# " + title)
    if re.match(r"^(\d+)([一-龥]{2,})$", first):
        m = re.match(r"^(\d+)([一-龥]{2,})$", first)
        return ("heading", "# " + m.group(2).strip())

    # Figure caption
    if re.match(r"^图\s*\d+\.\d+", first) or re.match(r"^Fig\.?\s*\d+", first, re.I):
        return ("figure", first)

    # Table caption
    if re.match(r"^表\s*\d+\.\d+", first):
        return ("table_caption", first)

    # Algorithm caption
    if re.match(r"^算法\s*\d+", first):
        return ("algorithm", s)

    return ("", "")


def is_formula_line(line: str) -> bool:
    """Heuristic: a line is formula-like if it contains many math symbols or an equation number."""
    math_chars = set("𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍𝛼𝛽𝛾𝛿𝜆𝜃𝜎𝜇𝜈𝜋𝜌𝜏𝜑𝜔𝜁𝜂𝜅𝜉𝜓ΓΔΘΛΣΦΨΩ∞∑∏∫∂∇√⋅×÷±≤≥≠≈∈∪∩→←⇒⇐⟨⟩")
    count = sum(1 for c in line if c in math_chars)
    has_eqnum = bool(re.search(r"\(\d+\.\d+\)\s*$", line.strip()))
    return count >= 3 or has_eqnum


def is_list_item(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^（\d+）|^\(\d+\)|^\d+[、．]\s|^[-•·–—]\s", s))


def is_code_line(line: str) -> bool:
    s = line.strip()
    if re.match(r"^(SELECT|FROM|WHERE|GROUP BY|ORDER BY|LIMIT|INSERT|UPDATE|DELETE|CREATE|TABLE|PRIMARY KEY|FOREIGN KEY|JOIN|INNER|LEFT|RIGHT|ON|AS)", s, re.I):
        return True
    if re.match(r"^\{.*\}$", s) or re.match(r'^".*"$', s):
        return True
    if re.match(r"^\(.*\)$", s) and any(k in s for k in ["integer", "text", "primary", "key"]):
        return True
    return False


MATH_MAP = {
    "𝜋": r"\pi", "𝛼": r"\alpha", "𝛽": r"\beta", "𝛾": r"\gamma",
    "𝛿": r"\delta", "𝜆": r"\lambda", "𝜃": r"\theta", "𝜎": r"\sigma",
    "𝜇": r"\mu", "𝜈": r"\nu", "𝜌": r"\rho", "𝜏": r"\tau",
    "𝜑": r"\varphi", "𝜔": r"\omega", "𝜁": r"\zeta", "𝜂": r"\eta",
    "𝜅": r"\kappa", "𝜉": r"\xi", "𝜓": r"\psi", "Γ": r"\Gamma",
    "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda", "Σ": r"\Sigma",
    "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega", "∞": r"\infty",
    "⋅": r"\cdot", "×": r"\times", "÷": r"\div", "±": r"\pm",
    "∓": r"\mp", "≤": r"\leq", "≥": r"\geq", "≠": r"\neq",
    "≈": r"\approx", "∈": r"\in", "∉": r"\notin", "∪": r"\cup",
    "∩": r"\cap", "⊂": r"\subset", "⊆": r"\subseteq", "⊃": r"\supset",
    "⊇": r"\supseteq", "∅": r"\emptyset", "∀": r"\forall", "∃": r"\exists",
    "∧": r"\land", "∨": r"\lor", "¬": r"\neg", "→": r"\rightarrow",
    "←": r"\leftarrow", "⇒": r"\Rightarrow", "⇐": r"\Leftarrow",
    "↔": r"\leftrightarrow", "⇔": r"\Leftrightarrow", "↑": r"\uparrow",
    "↓": r"\downarrow", "∑": r"\sum", "∏": r"\prod", "∫": r"\int",
    "∂": r"\partial", "∇": r"\nabla", "√": r"\sqrt", "…": r"\ldots",
    "⋯": r"\cdots", "⋮": r"\vdots", "⋱": r"\ddots", "′": "'", "″": "''",
    "⟨": r"\langle", "⟩": r"\rangle", "𝑑": "d", "𝔼": r"\mathbb{E}",
    "←": r"\leftarrow", "→": r"\rightarrow", "⇒": r"\Rightarrow",
}
for _c, _rep in [
    ("𝑎", "a"), ("𝑏", "b"), ("𝑐", "c"), ("𝑑", "d"), ("𝑒", "e"),
    ("𝑓", "f"), ("𝑔", "g"), ("ℎ", "h"), ("𝑖", "i"), ("𝑗", "j"),
    ("𝑘", "k"), ("𝑙", "l"), ("𝑚", "m"), ("𝑛", "n"), ("𝑜", "o"),
    ("𝑝", "p"), ("𝑞", "q"), ("𝑟", "r"), ("𝑠", "s"), ("𝑡", "t"),
    ("𝑢", "u"), ("𝑣", "v"), ("𝑤", "w"), ("𝑥", "x"), ("𝑦", "y"), ("𝑧", "z"),
    ("𝐴", "A"), ("𝐵", "B"), ("𝐶", "C"), ("𝐷", "D"), ("𝐸", "E"),
    ("𝐹", "F"), ("𝐺", "G"), ("𝐻", "H"), ("𝐼", "I"), ("𝐽", "J"),
    ("𝐾", "K"), ("𝐿", "L"), ("𝑀", "M"), ("𝑁", "N"), ("𝑂", "O"),
    ("𝑃", "P"), ("𝑄", "Q"), ("𝑅", "R"), ("𝑆", "S"), ("𝑇", "T"),
    ("𝑈", "U"), ("𝑉", "V"), ("𝑊", "W"), ("𝑋", "X"), ("𝑌", "Y"), ("𝑍", "Z"),
]:
    MATH_MAP[_c] = _rep

SUP_MAP = {
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
    "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "-",
    "⁼": "=", "⁽": "(", "⁾": ")", "ᵃ": "a", "ᵇ": "b", "ᶜ": "c",
    "ᵈ": "d", "ᵉ": "e", "ᶠ": "f", "ᵍ": "g", "ʰ": "h", "ⁱ": "i",
    "ʲ": "j", "ᵏ": "k", "ˡ": "l", "ᵐ": "m", "ⁿ": "n", "ᵒ": "o",
    "ᵖ": "p", "ʳ": "r", "ˢ": "s", "ᵗ": "t", "ᵘ": "u", "ᵛ": "v",
    "ʷ": "w", "ˣ": "x", "ʸ": "y", "ᶻ": "z",
}
SUB_MAP = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5",
    "₆": "6", "₇": "7", "₈": "8", "₉": "9", "₊": "+", "₋": "-",
    "₌": "=", "₍": "(", "₎": ")", "ₐ": "a", "ₑ": "e", "ᵢ": "i",
    "ⱼ": "j", "ₒ": "o", "ᵤ": "u", "ᵥ": "v", "ₓ": "x",
}


def unicode_to_latex_math(text: str) -> str:
    for ch, cmd in MATH_MAP.items():
        text = text.replace(ch, cmd)
    for ch, cmd in SUP_MAP.items():
        text = text.replace(ch, f"^{{{cmd}}}")
    for ch, cmd in SUB_MAP.items():
        text = text.replace(ch, f"_{{{cmd}}}")
    return text


def clean_paragraph(text: str) -> str:
    """Join broken lines in a paragraph into a single line."""
    lines = text.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if not out:
            out.append(s)
            continue
        last = out[-1]
        # Merge if previous line ends with hyphen
        if last.endswith("-") and not last.endswith("--"):
            out[-1] = last[:-1] + s
            continue
        # Merge if both sides are Latin-ish (word break across lines)
        a_end = last[-1]
        b_start = s[0]
        latin_end = a_end.isascii() and (a_end.isalnum() or a_end in ")]})%'?\"")
        latin_start = b_start.isascii() and (b_start.isalnum() or b_start in "([{'#\"")
        # Do not merge if previous line ends a sentence
        if a_end in "。；：！？.!?" or (a_end == "." and b_start.isupper()):
            out.append(s)
        elif latin_end and latin_start:
            out[-1] = last + " " + s
        else:
            out[-1] = last + s
    return "".join(out)


def classify_and_clean_block(block: str, page_num: int) -> list[tuple[str, str]]:
    """Convert one raw block into typed output lines."""
    btype, content = classify_block(block, page_num)
    if btype in ("cover", "toc", "statement", "empty"):
        return []
    if btype == "heading":
        return [("heading", content)]
    if btype == "figure":
        return [("figure", content)]
    if btype == "table_caption":
        return [("table_caption", content)]
    if btype == "algorithm":
        return [("algorithm", block)]

    # Mixed block: split into formulas / code / list / text
    lines = block.splitlines()
    out = []
    buf = []
    code_buf = []

    def flush_para():
        if buf:
            text = clean_paragraph("\n".join(buf))
            if text:
                out.append(("para", text))
            buf.clear()

    def flush_code():
        if code_buf:
            out.append(("code", "\n".join(code_buf)))
            code_buf.clear()

    for line in lines:
        s = line.rstrip()
        if not s.strip():
            flush_para()
            flush_code()
            continue

        # Inline standalone heading inside a block
        if s.strip() in STANDALONE_HEADINGS:
            flush_para()
            flush_code()
            out.append(("heading", "# " + s.strip()))
            continue

        if is_formula_line(s):
            flush_para()
            flush_code()
            out.append(("formula", s.strip()))
            continue

        if is_code_line(s):
            flush_para()
            code_buf.append(s)
            continue

        if code_buf and not is_code_line(s):
            # Maybe code block ended
            flush_code()

        if is_list_item(s):
            flush_para()
            out.append(("list", s.strip()))
            continue

        buf.append(s)

    flush_para()
    flush_code()
    return out


def process_blocks(blocks: list[tuple[int, str]]) -> list[tuple[str, str]]:
    """Process all blocks and merge paragraphs across page boundaries."""
    typed = []
    for pnum, block in blocks:
        typed.extend(classify_and_clean_block(block, pnum))

    # Merge consecutive paragraphs
    merged = []
    for btype, content in typed:
        if btype == "para" and merged and merged[-1][0] == "para":
            prev = merged[-1][1]
            # Merge if prev doesn't end sentence and content doesn't start list/heading
            if prev and prev[-1] not in "。；：！？" and not re.match(r"^（\d+）|^\(\d+\)|^\d+[、．]", content):
                merged[-1] = ("para", prev + content)
                continue
        merged.append((btype, content))
    return merged


def generate_markdown(blocks: list[tuple[str, str]]) -> str:
    out = []
    out.append("# 面向线索数据感知的多智能体SQL生成方法研究")
    out.append("")
    out.append("- **作者：** 张念龙")
    out.append("- **指导教师：** 叶荣华 教授")
    out.append("- **学校：** 浙江师范大学")
    out.append("- **专业：** 软件工程")
    out.append("- **学号：** 202320701127")
    out.append("- **提交时间：** 2026年5月25日")
    out.append("")
    out.append("> 说明：本文件由PDF自动转换生成，公式、图表、代码块已尽量保留结构，建议人工复核。")
    out.append("")

    prev_type = None
    for btype, content in blocks:
        if btype == "heading":
            out.append("")
            out.append(content)
            out.append("")
            prev_type = "heading"
        elif btype == "para":
            if prev_type == "para":
                out.append("")
            out.append(content)
            prev_type = "para"
        elif btype == "formula":
            out.append("")
            out.append(f"$${content}$$")
            out.append("")
            prev_type = "formula"
        elif btype == "code":
            out.append("")
            out.append("```")
            out.append(content)
            out.append("```")
            out.append("")
            prev_type = "code"
        elif btype == "list":
            out.append("")
            out.append(content)
            prev_type = "list"
        elif btype == "figure":
            out.append("")
            out.append(f"*{content}*")
            out.append("")
            prev_type = "figure"
        elif btype == "table_caption":
            out.append("")
            out.append(f"*{content}*")
            out.append("")
            prev_type = "table_caption"
        elif btype == "algorithm":
            out.append("")
            out.append("```")
            out.append(content)
            out.append("```")
            out.append("")
            prev_type = "algorithm"

    return "\n".join(out)


def escape_latex(text: str) -> str:
    chars = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
        "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde ",
        "^": r"\textasciicircum ",
    }
    for ch, rep in chars.items():
        text = text.replace(ch, rep)
    return text


def md_to_latex(md: str) -> str:
    lines = md.splitlines()
    body = []
    in_code = False
    in_list = False
    list_env = None  # 'enumerate' or 'itemize'

    def close_lists():
        nonlocal in_list, list_env
        if in_list:
            body.append(f"\\end{{{list_env}}}")
            in_list = False
            list_env = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if in_code:
                body.append("")
            else:
                close_lists()
            i += 1
            continue

        # Skip metadata
        if stripped.startswith("- **") or stripped.startswith("> 说明："):
            i += 1
            continue
        if stripped.startswith("# ") and "面向线索数据感知" in stripped and i < 15:
            i += 1
            continue

        if stripped.startswith("# "):
            close_lists()
            title = stripped[2:].strip()
            if title == "摘要":
                body.append(r"\chapter*{摘\quad 要}")
                body.append(r"\addcontentsline{toc}{chapter}{摘要}")
                body.append(r"\zihao{-4}")
            elif title == "ABSTRACT":
                body.append(r"\chapter*{Abstract}")
                body.append(r"\addcontentsline{toc}{chapter}{Abstract}")
                body.append(r"\zihao{-4}")
            elif title == "目录":
                body.append(r"\tableofcontents")
            elif title == "参考文献":
                body.append(r"\chapter*{参考文献}")
                body.append(r"\addcontentsline{toc}{chapter}{参考文献}")
                body.append(r"\zihao{-4}")
            elif title == "致谢":
                body.append(r"\chapter*{致\quad 谢}")
                body.append(r"\addcontentsline{toc}{chapter}{致谢}")
                body.append(r"\zihao{-4}")
            else:
                body.append(f"\\chapter{{{title}}}")
                body.append(r"\zihao{-4}")
        elif stripped.startswith("## "):
            close_lists()
            body.append(f"\\section{{{stripped[3:].strip()}}}")
        elif stripped.startswith("### "):
            close_lists()
            body.append(f"\\subsection{{{stripped[4:].strip()}}}")
        elif stripped.startswith("#### "):
            close_lists()
            body.append(f"\\subsubsection{{{stripped[5:].strip()}}}")
        elif stripped == "```":
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            else:
                close_lists()
                body.append(r"\begin{lstlisting}")
                in_code = True
        elif stripped.startswith("```"):
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            else:
                close_lists()
                body.append(r"\begin{lstlisting}")
                in_code = True
        elif stripped.startswith("*图"):
            close_lists()
            cap = stripped.strip("*").strip()
            body.append(r"\begin{figure}[htbp]")
            body.append(r"\centering")
            body.append(r"\fbox{\parbox{0.8\textwidth}{\centering \zihao{5} " + escape_latex(cap) + r"}}")
            body.append(r"\caption{" + escape_latex(cap) + r"}")
            body.append(r"\end{figure}")
        elif stripped.startswith("*表"):
            close_lists()
            cap = stripped.strip("*").strip()
            body.append(r"\begin{table}[htbp]")
            body.append(r"\centering")
            body.append(r"\caption{" + escape_latex(cap) + r"}")
            body.append(r"\fbox{\parbox{0.8\textwidth}{\centering \zihao{5} " + escape_latex(cap) + r"}}")
            body.append(r"\end{table}")
        elif stripped.startswith("$$") and stripped.endswith("$$"):
            close_lists()
            formula = stripped[2:-2].strip()
            formula = unicode_to_latex_math(formula)
            body.append(r"\begin{equation}")
            body.append(formula)
            body.append(r"\end{equation}")
        elif re.match(r"^\*\*关键词：\*\*|^\*\*Keywords:\*\*", stripped):
            close_lists()
            if "关键词" in stripped:
                body.append(r"\noindent\textbf{关键词：}" + stripped.split("关键词：", 1)[1].strip("*").strip())
            else:
                body.append(r"\noindent\textbf{Keywords:} " + stripped.split("Keywords:", 1)[1].strip("*").strip())
        elif re.match(r"^（\d+）", stripped):
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\begin{enumerate}[label=(\arabic*)]")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^（\d+）", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\(\d+\)", stripped):
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\begin{enumerate}[label=(\arabic*)]")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^\(\d+\)", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\d+[、．]\s", stripped):
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\begin{enumerate}")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^\d+[、．]\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^[-•·–—]\s", stripped):
            if not (in_list and list_env == "itemize"):
                close_lists()
                body.append(r"\begin{itemize}")
                in_list = True
                list_env = "itemize"
            item = re.sub(r"^[-•·–—]\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        else:
            if in_code:
                body.append(stripped)
            elif in_list:
                # continuation of a list item
                if body and body[-1].startswith(r"\item "):
                    body[-1] += " " + escape_latex(stripped)
                else:
                    close_lists()
                    body.append(escape_latex(stripped))
            else:
                body.append(escape_latex(stripped))
        i += 1

    close_lists()

    latex = r"""% 面向线索数据感知的多智能体SQL生成方法研究
% 作者：张念龙
% 本文件由PDF自动转换生成，公式、图表、代码块建议人工复核
\documentclass[12pt,a4paper,openright,UTF8]{ctexbook}

\usepackage{geometry}
\geometry{left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm}
\usepackage{xeCJK}
\usepackage{amsmath,amssymb,amsfonts,amsthm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{multirow}
\usepackage{array}
\usepackage{float}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{enumitem}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{listings}
\usepackage{xcolor}
\usepackage{hyperref}
\usepackage{cleveref}
\usepackage{setspace}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{tocloft}
\usepackage[numbers,sort&compress]{natbib}
\bibliographystyle{gbt7714-numerical}

\setlength{\headheight}{14pt}
\addtolength{\topmargin}{-2pt}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[C]{\small \leftmark}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\ctexset{
    chapter = {
        format = \zihao{-3}\bfseries\centering,
        beforeskip = 20pt,
        afterskip = 20pt
    },
    section = {
        format = \zihao{4}\bfseries,
        beforeskip = 12pt,
        afterskip = 6pt
    },
    subsection = {
        format = \zihao{-4}\bfseries,
        beforeskip = 8pt,
        afterskip = 4pt
    }
}

\onehalfspacing

\lstset{
    language=SQL,
    basicstyle=\small\ttfamily,
    keywordstyle=\color{blue},
    commentstyle=\color{gray},
    stringstyle=\color{orange},
    numbers=left,
    numberstyle=\tiny\color{gray},
    stepnumber=1,
    frame=single,
    breaklines=true,
    showstringspaces=false
}

\graphicspath{{figures/}}

\begin{document}
\hypersetup{pageanchor=false}

% ==================== 封面 ====================
\begin{titlepage}
    \centering
    \vspace*{2cm}
    {\zihao{2}\bfseries 浙江师范大学}\\[0.8cm]
    {\zihao{-1}\bfseries 硕士学位论文}\\[2.5cm]
    {\zihao{2}\bfseries 面向线索数据感知的多智能体\\SQL生成方法研究}\\[0.8cm]
    {\zihao{3} Research on a Clue Data-Aware SQL Generation Method\\Based on Multi-Agent Collaboration}\\[3cm]
    \begin{tabular}{rl}
        \zihao{4}\textbf{作\quad 者：} & \zihao{4}张念龙 \\[0.5cm]
        \zihao{4}\textbf{学\quad 号：} & \zihao{4}202320701127 \\[0.5cm]
        \zihao{4}\textbf{专\quad 业：} & \zihao{4}软件工程 \\[0.5cm]
        \zihao{4}\textbf{导\quad 师：} & \zihao{4}叶荣华教授 \\[0.5cm]
        \zihao{4}\textbf{学\quad 院：} & \zihao{4}计算机科学与技术学院 \\
    \end{tabular}
    \vfill
    {\zihao{4} 2026年5月}
\end{titlepage}

\newpage
\thispagestyle{empty}
\begin{center}
    {\zihao{3}\bfseries 学位论文原创性声明}
\end{center}
\vspace{1cm}
\zihao{-4}
本人郑重声明：所呈交的学位论文，是本人在导师的指导下，独立进行研究工作所取得的成果。除文中已经注明引用的内容外，本论文不包含任何其他个人或集体已经发表或撰写过的作品成果。对本文的研究做出重要贡献的个人和集体，均已在文中以明确方式标明。本人完全意识到本声明的法律结果由本人承担。
\vspace{2cm}
\begin{flushright}
    学位论文作者签名：\underline{\hspace{4cm}} \quad 日期：\underline{\hspace{3cm}}
\end{flushright}

\newpage
\thispagestyle{empty}
\begin{center}
    {\zihao{3}\bfseries 学位论文独创性声明}
\end{center}
\vspace{1cm}
\zihao{-4}
本人声明所呈交的学位论文是本人在导师指导下进行的研究工作及取得的研究成果。除了文中特别加以标注和致谢的地方外，论文中不包含其他人已经发表或撰写过的研究成果，也不包含为获得浙江师范大学或其他教育机构的学位或证书而使用过的材料。与我一同工作的同志对本研究所做的任何贡献均已在论文中作了明确的说明并表示谢意。
\vspace{2cm}
\begin{flushright}
    学位论文作者签名：\underline{\hspace{4cm}} \quad 日期：\underline{\hspace{3cm}}
\end{flushright}

\newpage
\thispagestyle{empty}
\begin{center}
    {\zihao{3}\bfseries 学位论文使用授权声明}
\end{center}
\vspace{1cm}
\zihao{-4}
本人完全了解浙江师范大学关于保留、使用学位论文的规定，即：学校有权保留送交论文的复印件和电子文档，允许论文被查阅和借阅，可以采用影印、缩印或扫描等手段保存、汇编学位论文。同意学校用不同方式在不同媒体上发表、传播论文的全部或部分内容。保密的学位论文在解密后遵守此协议。
\vspace{2cm}
\begin{flushright}
    学位论文作者签名：\underline{\hspace{4cm}} \quad 日期：\underline{\hspace{3cm}} \\[1cm]
    导师签名：\underline{\hspace{4.6cm}} \quad 日期：\underline{\hspace{3cm}}
\end{flushright}

\newpage
\pagenumbering{Roman}
\setcounter{page}{1}

"""
    latex += "\n".join(body)
    latex += r"""

\end{document}
"""
    return latex


def main():
    pages = load_pages()
    blocks = split_into_blocks(pages)
    processed = process_blocks(blocks)

    md = generate_markdown(processed)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote Markdown to {OUTPUT_MD}")

    latex = md_to_latex(md)
    with open(OUTPUT_TEX, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"Wrote LaTeX to {OUTPUT_TEX}")


if __name__ == "__main__":
    main()
