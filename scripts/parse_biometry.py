#!/usr/bin/env python3
"""
Extrai biometria de um laudo (PDF com texto, PDF escaneado, imagem PNG/JPG ou .txt)
e grava biometria.json no schema de assets/biometry.schema.json.

É um PRIMEIRO PASSO determinístico. Laudos variam muito entre aparelhos e versões de
software, então o JSON traz `raw_snippets` (o trecho de texto de onde cada número saiu)
e `confidence`. Quem usa a skill DEVE comparar o JSON com o laudo (abrindo a página como
imagem) antes de digitar em qualquer calculadora. Nunca confie cegamente neste parser.

Privacidade: nome/prontuário NÃO são gravados. Só `patient.code` (passado por --code).

Uso:
  python3 parse_biometry.py laudo.pdf --code P-2026-091 --out biometria.json
  python3 parse_biometry.py laudo.png --code P-2026-091 --ocr --lang por+eng
  python3 parse_biometry.py laudo.pdf --dump-text        # só mostra o texto extraído (debug)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

NUM = r"(-?\d{1,3}(?:[.,]\d{1,3})?)"


def _to_float(s: str) -> float:
    return float(s.replace(",", "."))


# ------------------------------------------------------------------ extração de texto
def extract_text(path: Path, force_ocr: bool = False, lang: str = "por+eng") -> tuple[str, str]:
    """Retorna (texto, método). Tenta camada de texto do PDF; cai em OCR se vazio."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace"), "txt"
    if suffix == ".pdf" and not force_ocr:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            text = "\n".join(page.get_text("text") for page in doc)
            if len(text.strip()) > 80:
                return text, "pdf-text"
        except ImportError:
            pass
    # OCR (PDF escaneado ou imagem)
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise SystemExit(f"OCR indisponível ({exc}). Instale pytesseract/Pillow ou passe um PDF com texto.")
    images = []
    if suffix == ".pdf":
        import fitz
        doc = fitz.open(path)
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            images.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    else:
        images.append(Image.open(path))
    text = "\n".join(pytesseract.image_to_string(im, lang=lang, config="--psm 6") for im in images)
    return text, "ocr"


# ------------------------------------------------------------------ detecção de aparelho
DEVICE_PATTERNS = [
    ("IOLMaster 700", r"IOLMaster\s*700"),
    ("IOLMaster 500", r"IOLMaster\s*500"),
    ("IOLMaster", r"IOLMaster"),
    ("Lenstar LS900", r"LENSTAR|EyeSuite"),
    ("Argos", r"\bARGOS\b"),
    ("Anterion", r"ANTERION"),
    ("Pentacam AXL", r"Pentacam\s*AXL"),
    ("Aladdin", r"Aladdin"),
    ("AL-Scan", r"AL-?Scan"),
    ("OA-2000", r"OA-?2000"),
]


def detect_device(text: str) -> str:
    for name, pat in DEVICE_PATTERNS:
        if re.search(pat, text, re.I):
            return name
    return "desconhecido"


# ------------------------------------------------------------------ split por olho
def split_eyes(text: str) -> dict[str, str]:
    """Divide o texto em blocos OD/OS. Se o laudo é lado a lado (comum), devolve o texto
    inteiro para os dois e deixa a extração por posição resolver (1º valor = OD, 2º = OS)."""
    right_markers = [m.start() for m in re.finditer(r"\b(OD|Right|Direito)\b|\bR\s*(?=\n|:|\s{2,})", text)]
    left_markers = [m.start() for m in re.finditer(r"\b(OS|OE|Left|Esquerdo)\b|\bL\s*(?=\n|:|\s{2,})", text)]
    if not right_markers or not left_markers:
        return {"OD": text, "OS": text}
    r0, l0 = right_markers[0], left_markers[0]
    if abs(r0 - l0) < 40:            # cabeçalhos lado a lado → laudo em colunas
        return {"OD": text, "OS": text}
    if r0 < l0:
        return {"OD": text[r0:l0], "OS": text[l0:]}
    return {"OS": text[l0:r0], "OD": text[r0:]}


# ------------------------------------------------------------------ extração de campos
FIELD_PATTERNS = {
    "AL":  [rf"\bAL\s*[:=]?\s*{NUM}\s*mm", rf"Axial\s*Length\s*[:=]?\s*{NUM}", rf"Comprimento\s*axial\s*[:=]?\s*{NUM}"],
    "K1":  [rf"\bK1\s*[:=]?\s*{NUM}\s*D?\s*(?:@\s*(\d{{1,3}}))?", rf"\bR1\s*[:=]?\s*{NUM}\s*mm\s*(?:@\s*(\d{{1,3}}))?"],
    "K2":  [rf"\bK2\s*[:=]?\s*{NUM}\s*D?\s*(?:@\s*(\d{{1,3}}))?", rf"\bR2\s*[:=]?\s*{NUM}\s*mm\s*(?:@\s*(\d{{1,3}}))?"],
    "TK1": [rf"\bTK1\s*[:=]?\s*{NUM}\s*D?\s*(?:@\s*(\d{{1,3}}))?"],
    "TK2": [rf"\bTK2\s*[:=]?\s*{NUM}\s*D?\s*(?:@\s*(\d{{1,3}}))?"],
    "ACD_ext": [rf"\bACD\s*\(ext\.?\)\s*[:=]?\s*{NUM}"],
    "ACD_int": [rf"\bACD\s*\(int\.?\)\s*[:=]?\s*{NUM}"],
    "ACD": [rf"\bACD\s*[:=]?\s*{NUM}\s*mm", rf"Anterior\s*Chamber\s*Depth\s*[:=]?\s*{NUM}"],
    "AD":  [rf"\bA(?:Q)?D\s*(?:\(ACD\))?\s*[:=]?\s*{NUM}\s*mm"],
    "AL_SD": [rf"\bAL\s*[:=]?\s*{NUM}\s*mm\s*(?:SD|±)\s*[:=]?\s*{NUM}"],
    "LT":  [rf"\bLT\s*[:=]?\s*{NUM}\s*mm", rf"Lens\s*Thickness\s*[:=]?\s*{NUM}"],
    "WTW": [rf"\bWTW\s*[:=]?\s*{NUM}\s*mm", rf"White[- ]to[- ]White\s*[:=]?\s*{NUM}"],
    "CCT": [rf"\bCCT\s*[:=]?\s*{NUM}\s*(?:µm|um|μm)", rf"Pachymetry\s*[:=]?\s*{NUM}"],
    "SNR": [rf"\bSNR\s*[:=]?\s*{NUM}"],
}
AGE_PATTERNS = [r"(?:Age|Idade)\s*[:=]?\s*(\d{1,3})", r"(\d{1,3})\s*(?:anos|years|yrs)"]
SEX_PATTERNS = [r"(?:Sex|Sexo|Gender)\s*[:=]?\s*(F|M|Fem\w*|Masc\w*|Male|Female)"]
INDEX_PATTERNS = [r"(?:n\s*=|index|índice)\s*(1[.,]33(?:75|2|15))"]


def _find_all(patterns: list[str], text: str) -> list[tuple[float, str | None, str]]:
    hits = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.I):
            val = _to_float(m.group(1))
            axis = m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else None
            hits.append((val, axis, m.group(0)))
    return hits


def extract_eye(block: str, position: int, shared: bool) -> dict:
    """position: 0 para OD, 1 para OS quando o laudo é em colunas (shared=True)."""
    eye: dict = {"quality_flags": [], "raw_snippets": {}}
    for field, pats in FIELD_PATTERNS.items():
        hits = _find_all(pats, block)
        if not hits:
            continue
        idx = min(position, len(hits) - 1) if shared else 0
        val, axis, snippet = hits[idx]
        if shared and len(hits) < 2:
            eye["quality_flags"].append(f"{field}: só 1 valor no laudo em colunas; OD/OS podem estar ambíguos")
        eye["raw_snippets"][field] = snippet
        if field in ("K1", "K2", "TK1", "TK2"):
            entry = {"D": None, "mm": None, "axis": int(axis) if axis else None}
            if val < 12:            # veio em mm (raio); converte com 1.3375
                entry["mm"] = val
                entry["D"] = round(337.5 / val, 2)
                eye["quality_flags"].append(f"{field} lido em mm ({val}); convertido para D com n=1.3375")
            else:
                entry["D"] = val
            eye[field] = entry
        elif field == "SNR":
            eye["AL_SNR"] = val
        elif field == "AL_SD":
            # padrão captura (AL, SD): o 2º grupo é o SD
            m = re.search(pats[0], block, re.I)
            if m:
                eye["AL_SD"] = _to_float(m.group(2))
        else:
            eye[field] = val
    eye.setdefault("K_index", 1.3375)
    eye["K_type"] = "SimK"
    # Resolve ACD: preferir epitélio→cristalino. Pentacam ACD (ext.) > ACD > (AD/AQD + CCT).
    if eye.get("ACD_ext") is not None:
        eye["ACD"], eye["ACD_reference"] = eye["ACD_ext"], "epithelium"
    elif eye.get("ACD") is not None:
        eye["ACD_reference"] = "epithelium"   # IOLMaster/Lenstar/Argos/Aladdin rotulam ACD assim
    else:
        aqueous = eye.get("ACD_int") if eye.get("ACD_int") is not None else eye.get("AD")
        if aqueous is not None and eye.get("CCT") is not None:
            eye["ACD"] = round(aqueous + eye["CCT"] / 1000.0, 2)
            eye["ACD_reference"] = "epithelium"
            eye["quality_flags"].append(f"ACD derivado de profundidade aquosa {aqueous} + CCT {eye['CCT']} µm (Lenstar AD / Anterion AQD / Pentacam int.)")
        elif aqueous is not None:
            eye["ACD"], eye["ACD_reference"] = aqueous, "endothelium"
            eye["quality_flags"].append("Só profundidade aquosa (endotélio→cristalino) e sem CCT: ACD marcado como endothelium")
        else:
            eye["ACD_reference"] = "unknown"
    for k in ("ACD_ext", "ACD_int", "AD"):
        eye.pop(k, None)
    # Olho já operado: LT de LIO (<1.5 mm) e/ou ACD até a LIO (>4.5 mm) → não é erro, é pseudofacia.
    if (eye.get("LT") is not None and eye["LT"] < 1.5) or (eye.get("ACD") is not None and eye["ACD"] > 4.5 and eye.get("LT", 9) < 2.5):
        eye["skip"] = "pseudofacico"
        eye["quality_flags"].append("LS provável: Pseudophakic (LT/ACD compatíveis com LIO). Cálculo pulado; só calcule se for troca de LIO.")
    if re.search(r"Pseudophakic|Pseudof[áa]cic", block, re.I) and not re.search(r"\bPhakic\b", block):
        eye["skip"] = "pseudofacico"
    return eye


def parse(text: str, code: str, source: str) -> dict:
    device = detect_device(text)
    blocks = split_eyes(text)
    shared = blocks["OD"] is blocks["OS"] or blocks["OD"] == blocks["OS"]
    eyes = {}
    for pos, eye in enumerate(("OD", "OS")):
        parsed = extract_eye(blocks[eye], pos, shared)
        if "AL" in parsed and "K1" in parsed and "K2" in parsed:
            eyes[eye] = parsed
    age = sex = None
    for pat in AGE_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            age = int(m.group(1)); break
    for pat in SEX_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            sex = m.group(1)[0].upper(); break
    for pat in INDEX_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            idx = _to_float(m.group(1))
            for e in eyes.values():
                e["K_index"] = idx
            break
    n_fields = sum(len(e["raw_snippets"]) for e in eyes.values())
    confidence = "alta" if n_fields >= 10 else ("media" if n_fields >= 6 else "baixa")
    return {
        "patient": {"code": code, "age": age, "sex": sex},
        "device": device,
        "exam_date": None,
        "source_file": Path(source).name,
        "eyes": eyes,
        "plan": {"target_refraction": 0.0, "lens_model": None, "A_constant": None, "post_refractive": "none", "toric": False, "formulas": []},
        "_parser": {"confidence": confidence, "fields_found": n_fields, "layout": "colunas" if shared else "blocos"},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--code", default="P-0000", help="código interno do paciente (NUNCA nome)")
    ap.add_argument("--out", default="biometria.json")
    ap.add_argument("--ocr", action="store_true", help="força OCR mesmo em PDF com texto")
    ap.add_argument("--lang", default="por+eng")
    ap.add_argument("--dump-text", action="store_true")
    args = ap.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        print(f"arquivo não encontrado: {path}", file=sys.stderr); return 2
    text, method = extract_text(path, force_ocr=args.ocr, lang=args.lang)
    if args.dump_text:
        print(text); return 0
    data = parse(text, args.code, str(path))
    data["_parser"]["text_method"] = method
    Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"out": args.out, "device": data["device"], "eyes": list(data["eyes"].keys()),
                      "parser": data["_parser"]}, ensure_ascii=False))
    if not data["eyes"]:
        print("AVISO: nenhum olho com AL+K1+K2 encontrado. Use --dump-text para ver o texto e ajuste manualmente.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
