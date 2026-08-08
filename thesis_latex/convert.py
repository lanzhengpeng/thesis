#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert extracted thesis PDF text to Markdown and LaTeX."""

import json
import re
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXTRACTED_JSON = BASE_DIR / "extracted_text.json"
OUTPUT_MD = BASE_DIR / "thesis.md"
OUTPUT_TEX = BASE_DIR / "thesis_generated.tex"

CHAPTER_TITLES = {
    "绪论", "相关理论与技术", "认知对齐增强和多视角共识推理方法",
    "基于动态强化学习的检索增强生成方法", "多智能体协同的NL2SQL框架",
    "多智能体协同的NL2SQL 框架", "总结与展望"
}

# Page numbers where chapter headings should be inserted (after header cropping removed them)
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


def load_extracted():
    with open(EXTRACTED_JSON, "r", encoding="utf-8") as f:
        pages = json.load(f)
    for page in pages:
        pnum = page.get("page", 0)
        if pnum in CHAPTER_INSERTIONS:
            heading = CHAPTER_INSERTIONS[pnum]
            text = page.get("text", "")
            # Avoid duplicating if heading already present at start
            first_lines = "\n".join(text.splitlines()[:2])
            if heading not in first_lines:
                page["text"] = heading + "\n" + text
    return pages


def classify_page(text: str, page_num: int) -> str:
    """Classify page type based on content."""
    s = text.strip()
    lines = s.splitlines()
    toc_like = sum(1 for line in lines if re.search(r"\.{4,}", line))
    if page_num <= 3:
        return "cover"
    if toc_like >= 5 or "目 录" in s or "目录" in s[:10] or re.search(r"\.{5,}\s*I+\s*$", s, re.M):
        return "toc"
    if "学位论文原创性声明" in s or "学位论文独创性声明" in s or "学位论文使用授权声明" in s or "诚信承诺书" in s:
        return "statement"
    if "摘 要" in s[:10] or s.startswith("摘要"):
        return "abstract_cn"
    if s.startswith("ABSTRACT") or s.startswith("Research on"):
        return "abstract_en"
    if "参考文献" in s[:10]:
        return "references"
    if "致谢" in s[:10]:
        return "acknowledgement"
    if "攻读学位期间取得的研究成果" in s[:30]:
        return "publications"
    return "body"


def remove_page_header_footer(lines: list[str]) -> list[str]:
    """Remove standalone Roman numeral page numbers only."""
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        # Keep digits (may be chapter numbers or list items)
        if re.fullmatch(r"[IVXLC]+", s):
            continue
        out.append(s)
    return out


def detect_heading(line: str) -> tuple[str, int] | None:
    s = line.strip()
    # Subsection - allow optional space, also no-space Chinese titles
    m = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\s*([一-龥A-Z].*)$", s)
    if m:
        return (m.group(2).strip(), 3)
    # Section
    m = re.match(r"^(\d{1,2}\.\d{1,2})\s*([一-龥A-Z].*)$", s)
    if m:
        return (m.group(2).strip(), 2)
    # Chapter with space
    m = re.match(r"^(\d+)\s+(.+)$", s)
    if m and not re.match(r"^\d+[、．]", s):
        title = m.group(2).strip()
        if len(title) < 40 and not title.startswith("("):
            return (title, 1)
    # Chapter without space: e.g. "1绪论"
    m = re.match(r"^(\d+)([一-龥]{2,})$", s)
    if m:
        return (m.group(2).strip(), 1)
    # Special headings
    if s in ("摘 要", "摘要", "ABSTRACT", "目 录", "目录", "参考文献", "致谢"):
        return (s.replace(" ", ""), 1)
    return None


def is_list_item(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^（\d+）|^\(\d+\)|^\d+[、．]\s|^[-•·–—]\s", s))


def is_caption(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^(图|表|Fig\.?|Table)\s*\d+", s))


def is_formula_line(line: str) -> bool:
    math_chars = set("𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍𝛼𝛽𝛾𝛿𝜆𝜃𝜎𝜇𝜈𝜋𝜌𝜏𝜑𝜔𝜁𝜂𝜅𝜉𝜓ΓΔΘΛΣΦΨΩ∞∑∏∫∂∇√⋅×÷±≤≥≠≈∈∪∩→←⇒⇐⟨⟩")
    count = sum(1 for c in line if c in math_chars)
    return count > 2 or bool(re.search(r"\(\d+\.\d+\)\s*$", line.strip()))


def is_structured_line(line: str) -> bool:
    s = line.strip()
    if re.match(r"^(SELECT|FROM|WHERE|GROUP BY|ORDER BY|LIMIT|INSERT|UPDATE|DELETE|CREATE|TABLE|PRIMARY KEY|FOREIGN KEY)", s, re.I):
        return True
    if re.match(r"^\{.*\}$", s) or re.match(r'^".*"$', s):
        return True
    return False


def needs_space_between(a: str, b: str) -> bool:
    """Return True if a space should be inserted between two concatenated lines."""
    if not a or not b:
        return False
    # Add space if a ends with Latin letter/digit/paren and b starts with Latin letter/digit/paren
    a_end = a[-1]
    b_start = b[0]
    latin_end = a_end.isascii() and (a_end.isalnum() or a_end in ")]}%'")
    latin_start = b_start.isascii() and (b_start.isalnum() or b_start in "([{#'")
    return latin_end and latin_start


def is_sentence_end(a: str, b: str) -> bool:
    """Determine if line a ends a sentence relative to the start of line b."""
    if not a:
        return False
    last = a.rstrip()[-1]
    if last in "。；：！？":
        return True
    if last in ".!?":
        b_start = b.strip()[:1]
        if b_start.isupper():
            return True
        return False
    return False


def pre_merge_headings(lines: list[str]) -> list[str]:
    """Merge heading fragments that PyMuPDF splits across lines."""
    out = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            # 摘 + 要
            if s == "摘" and nxt == "要":
                out.append("摘要")
                i += 2
                continue
            # Section/subsection number + title (strict: no % sign, short number)
            if re.match(r"^\d{1,2}\.\d{1,2}(\.\d{1,2})?\.?$", s) and "%" not in s and len(s) < 10 and re.match(r"^[一-龥A-Z]", nxt):
                out.append(s + " " + nxt)
                i += 2
                continue
            # Chapter number + title
            if re.match(r"^\d$", s) and nxt in CHAPTER_TITLES:
                out.append(s + " " + nxt)
                i += 2
                continue
        out.append(s)
        i += 1
    return out


def normalize_body_text(text: str) -> list[str]:
    """Merge lines into paragraphs while preserving structure."""
    lines = text.splitlines()
    lines = remove_page_header_footer(lines)
    lines = pre_merge_headings(lines)

    out = []
    buf = ""

    def flush():
        nonlocal buf
        if buf:
            if buf.endswith("-") and not buf.endswith("--"):
                buf = buf[:-1]
            out.append(buf)
            buf = ""

    for s in lines:
        s = s.strip()
        if not s:
            flush()
            continue

        if detect_heading(s) or is_caption(s) or is_formula_line(s):
            flush()
            out.append(s)
            continue

        if is_structured_line(s):
            flush()
            out.append(s)
            continue

        if not buf:
            buf = s
            continue

        last = buf.rstrip()
        if last.endswith("-"):
            buf = buf[:-1] + s
        elif is_sentence_end(last, s):
            flush()
            buf = s
        else:
            if needs_space_between(last, s):
                buf += " " + s
            else:
                buf += s

    flush()
    return out


def unicode_to_latex_math(text: str) -> str:
    mappings = {
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
        "†": r"\dagger", "‡": r"\ddagger", "§": r"\S", "¶": r"\P",
        "⟨": r"\langle", "⟩": r"\rangle", "𝑑": "d", "𝔼": r"\mathbb{E}",
    }
    for c, rep in [
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
        mappings[c] = rep

    for ch, cmd in mappings.items():
        text = text.replace(ch, cmd)

    sup_map = {
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5",
        "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9", "⁺": "+", "⁻": "-",
        "⁼": "=", "⁽": "(", "⁾": ")", "ᵃ": "a", "ᵇ": "b", "ᶜ": "c",
        "ᵈ": "d", "ᵉ": "e", "ᶠ": "f", "ᵍ": "g", "ʰ": "h", "ⁱ": "i",
        "ʲ": "j", "ᵏ": "k", "ˡ": "l", "ᵐ": "m", "ⁿ": "n", "ᵒ": "o",
        "ᵖ": "p", "ʳ": "r", "ˢ": "s", "ᵗ": "t", "ᵘ": "u", "ᵛ": "v",
        "ʷ": "w", "ˣ": "x", "ʸ": "y", "ᶻ": "z",
    }
    sub_map = {
        "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5",
        "₆": "6", "₇": "7", "₈": "8", "₉": "9", "₊": "+", "₋": "-",
        "₌": "=", "₍": "(", "₎": ")", "ₐ": "a", "ₑ": "e", "ᵢ": "i",
        "ⱼ": "j", "ₒ": "o", "ᵤ": "u", "ᵥ": "v", "ₓ": "x",
    }
    for ch, cmd in sup_map.items():
        text = text.replace(ch, f"^{{{cmd}}}")
    for ch, cmd in sub_map.items():
        text = text.replace(ch, f"_{{{cmd}}}")
    return text


def process_pages(pages: list[dict]) -> list[tuple[str, list[str]]]:
    """Process pages in order, merging consecutive body-like pages to preserve paragraphs across page breaks."""
    classified = []
    for page in pages:
        text = page.get("text", "")
        page_num = page.get("page", 0)
        if not text.strip():
            continue
        ptype = classify_page(text, page_num)
        classified.append((ptype, text))

    result = []
    body_buffer = []

    def flush_body():
        if body_buffer:
            combined = "\n".join(body_buffer)
            result.append(("body", normalize_body_text(combined)))
            body_buffer.clear()

    for ptype, text in classified:
        if ptype in ("cover", "toc", "statement"):
            flush_body()
            result.append((ptype, remove_page_header_footer(text.splitlines())))
        else:
            body_buffer.append(text)

    flush_body()
    return result


def generate_markdown(processed: list[tuple[str, list[str]]]) -> str:
    blocks = []
    blocks.append(("meta", "# 面向线索数据感知的多智能体SQL生成方法研究"))
    blocks.append(("meta", "- **作者：** 张念龙"))
    blocks.append(("meta", "- **指导教师：** 叶荣华 教授"))
    blocks.append(("meta", "- **学校：** 浙江师范大学"))
    blocks.append(("meta", "- **专业：** 软件工程"))
    blocks.append(("meta", "- **学号：** 202320701127"))
    blocks.append(("meta", "- **提交时间：** 2026年5月25日"))
    blocks.append(("meta", "> 说明：本文件由PDF自动转换生成，部分公式、图表、代码块可能需要人工复核。"))

    toc_seen = False
    for ptype, lines in processed:
        if ptype == "toc":
            if not toc_seen:
                blocks.append(("heading", "# 目录"))
                blocks.append(("para", "_（目录页内容省略，详见PDF原文）_"))
                toc_seen = True
            continue
        if ptype == "cover":
            continue
        if ptype == "statement":
            blocks.append(("para", "\n".join(lines)))
            continue

        for s in lines:
            s = s.strip()
            if not s:
                continue
            heading = detect_heading(s)
            if heading:
                title, level = heading
                blocks.append(("heading", f"{'#' * level} {title}"))
                continue
            if is_caption(s):
                blocks.append(("caption", f"*{s}*"))
                continue
            if is_formula_line(s):
                blocks.append(("formula", f"$${s}$$"))
                continue
            if is_structured_line(s):
                blocks.append(("code", f"```\n{s}\n```"))
                continue
            if is_list_item(s):
                blocks.append(("list", s))
                continue
            blocks.append(("para", s))

    # Join blocks with appropriate spacing
    out = []
    prev_type = None
    for btype, text in blocks:
        if btype == "heading":
            out.append("\n" + text + "\n")
        elif btype in ("caption", "formula", "code"):
            out.append("\n" + text + "\n")
        elif btype == "list":
            if prev_type == "list":
                out.append(text)
            else:
                out.append("\n" + text)
        elif btype == "para":
            if prev_type == "para":
                out.append("\n\n" + text)
            else:
                out.append(text)
        else:  # meta, etc.
            out.append(text)
        prev_type = btype

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
    in_enumerate = False
    in_itemize = False
    in_code = False

    def close_lists():
        nonlocal in_enumerate, in_itemize
        if in_enumerate:
            body.append(r"\end{enumerate}")
            in_enumerate = False
        if in_itemize:
            body.append(r"\end{itemize}")
            in_itemize = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            if in_code:
                body.append("")
            else:
                close_lists()
                body.append("")
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
            body.append(r"\fbox{\parbox{0.8\textwidth}{\centering \zihao{5}" + cap + r"}}")
            body.append(r"\caption{" + cap + r"}")
            body.append(r"\end{figure}")
        elif stripped.startswith("*表"):
            close_lists()
            cap = stripped.strip("*").strip()
            body.append(r"\begin{table}[htbp]")
            body.append(r"\centering")
            body.append(r"\caption{" + cap + r"}")
            body.append(r"\fbox{\parbox{0.8\textwidth}{\centering \zihao{5}" + cap + r"}}")
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
            if not in_enumerate:
                close_lists()
                body.append(r"\begin{enumerate}[label=(\arabic*)]")
                in_enumerate = True
            item = re.sub(r"^（\d+）", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\(\d+\)", stripped):
            if not in_enumerate:
                close_lists()
                body.append(r"\begin{enumerate}[label=(\arabic*)]")
                in_enumerate = True
            item = re.sub(r"^\(\d+\)", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\d+[、．]\s", stripped):
            if not in_enumerate:
                close_lists()
                body.append(r"\begin{enumerate}")
                in_enumerate = True
            item = re.sub(r"^\d+[、．]\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^[-•·–—]\s", stripped):
            if not in_itemize:
                close_lists()
                body.append(r"\begin{itemize}")
                in_itemize = True
            item = re.sub(r"^[-•·–—]\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        else:
            if in_code:
                body.append(stripped)
            elif in_enumerate or in_itemize:
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
% 本文件由PDF自动转换生成，公式、图表、代码块可能需要人工复核
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
    pages = load_extracted()
    processed = process_pages(pages)
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
