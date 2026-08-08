#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert thesis PDF to clean Markdown and LaTeX (v5).
"""

import json
import re
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).parent
PDF_PATH = BASE_DIR.parent / "面向线索数据感知的多智能体SQL生成-张念龙.pdf"
OUTPUT_MD = BASE_DIR / "thesis.md"
OUTPUT_TEX = BASE_DIR / "thesis.tex"
FIGURES_DIR = BASE_DIR / "figures"
EXTRACTED_JSON = BASE_DIR / "extracted_text_v5.json"

BODY_SIZE = 12.0
CHAPTER_SIZE = 16.0
SECTION_SIZE = 15.0
SMALL_SIZE = 10.8

MATH_SYMBOLS = set(
    "𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧"
    "𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍"
    "𝛼𝛽𝛾𝛿𝜆𝜃𝜎𝜇𝜈𝜋𝜌𝜏𝜑𝜔𝜁𝜂𝜅𝜉𝜓"
    "ΓΔΘΛΣΦΨΩ∞∑∏∫∂∇√⋅×÷±≤≥≠≈∈∪∩→←⇒⇐⟨⟩"
)


def ensure_dirs():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def is_bold(span):
    return bool(span["flags"] & 16) or span["flags"] == 20


def collect_spans(page):
    spans = []
    for block in page.get_text("dict")["blocks"]:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                spans.append({
                    "text": span["text"],
                    "size": round(span["size"], 1),
                    "flags": span["flags"],
                    "bold": is_bold(span),
                    "bbox": span["bbox"],
                    "origin": span["origin"],
                })
    spans.sort(key=lambda s: (round(s["bbox"][1], 1), s["bbox"][0]))
    return spans


def merge_spans_into_lines(spans):
    lines = []
    if not spans:
        return lines
    cur = [spans[0]]
    y_tol = 3.0
    for sp in spans[1:]:
        if abs(sp["bbox"][1] - cur[-1]["bbox"][1]) <= y_tol:
            cur.append(sp)
        else:
            cur.sort(key=lambda s: s["bbox"][0])
            lines.append(cur)
            cur = [sp]
    if cur:
        cur.sort(key=lambda s: s["bbox"][0])
        lines.append(cur)
    return lines


def line_text(line, strip=True):
    t = "".join(s["text"] for s in line)
    return t.strip() if strip else t


def avg_size(line):
    if not line:
        return 0
    return sum(s["size"] for s in line) / len(line)


def all_bold(line):
    return all(s["bold"] for s in line) and len(line) > 0


def line_has_math(line):
    t = line_text(line, False)
    return any(c in MATH_SYMBOLS for c in t) or bool(re.search(r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]", t))


def is_equation_line(line):
    t = line_text(line)
    size = avg_size(line)
    has_eqnum = bool(re.search(r"\(\s*\d+\.\d+\s*\)\s*$", t))
    if has_eqnum:
        return True
    if size <= SMALL_SIZE and line_has_math(line):
        return True
    if line_has_math(line) and not re.search(r"[一-鿿]", t):
        return True
    return False


def is_page_header_footer(t, page_num):
    s = t.strip()
    if re.fullmatch(r"[IVXLC]+", s):
        return True
    if re.fullmatch(r"\d+", s):
        return True
    if s == "面向线索数据感知的多智能体SQL生成方法研究":
        return True
    # page headers like "1绪论", "1 绪论", "2 相关理论与技术"
    if re.match(r"^\d\s*[一-龥A-Z].{2,30}$", s):
        return True
    if re.match(r"^\d\.\d\s*[一-龥A-Z].{2,30}$", s):
        return True
    if re.match(r"^\d\.\d\.\d\s*[一-龥A-Z].{2,30}$", s):
        return True
    return False


def strip_inline_page_header(t):
    """Remove page header prefix from a line if present."""
    s = t.strip()
    # patterns: "1绪论 ...", "2 相关理论与技术 ...", "3.4 本章小结 ..."
    m = re.match(r"^(\d\s*[一-龥A-Z][一-龥a-zA-Z\s]{2,30})(?=[A-Za-z]|User|\d{4}|\{|SELECT|TABLE|图|表)", s)
    if m:
        return s[len(m.group(1)):].strip()
    m = re.match(r"^(\d\.\d\s*[一-龥A-Z][一-龥a-zA-Z\s]{2,30})(?=[A-Za-z]|User|SELECT|TABLE|图|表)", s)
    if m:
        return s[len(m.group(1)):].strip()
    return t


def classify_page_type(text, first_lines, page_num):
    s = text.strip()
    first_text = "\n".join(first_lines[:8])
    if page_num <= 3:
        return "cover"
    if "学位论文原创性声明" in s or "学位论文独创性声明" in s or "学位论文使用授权声明" in s:
        return "statement"
    if "目录" in first_text[:20] or re.search(r"\.{5,}\s*\d+\s*$", first_text, re.M):
        return "toc"
    if first_text.startswith("摘要") or first_text.startswith("摘 要") or "\n摘要" in first_text[:30]:
        return "abstract_cn"
    if first_text.startswith("ABSTRACT") or first_text.startswith("Research on a Clue"):
        return "abstract_en"
    if s.startswith("参考文献"):
        return "references"
    if s.startswith("致谢"):
        return "acknowledgement"
    # Continuation of abstract: previous page was abstract and current has no new heading
    # This is handled externally via page context
    if "攻读学位期间取得的研究成果" in s[:40]:
        return "publications"
    if re.search(r"\.{10,}\s*\d+", s):
        return "toc"
    return "body"


def extract_images(page, page_num):
    saved = []
    imglist = page.get_images(full=True)
    for img_index, img in enumerate(imglist, start=1):
        xref = img[0]
        try:
            pix = fitz.Pixmap(page.parent, xref)
            if pix.n - pix.alpha > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            name = f"fig_p{page_num:03d}_{img_index:02d}.png"
            path = FIGURES_DIR / name
            pix.save(str(path))
            saved.append(str(path.relative_to(BASE_DIR)))
        except Exception as e:
            print(f"  image save error page {page_num}: {e}")
    return saved


def extract_page(page_num, doc):
    page = doc[page_num - 1]
    spans = collect_spans(page)
    lines = merge_spans_into_lines(spans)
    page_h = page.rect.height
    filtered = []
    for line in lines:
        y_top = line[0]["bbox"][1]
        y_bot = line[0]["bbox"][3]
        t = line_text(line)
        # remove standalone page headers by position
        if y_top < 55 and is_page_header_footer(t, page_num):
            continue
        if y_bot > page_h - 70 and is_page_header_footer(t, page_num):
            continue
        # strip inline page header prefix from any line
        cleaned = strip_inline_page_header(t)
        if cleaned != t:
            # rebuild line text by updating the first span(s) - simple approximation
            # for our downstream use we only need line_text, so store cleaned in a new single span line
            new_line = [{"text": cleaned, "size": line[0]["size"], "flags": line[0]["flags"], "bold": line[0]["bold"], "bbox": line[0]["bbox"], "origin": line[0]["origin"]}]
            filtered.append(new_line)
        else:
            filtered.append(line)

    text_lines = [line_text(line) for line in filtered]
    text = "\n".join(text_lines)
    ptype = classify_page_type(text, text_lines, page_num)
    images = extract_images(page, page_num) if ptype == "body" else []
    return {
        "page": page_num,
        "type": ptype,
        "lines": filtered,
        "images": images,
    }


def is_code_line(t):
    s = t.strip()
    sql_kw = r"SELECT|FROM|WHERE|GROUP BY|ORDER BY|LIMIT|INSERT|UPDATE|DELETE|CREATE|TABLE|PRIMARY KEY|FOREIGN KEY|JOIN|INNER|LEFT|RIGHT|ON|AS|ALTER|DROP|INDEX|VALUES"
    if re.match(rf"^({sql_kw})\\b", s, re.I):
        return True
    if re.match(r"^\\{.*\\}$", s) or re.match(r'^".*"$', s):
        return True
    if re.match(r"^\\(.*\\)$", s) and any(k in s.lower() for k in ["integer", "text", "primary", "key"]):
        return True
    return False


def normalize_body_text(page_data_list):
    blocks = []
    buf_lines = []

    def flush_para():
        nonlocal buf_lines
        if not buf_lines:
            return
        text = " ".join(line_text(l) for l in buf_lines)
        text = re.sub(r"(\w)-\s+", r"\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            blocks.append(("para", text))
        buf_lines = []

    def detect_heading_line(t, size, bold):
        t = t.strip()
        # English title
        if t.startswith("Research on a Clue Data-Aware SQL Generation Method"):
            return t, 1
        m = re.match(r"^([1-9])\s+([一-龥A-Z].{1,30})$", t)
        if m and (size >= CHAPTER_SIZE - 1 or bold):
            return m.group(2).strip(), 1
        m = re.match(r"^第([1-9一二三四五六])章\s+(.+)$", t)
        if m:
            return m.group(2).strip(), 1
        m = re.match(r"^(\d{1,2}\.\d{1,2})\s+([一-龥A-Z].+)$", t)
        if m and (size >= SECTION_SIZE - 1 or bold):
            return m.group(2).strip(), 2
        m = re.match(r"^(\d{1,2}\.\d{1,2}\.\d{1,2})\s+([一-龥A-Z].+)$", t)
        if m:
            return m.group(2).strip(), 3
        if t in ("摘要", "ABSTRACT", "参考文献", "致谢", "攻读学位期间取得的研究成果"):
            return t, 1
        return None

    for page_data in page_data_list:
        ptype = page_data["type"]
        for line in page_data["lines"]:
            t = line_text(line)
            if not t:
                flush_para()
                continue
            size = avg_size(line)
            bold = all_bold(line)

            heading = detect_heading_line(t, size, bold)
            if heading:
                flush_para()
                blocks.append(("heading", heading[0], heading[1]))
                continue

            if re.match(r"^(图|表|Fig\.?|Table)\s*\d+", t):
                flush_para()
                blocks.append(("caption", t))
                continue

            if is_equation_line(line):
                flush_para()
                blocks.append(("formula", t))
                continue

            if is_code_line(t) and (t.upper().startswith(("SELECT", "FROM", "WHERE", "TABLE", "CREATE", "INSERT", "UPDATE", "DELETE", "PRIMARY", "FOREIGN", "JOIN", "INNER", "LEFT", "RIGHT", "ON", "AS", "ALTER", "DROP", "INDEX", "VALUES", "GROUP", "ORDER", "LIMIT")) or re.match(r"^[\"{\\(]", t)):
                flush_para()
                blocks.append(("code", t))
                continue

            if re.match(r"^（\d+）|^\(\d+\)|^\d+[、．]\s|^[-•·–—]\s", t):
                flush_para()
                blocks.append(("list", t))
                continue

            if size <= SMALL_SIZE and not re.search(r"[一-鿿]", t) and len(t) < 80 and not t.endswith((".", "。", "?", "!")):
                flush_para()
                blocks.append(("figure_text", t))
                continue

            buf_lines.append(line)

    flush_para()
    return blocks


def process_pdf():
    ensure_dirs()
    doc = fitz.open(str(PDF_PATH))
    pages = []
    for page_num in range(1, len(doc) + 1):
        pages.append(extract_page(page_num, doc))
    doc.close()

    # Fix abstract continuation classifications
    prev_type = None
    for p in pages:
        if prev_type in ("abstract_cn", "abstract_en") and p["type"] == "body":
            first_lines_text = "\n".join(line_text(line) for line in p["lines"][:5])
            # if no chapter/section heading, it's likely abstract continuation
            if not re.search(r"^(摘要|ABSTRACT|第[1-9一二三四五六]章|\d+\s+[一-龥A-Z]|\d+\.\d+\s+[一-龥A-Z])", first_lines_text):
                p["type"] = prev_type
        prev_type = p["type"]

    with open(EXTRACTED_JSON, "w", encoding="utf-8") as f:
        json.dump(pages, f, ensure_ascii=False, indent=2)

    body_pages = [p for p in pages if p["type"] in ("body", "abstract_cn", "abstract_en")]
    blocks = normalize_body_text(body_pages)
    return blocks, pages


def unicode_to_latex_math(text):
    mappings = {
        "𝜋": r"\\pi", "𝛼": r"\\alpha", "𝛽": r"\\beta", "𝛾": r"\\gamma",
        "𝛿": r"\\delta", "𝜆": r"\\lambda", "𝜃": r"\\theta", "𝜎": r"\\sigma",
        "𝜇": r"\\mu", "𝜈": r"\\nu", "𝜌": r"\\rho", "𝜏": r"\\tau",
        "𝜑": r"\\varphi", "𝜔": r"\\omega", "𝜁": r"\\zeta", "𝜂": r"\\eta",
        "𝜅": r"\\kappa", "𝜉": r"\\xi", "𝜓": r"\\psi", "Γ": r"\\Gamma",
        "Δ": r"\\Delta", "Θ": r"\\Theta", "Λ": r"\\Lambda", "Σ": r"\\Sigma",
        "Φ": r"\\Phi", "Ψ": r"\\Psi", "Ω": r"\\Omega", "∞": r"\\infty",
        "⋅": r"\\cdot", "×": r"\\times", "÷": r"\\div", "±": r"\\pm",
        "∓": r"\\mp", "≤": r"\\leq", "≥": r"\\geq", "≠": r"\\neq",
        "≈": r"\\approx", "∈": r"\\in", "∉": r"\\notin", "∪": r"\\cup",
        "∩": r"\\cap", "⊂": r"\\subset", "⊆": r"\\subseteq", "⊃": r"\\supset",
        "⊇": r"\\supseteq", "∅": r"\\emptyset", "∀": r"\\forall", "∃": r"\\exists",
        "∧": r"\\land", "∨": r"\\lor", "¬": r"\\neg", "→": r"\\rightarrow",
        "←": r"\\leftarrow", "⇒": r"\\Rightarrow", "⇐": r"\\Leftarrow",
        "↔": r"\\leftrightarrow", "⇔": r"\\Leftrightarrow", "↑": r"\\uparrow",
        "↓": r"\\downarrow", "∑": r"\\sum", "∏": r"\\prod", "∫": r"\\int",
        "∂": r"\\partial", "∇": r"\\nabla", "√": r"\\sqrt", "…": r"\\ldots",
        "⋯": r"\\cdots", "⋮": r"\\vdots", "⋱": r"\\ddots", "′": "'", "″": "''",
        "⟨": r"\\langle", "⟩": r"\\rangle", "𝑑": "d", "𝔼": r"\\mathbb{E}",
    }
    italic = [
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
    ]
    for a, b in italic:
        mappings[a] = b

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


def generate_markdown(blocks, pages):
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

    prev_type = None
    in_code = False
    for block in blocks:
        btype = block[0]
        if btype == "heading":
            _, title, level = block
            if in_code:
                out.append("```")
                in_code = False
            prefix = "#" * level
            out.append("")
            out.append(f"{prefix} {title}")
            out.append("")
            prev_type = "heading"
        elif btype == "para":
            text = block[1]
            if in_code:
                out.append("```")
                in_code = False
            if prev_type == "para":
                out.append("")
            out.append(text)
            prev_type = "para"
        elif btype == "formula":
            text = block[1]
            if in_code:
                out.append("```")
                in_code = False
            out.append("")
            out.append(f"$${text}$$")
            out.append("")
            prev_type = "formula"
        elif btype == "code":
            text = block[1]
            if not in_code:
                out.append("")
                out.append("```sql")
                in_code = True
            out.append(text)
            prev_type = "code"
        elif btype == "list":
            text = block[1]
            if in_code:
                out.append("```")
                in_code = False
            out.append("")
            out.append(text)
            prev_type = "list"
        elif btype == "caption":
            text = block[1]
            if in_code:
                out.append("```")
                in_code = False
            out.append("")
            out.append(f"*{text}*")
            out.append("")
            prev_type = "caption"
        elif btype == "figure_text":
            text = block[1]
            if not in_code:
                out.append("")
                out.append("```")
                in_code = True
            out.append(text)
            prev_type = "code"

    if in_code:
        out.append("```")

    for ptype in ("references", "acknowledgement", "publications"):
        for p in pages:
            if p["type"] == ptype:
                title_map = {
                    "references": "参考文献",
                    "acknowledgement": "致谢",
                    "publications": "攻读学位期间取得的研究成果",
                }
                out.append("")
                out.append(f"# {title_map[ptype]}")
                out.append("")
                for line in p["lines"]:
                    t = line_text(line)
                    if not t or t.startswith("参考文献") or t.startswith("致谢") or t.startswith("攻读学位"):
                        continue
                    out.append(t)

    return "\n".join(out)


def escape_latex(text):
    chars = {
        "&": r"\\&", "%": r"\\%", "$": r"\\$", "#": r"\\#",
        "_": r"\\_", "{": r"\\{", "}": r"\\}",
        "~": r"\\textasciitilde{}",
        "^": r"\\textasciicircum{}",
    }
    for ch, rep in chars.items():
        text = text.replace(ch, rep)
    return text


def md_to_latex(md):
    lines = md.splitlines()
    body = []
    in_code = False
    in_list = False
    list_env = None

    def close_lists():
        nonlocal in_list, list_env
        if in_list:
            body.append(f"\\\\end{{{list_env}}}")
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

        if stripped.startswith("- **") or stripped.startswith("> 说明："):
            i += 1
            continue
        if stripped.startswith("# ") and "面向线索数据感知" in stripped and i < 15:
            i += 1
            continue

        if stripped.startswith("# "):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            close_lists()
            title = stripped[2:].strip()
            if title == "摘要":
                body.append(r"\\chapter*{摘\\quad 要}")
                body.append(r"\\addcontentsline{toc}{chapter}{摘要}")
            elif title == "ABSTRACT":
                body.append(r"\\chapter*{Abstract}")
                body.append(r"\\addcontentsline{toc}{chapter}{Abstract}")
            elif title == "参考文献":
                body.append(r"\\chapter*{参考文献}")
                body.append(r"\\addcontentsline{toc}{chapter}{参考文献}")
            elif title == "致谢":
                body.append(r"\\chapter*{致\\quad 谢}")
                body.append(r"\\addcontentsline{toc}{chapter}{致谢}")
            elif title == "攻读学位期间取得的研究成果":
                body.append(r"\\chapter*{攻读学位期间取得的研究成果}")
                body.append(r"\\addcontentsline{toc}{chapter}{攻读学位期间取得的研究成果}")
            else:
                body.append(f"\\chapter{{{title}}}")
            body.append(r"\\zihao{{-4}}")
        elif stripped.startswith("## "):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            close_lists()
            body.append(f"\\section{{{stripped[3:].strip()}}}")
        elif stripped.startswith("### "):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            close_lists()
            body.append(f"\\subsection{{{stripped[4:].strip()}}}")
        elif stripped.startswith("#### "):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            close_lists()
            body.append(f"\\subsubsection{{{stripped[5:].strip()}}}")
        elif stripped == "```sql" or stripped == "```":
            if in_code:
                body.append(r"\\end{lstlisting}")
                in_code = False
            else:
                close_lists()
                body.append(r"\\begin{lstlisting}")
                in_code = True
        elif stripped.startswith("*") and re.match(r"^[*](图|表|Fig|Table).*", stripped):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            close_lists()
            cap = stripped.strip("*").strip()
            body.append(r"\\begin{figure}[htbp]")
            body.append(r"\\centering")
            body.append(r"\\fbox{\\parbox{0.8\\textwidth}{\\centering \\zihao{5} " + escape_latex(cap) + r"}}")
            body.append(r"\\caption{" + escape_latex(cap) + r"}")
            body.append(r"\\end{figure}")
        elif stripped.startswith("$$") and stripped.endswith("$$"):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            close_lists()
            formula = stripped[2:-2].strip()
            formula = unicode_to_latex_math(formula)
            body.append(r"\\begin{equation}")
            body.append(formula)
            body.append(r"\\end{equation}")
        elif re.match(r"^（\d+）", stripped):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\\begin{enumerate}[label=(\\arabic*)]")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^（\d+）", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\(\d+\)", stripped):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\\begin{enumerate}[label=(\\arabic*)]")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^\(\d+\)", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^\d+[、．]\\s", stripped):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "enumerate"):
                close_lists()
                body.append(r"\\begin{enumerate}")
                in_list = True
                list_env = "enumerate"
            item = re.sub(r"^\d+[、．]\\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        elif re.match(r"^[-•·–—]\\s", stripped):
            if in_code:
                body.append("\\\\end{lstlisting}")
                in_code = False
            if not (in_list and list_env == "itemize"):
                close_lists()
                body.append(r"\\begin{itemize}")
                in_list = True
                list_env = "itemize"
            item = re.sub(r"^[-•·–—]\\s", "", stripped).strip()
            body.append(f"\\item {escape_latex(item)}")
        else:
            if in_code:
                body.append(escape_latex(line.rstrip()))
            else:
                close_lists()
                body.append(escape_latex(line.rstrip()) + r"\\")
        i += 1

    if in_code:
        body.append("\\\\end{lstlisting}")
    if in_list:
        body.append(f"\\\\end{{{list_env}}}")

    return "\n".join(body)


def build_latex(body_tex):
    lines = [
        r"% 面向线索数据感知的多智能体SQL生成方法研究",
        r"% 作者：张念龙",
        r"\documentclass[12pt,a4paper,openright,UTF8]{ctexbook}",
        r"\usepackage{geometry}",
        r"\geometry{left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm}",
        r"\usepackage{xeCJK}",
        r"\usepackage{amsmath,amssymb,amsfonts,amsthm}",
        r"\usepackage{graphicx}",
        r"\usepackage{booktabs}",
        r"\usepackage{longtable}",
        r"\usepackage{multirow}",
        r"\usepackage{array}",
        r"\usepackage{float}",
        r"\usepackage{caption}",
        r"\usepackage{subcaption}",
        r"\usepackage{enumitem}",
        r"\usepackage{algorithm}",
        r"\usepackage{algpseudocode}",
        r"\usepackage{listings}",
        r"\usepackage{xcolor}",
        r"\usepackage{hyperref}",
        r"\usepackage{cleveref}",
        r"\usepackage{setspace}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{titlesec}",
        r"\usepackage{tocloft}",
        r"\usepackage[numbers,sort&compress]{natbib}",
        r"\bibliographystyle{gbt7714-numerical}",
        r"\setlength{\headheight}{14pt}",
        r"\addtolength{\topmargin}{-2pt}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\fancyhead[C]{\small \leftmark}",
        r"\fancyfoot[C]{\thepage}",
        r"\renewcommand{\headrulewidth}{0.4pt}",
        r"\ctexset{",
        r"    chapter = {format = \zihao{-3}\bfseries\centering, beforeskip = 20pt, afterskip = 20pt},",
        r"    section = {format = \zihao{4}\bfseries, beforeskip = 12pt, afterskip = 6pt},",
        r"    subsection = {format = \zihao{-4}\bfseries, beforeskip = 8pt, afterskip = 4pt}",
        r"}",
        r"\onehalfspacing",
        r"\lstset{language=SQL,basicstyle=\small\ttfamily,keywordstyle=\color{blue},commentstyle=\color{gray},stringstyle=\color{orange},numbers=left,numberstyle=\tiny\color{gray},stepnumber=1,frame=single,breaklines=true,showstringspaces=false}",
        r"\graphicspath{{figures/}}",
        r"\begin{document}",
        r"\hypersetup{pageanchor=false}",
        r"",
        r"% ==================== 封面 ====================",
        r"\begin{titlepage}",
        r"    \centering",
        r"    \vspace*{2cm}",
        r"    {\zihao{2}\bfseries 浙江师范大学}\\[0.8cm]",
        r"    {\zihao{-1}\bfseries 硕士学位论文}\\[2.5cm]",
        r"    {\zihao{2}\bfseries 面向线索数据感知的多智能体\\SQL生成方法研究}\\[0.8cm]",
        r"    {\zihao{3} Research on a Clue Data-Aware SQL Generation Method\\Based on Multi-Agent Collaboration}\\[3cm]",
        r"    \begin{tabular}{rl}",
        r"        \zihao{4}\textbf{作\quad 者：} & \zihao{4}张念龙 \\[0.5cm]",
        r"        \zihao{4}\textbf{学\quad 号：} & \zihao{4}202320701127 \\[0.5cm]",
        r"        \zihao{4}\textbf{专\quad 业：} & \zihao{4}软件工程 \\[0.5cm]",
        r"        \zihao{4}\textbf{导\quad 师：} & \zihao{4}叶荣华教授 \\[0.5cm]",
        r"        \zihao{4}\textbf{学\quad 院：} & \zihao{4}计算机科学与技术学院 \\",
        r"    \end{tabular}",
        r"    \vfill",
        r"    {\zihao{4} 2026年5月}",
        r"\end{titlepage}",
        r"",
        r"\newpage",
        r"\thispagestyle{empty}",
        r"\begin{center}",
        r"    {\zihao{3}\bfseries 学位论文原创性声明}",
        r"\end{center}",
        r"\vspace{1cm}",
        r"\zihao{-4}",
        r"本人郑重声明：所呈交的学位论文，是本人在导师的指导下，独立进行研究工作所取得的成果。除文中已经注明引用的内容外，本论文不包含任何其他个人或集体已经发表或撰写过的作品成果。对本文的研究做出重要贡献的个人和集体，均已在文中以明确方式标明。本人完全意识到本声明的法律结果由本人承担。",
        r"\vspace{2cm}",
        r"\begin{flushright}",
        r"    学位论文作者签名：\underline{\hspace{4cm}} \quad 日期：\underline{\hspace{3cm}}",
        r"\end{flushright}",
        r"",
        r"\newpage",
        r"\thispagestyle{empty}",
        r"\begin{center}",
        r"    {\zihao{3}\bfseries 学位论文独创性声明}",
        r"\end{center}",
        r"\vspace{1cm}",
        r"\zihao{-4}",
        r"本人声明所呈交的学位论文是本人在导师指导下进行的研究工作及取得的研究成果。除了文中特别加以标注和致谢的地方外，论文中不包含其他人已经发表或撰写过的研究成果，也不包含为获得浙江师范大学或其他教育机构的学位或证书而使用过的材料。与我一同工作的同志对本研究所做的任何贡献均已在论文中作了明确的说明并表示谢意。",
        r"\vspace{2cm}",
        r"\begin{flushright}",
        r"    学位论文作者签名：\underline{\hspace{4cm}} \quad 日期：\underline{\hspace{3cm}}",
        r"\end{flushright}",
        r"",
        r"\newpage",
        r"\thispagestyle{empty}",
        r"\begin{center}",
        r"    {\zihao{3}\bfseries 学位论文使用授权声明}",
        r"\end{center}",
        r"\vspace{1cm}",
        r"\zihao{-4}",
        r"本人完全了解浙江师范大学关于保留、使用学位论文的规定，即：学校有权保留送交论文的复印件和电子文档，允许论文被查阅和借阅，可以采用影印、缩印或扫描等手段保存、汇编学位论文。同意学校用不同方式在不同媒体上发表、传播论文的全部或部分内容。保密的学位论文在解密后遵守此协议。",
        r"\vspace{2cm}",
        r"\begin{flushright}",
        r"    学位论文作者签名：\underline{\hspace{4cm}} \quad 日期：\underline{\hspace{3cm}} \\[1cm]",
        r"    导师签名：\underline{\hspace{4.6cm}} \quad 日期：\underline{\hspace{3cm}}",
        r"\end{flushright}",
        r"",
        r"\newpage",
        r"\pagenumbering{Roman}",
        r"\setcounter{page}{1}",
        r"\tableofcontents",
        r"\newpage",
        r"\pagenumbering{arabic}",
        r"\setcounter{page}{1}",
        r"",
        body_tex,
        r"",
        r"\end{document}",
    ]
    return "\n".join(lines)


def main():
    print("Extracting PDF...")
    blocks, pages = process_pdf()
    print(f"Extracted {len(blocks)} blocks")

    print("Generating Markdown...")
    md = generate_markdown(blocks, pages)
    OUTPUT_MD.write_text(md, encoding="utf-8")
    print(f"Wrote {OUTPUT_MD}")

    print("Generating LaTeX...")
    body_tex = md_to_latex(md)
    tex = build_latex(body_tex)
    OUTPUT_TEX.write_text(tex, encoding="utf-8")
    print(f"Wrote {OUTPUT_TEX}")


if __name__ == "__main__":
    main()
