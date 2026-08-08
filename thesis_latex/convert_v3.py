#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert extracted thesis PDF text to Markdown and LaTeX.
Uses line-based paragraph merging with improved heading/formula/code detection.
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
EXTRACTED_JSON = BASE_DIR / "extracted_text.json"
OUTPUT_MD = BASE_DIR / "thesis.md"
OUTPUT_TEX = BASE_DIR / "thesis.tex"

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

CHAPTER_TITLES = {
    "绪论", "相关理论与技术", "认知对齐增强和多视角共识推理方法",
    "基于动态强化学习的检索增强生成方法", "多智能体协同的NL2SQL框架",
    "多智能体协同的NL2SQL 框架", "总结与展望",
}


def load_extracted():
    with open(EXTRACTED_JSON, "r", encoding="utf-8") as f:
        pages = json.load(f)
    for page in pages:
        pnum = page.get("page", 0)
        if pnum in CHAPTER_INSERTIONS:
            heading = CHAPTER_INSERTIONS[pnum]
            text = page.get("text", "")
            first_lines = "\n".join(text.splitlines()[:2])
            if heading not in first_lines:
                page["text"] = heading + "\n" + text
    return pages


def remove_page_header_footer(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if re.fullmatch(r"[IVXLC]+", s):
            continue
        out.append(s)
    return out


def pre_merge_headings(lines: list[str]) -> list[str]:
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
            if re.match(r"^\d{1,2}\.\d{1,2}(\.\d{1,2})?$", s) and "%" not in s and len(s) < 10 and re.match(r"^[一-龥A-Z]", nxt):
                out.append(s + " " + nxt)
                i += 2
                continue
            if re.match(r"^\d$", s) and nxt in CHAPTER_TITLES:
                out.append(s + " " + nxt)
                i += 2
                continue
        out.append(s)
        i += 1
    return out


def detect_heading(line: str) -> tuple[str, int] | None:
    s = line.strip()
    # Subsection
    m = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\s*([一-龥A-Z].*)$", s)
    if m:
        return (m.group(2).strip(), 3)
    # Section
    m = re.match(r"^(\d{1,2}\.\d{1,2})\s*([一-龥A-Z].*)$", s)
    if m:
        return (m.group(2).strip(), 2)
    # Chapter with space - restrict chapter number to 1-9
    m = re.match(r"^([1-9])\s+(.+)$", s)
    if m and not re.match(r"^\d+[、．]", s):
        title = m.group(2).strip()
        if len(title) < 40 and not title.startswith("(") and not title[0].isdigit():
            return (title, 1)
    # Chapter without space, e.g. "1绪论"
    m = re.match(r"^([1-9])([一-龥]{2,})$", s)
    if m:
        return (m.group(2).strip(), 1)
    # Special headings
    if s in ("摘 要", "摘要", "ABSTRACT", "目 录", "目录", "参考文献", "致谢"):
        return (s.replace(" ", ""), 1)
    return None


def is_caption(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^(图|表|Fig\.?|Table)\s*\d+", s))


def is_formula_line(line: str) -> bool:
    """A line is formula-like if it is dominated by math symbols or ends with an equation number."""
    s = line.strip()
    math_chars = set("𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍𝛼𝛽𝛾𝛿𝜆𝜃𝜎𝜇𝜈𝜋𝜌𝜏𝜑𝜔𝜁𝜂𝜅𝜉𝜓ΓΔΘΛΣΦΨΩ∞∑∏∫∂∇√⋅×÷±≤≥≠≈∈∪∩→←⇒⇐⟨⟩")
    math_count = sum(1 for c in line if c in math_chars)
    latin_letters = sum(1 for c in line if c.isascii() and c.isalpha())
    chinese_chars = len(re.findall(r"[一-鿿]", line))
    has_eqnum = bool(re.search(r"\(\d+\.\d+\)\s*$", s))

    # Strong signal: ends with equation number
    if has_eqnum:
        return True
    # If lots of Chinese text, not a formula even with a few math symbols
    if chinese_chars > 10 and math_count < 8:
        return False
    # If mostly latin/math and several math symbols
    if math_count >= 4 and (math_count + latin_letters) > 0.5 * len(s):
        return True
    return False


def is_code_line(line: str) -> bool:
    s = line.strip()
    if re.match(r"^(SELECT|FROM|WHERE|GROUP BY|ORDER BY|LIMIT|INSERT|UPDATE|DELETE|CREATE|TABLE|PRIMARY KEY|FOREIGN KEY|JOIN|INNER|LEFT|RIGHT|ON|AS|ALTER|DROP|INDEX|VALUES)", s, re.I):
        return True
    if re.match(r"^\{.*\}$", s) or re.match(r'^".*"$', s):
        return True
    if re.match(r"^\(.*\)$", s) and any(k in s.lower() for k in ["integer", "text", "primary", "key"]):
        return True
    return False


def is_list_item(line: str) -> bool:
    s = line.strip()
    return bool(re.match(r"^（\d+）|^\(\d+\)|^\d+[、．]\s|^[-•·–—]\s", s))


def needs_space_between(a: str, b: str) -> bool:
    if not a or not b:
        return False
    a_end = a[-1]
    b_start = b[0]
    latin_end = a_end.isascii() and (a_end.isalnum() or a_end in ")]})%'")")
    latin_start = b_start.isascii() and (b_start.isalnum() or b_start in "([{#'\"")
    return latin_end and latin_start


def is_sentence_end(a: str) -> bool:
    if not a:
        return False
    last = a.rstrip()[-1]
    return last in "。；：！？.!?"


def normalize_body_text(text: str) -> list[tuple[str, str]]:
    """Merge lines into paragraphs while preserving structure. Returns typed blocks."""
    lines = text.splitlines()
    lines = remove_page_header_footer(lines)
    lines = pre_merge_headings(lines)

    out = []
    buf = ""

    def flush_para():
        nonlocal buf
        if buf:
            if buf.endswith("-") and not buf.endswith("--"):
                buf = buf[:-1]
            out.append(("para", buf))
            buf = ""

    for s in lines:
        s = s.strip()
        if not s:
            flush_para()
            continue

        heading = detect_heading(s)
        if heading:
            flush_para()
            title, level = heading
            out.append(("heading", "#" * level + " " + title))
            continue

        if is_caption(s):
            flush_para()
            out.append(("caption", s))
            continue

        if is_formula_line(s):
            flush_para()
            out.append(("formula", s))
            continue

        if is_code_line(s):
            flush_para()
            out.append(("code", s))
            continue

        if is_list_item(s):
            flush_para()
            out.append(("list", s))
            continue

        if not buf:
            buf = s
            continue

        last = buf.rstrip()
        if last.endswith("-"):
            buf = buf[:-1] + s
        elif is_sentence_end(last):
            flush_para()
            buf = s
        else:
            if needs_space_between(last, s):
                buf += " " + s
            else:
                buf += s

    flush_para()
    return out


def classify_page(text: str, page_num: int) -> str:
    s = text.strip()
    if page_num <= 3:
        return "cover"
    if "目 录" in s[:10] or "目录" in s[:10] or re.search(r"\.{5,}\s*I+\s*$", s, re.M):
        return "toc"
    if "学位论文原创性声明" in s or "学位论文独创性声明" in s or "学位论文使用授权声明" in s:
        return "statement"
    if s.startswith("摘 要") or s.startswith("摘要"):
        return "abstract_cn"
    if s.startswith("ABSTRACT") or s.startswith("Research on"):
        return "abstract_en"
    if s.startswith("参考文献"):
        return "references"
    if s.startswith("致谢"):
        return "acknowledgement"
    if "攻读学位期间取得的研究成果" in s[:30]:
        return "publications"
    return "body"


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
        "⟨": r"\langle", "⟩": r"\rangle", "𝑑": "d", "𝔼": r"\mathbb{E}",
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
        mappings[_c] = _rep

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


def process_pages(pages: list[dict]) -> list[tuple[str, str]]:
    classified = []
    for page in pages:
        text = page.get("text", "")
        page_num = page.get("page", 0)
        if not text.strip():
            continue
        ptype = classify_page(text, page_num)
        classified.append((ptype, text, page_num))

    result = []
    body_buffer = []

    def flush_body():
        if body_buffer:
            combined = "\n".join(body_buffer)
            result.extend(normalize_body_text(combined))
            body_buffer.clear()

    for ptype, text, _ in classified:
        if ptype in ("cover", "toc", "statement"):
            flush_body()
            # skip these pages entirely for now
            continue
        body_buffer.append(text)

    flush_body()
    return result


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
    for btype, text in blocks:
        if btype == "heading":
            out.append("")
            out.append(text)
            out.append("")
            prev_type = "heading"
        elif btype == "para":
            if prev_type == "para":
                out.append("")
            out.append(text)
            prev_type = "para"
        elif btype == "formula":
            out.append("")
            out.append(f"$${text}$$")
            out.append("")
            prev_type = "formula"
        elif btype == "code":
            if prev_type == "code":
                out.append(text)
            else:
                out.append("")
                out.append("```")
                out.append(text)
            prev_type = "code"
        elif btype == "list":
            if prev_type == "list":
                out.append(text)
            else:
                out.append("")
                out.append(text)
            prev_type = "list"
        elif btype == "caption":
            out.append("")
            out.append(f"*{text}*")
            out.append("")
            prev_type = "caption"

    if prev_type == "code":
        out.append("```")

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
    list_env = None

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
            if in_code:
                body.append("\\end{lstlisting}")
                in_code = False
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
            if in_code:
                body.append("\\end{lstlisting}")
                in_code = False
            body.append(f"\\section{{{stripped[3:].strip()}}}")
        elif stripped.startswith("### "):
            close_lists()
            if in_code:
                body.append("\\end{lstlisting}")
                in_code = False
            body.append(f"\\subsection{{{stripped[4:].strip()}}}")
        elif stripped.startswith("#### "):
            close_lists()
            if in_code:
                body.append("\\end{lstlisting}")
                in_code = False
            body.append(f"\\subsubsection{{{stripped[5:].strip()}}}")
        elif stripped == "```":
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            else:
                close_lists()
                body.append(r"\begin{lstlisting}")
                in_code = True
        elif stripped.startswith("*图"):
            close_lists()
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            cap = stripped.strip("*").strip()
            body.append(r"\begin{figure}[htbp]")
            body.append(r"\centering")
            body.append(r"\fbox{\parbox{0.8\textwidth}{\centering \zihao{5} " + escape_latex(cap) + r"}}")
            body.append(r"\caption{" + escape_latex(cap) + r"}")
            body.append(r"\end{figure}")
        elif stripped.startswith("*表"):
            close_lists()
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            cap = stripped.strip("*").strip()
            body.append(r"\begin{table}[htbp]")
            body.append(r"\centering")
            body.append(r"\caption{" + escape_latex(cap) + r"}")
            body.append(r"\fbox{\parbox{0.8\textwidth}{\centering \zihao{5} " + escape_latex(cap) + r"}}")
            body.append(r"\end{table}")
        elif stripped.startswith("$$") and stripped.endswith("$$"):
            close_lists()
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            formula = stripped[2:-2].strip()
            formula = unicode_to_latex_math(formula)
            body.append(r"\begin{equation}")
            body.append(formula)
            body.append(r"\end{equation}")
        elif re.match(r"^\*\*关键词：\*\*|^\*\*Keywords:\*\*", stripped):
            close_lists()
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            if "关键词" in stripped:
                body.append(r"\noindent\textbf{关键词：}" + stripped.split("关键词：", 1)[1].strip("*").strip())
            else:
                body.append(r"\noindent\textbf{Keywords:} " + stripped.split("Keywords:", 1)[1].strip("*").strip())
        elif re.match(r"^（\d+）", stripped):
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\begin{enumerate}[label=(\arabic*)]")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^（\d+）", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\(\d+\)", stripped):
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\begin{enumerate}[label=(\arabic*)]")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^\(\d+\)", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\d+[、．]\s", stripped):
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\begin{enumerate}")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^\d+[、．]\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^[-•·–—]\s", stripped):
            if in_code:
                body.append(r"\end{lstlisting}")
                in_code = False
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
                if body and body[-1].startswith(r"\item "):
                    body[-1] += " " + escape_latex(stripped)
                else:
                    close_lists()
                    body.append(escape_latex(stripped))
            else:
                body.append(escape_latex(stripped))
        i += 1

    close_lists()
    if in_code:
        body.append(r"\end{lstlisting}")

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
    pages = load_extracted()
    blocks = process_pages(pages)
    md = generate_markdown(blocks)
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote Markdown to {OUTPUT_MD}")

    latex = md_to_latex(md)
    with open(OUTPUT_TEX, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"Wrote LaTeX to {OUTPUT_TEX}")


if __name__ == "__main__":
    main()
