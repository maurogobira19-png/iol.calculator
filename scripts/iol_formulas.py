#!/usr/bin/env python3
"""
Fórmulas de cálculo de LIO de domínio público, implementadas para CHECAGEM CRUZADA
dos resultados devolvidos pelas calculadoras web (Barrett, Kane, EVO, Hill-RBF, ...).

NÃO substituem as calculadoras modernas. Servem para:
  1. detectar erro de transcrição/unidade antes de abrir o browser (pré-cálculo);
  2. detectar resultado web absurdo (campo colado errado, índice de K trocado);
  3. dar um envelope esperado (min/max entre SRK/T, Holladay 1, Hoffer Q, Haigis).

Referências:
  SRK/T   : Retzlaff JA, Sanders DR, Kraff MC. J Cataract Refract Surg 1990;16:333-340 (+ errata).
  Holladay1: Holladay JT et al. J Cataract Refract Surg 1988;14:17-24.
  Hoffer Q: Hoffer KJ. J Cataract Refract Surg 1993;19:700-712 (+ errata 1994, 2007).
  Haigis  : Haigis W et al. Graefes Arch Clin Exp Ophthalmol 2000;238:765-773.

Uso CLI:
  python3 iol_formulas.py --al 23.45 --k1 43.25 --k2 44.00 --acd 3.12 --a-const 118.7 --target -0.25
  python3 iol_formulas.py --json biometria.json --eye OD --a-const 119.3
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, asdict

N_AQUEOUS = 1.336          # índice do aquoso/vítreo (todas as fórmulas)
K_INDEX_DEFAULT = 1.3375   # índice ceratométrico "clínico" (337.5/r)
VERTEX_MM = 12.0           # distância vértice para refração alvo


@dataclass(frozen=True)
class Inputs:
    al: float            # comprimento axial, mm
    k1: float            # D (índice k_index)
    k2: float            # D
    a_const: float       # A-constante SRK/T do modelo de LIO
    target: float = 0.0  # refração alvo, D (negativo = miopia)
    acd: float | None = None   # ACD medido (epitélio -> cristalino), mm. Só Haigis usa.
    k_index: float = K_INDEX_DEFAULT
    a0: float | None = None    # Haigis; se None, deriva do A-constante
    a1: float = 0.4
    a2: float = 0.1

    @property
    def k_mean(self) -> float:
        return (self.k1 + self.k2) / 2.0

    @property
    def r_mm(self) -> float:
        """Raio corneano em mm a partir de K médio e do índice ceratométrico usado."""
        return (self.k_index - 1.0) * 1000.0 / self.k_mean


def _k_1_3375(inp: Inputs) -> float:
    """Reexpressa K médio no índice 1.3375 (SRK/T, Holladay, Hoffer Q assumem 337.5/r)."""
    return 337.5 / inp.r_mm


# --------------------------------------------------------------------------- SRK/T
def srkt(inp: Inputs) -> float:
    na, nc = N_AQUEOUS, 1.333
    ncm1 = nc - 1.0
    k = _k_1_3375(inp)
    r = 337.5 / k
    al = inp.al
    lcor = al if al <= 24.2 else (-3.446 + 1.716 * al - 0.0237 * al * al)
    cw = -5.41 + 0.58412 * lcor + 0.098 * k
    disc = r * r - (cw * cw) / 4.0
    h = r - math.sqrt(disc) if disc > 0 else r
    acd_const = 0.62467 * inp.a_const - 68.747
    offset = acd_const - 3.336
    acd_est = h + offset
    rethick = 0.65696 - 0.02029 * al
    lopt = al + rethick
    rx, v = inp.target, VERTEX_MM
    num = 1000.0 * na * (na * r - ncm1 * lopt) - 0.001 * rx * (v * (na * r - ncm1 * lopt) + lopt * r)
    den = (lopt - acd_est) * (na * r - ncm1 * acd_est) - 0.001 * rx * (v * (na * r - ncm1 * acd_est) + acd_est * r)
    return num / den


# --------------------------------------------------------------------------- Holladay 1
def holladay1(inp: Inputs) -> float:
    na, nc = N_AQUEOUS, 4.0 / 3.0
    k = _k_1_3375(inp)
    rag = max(337.5 / k, 7.0)
    ag = min(12.5 * inp.al / 23.45, 13.5)
    acd = 0.56 + rag - math.sqrt(rag * rag - ag * ag / 4.0)
    sf = 0.5663 * inp.a_const - 65.6            # Surgeon Factor derivado da A-constante
    alm = inp.al + 0.2
    rx, v = inp.target, VERTEX_MM
    num = 1000.0 * na * (na * rag - (nc - 1) * alm - 0.001 * rx * (v * (na * rag - (nc - 1) * alm) + alm * rag))
    den = (alm - acd - sf) * (na * rag - (nc - 1) * (acd + sf) - 0.001 * rx * (v * (na * rag - (nc - 1) * (acd + sf)) + (acd + sf) * rag))
    return num / den


# --------------------------------------------------------------------------- Hoffer Q
def hoffer_q(inp: Inputs) -> float:
    k = _k_1_3375(inp)
    al = inp.al
    p_acd = 0.58357 * inp.a_const - 63.896     # pACD derivado da A-constante
    m, g = (1.0, 28.0) if al <= 23.0 else (-1.0, 23.5)
    al_c = min(max(al, 18.5), 31.0)
    tan_k = math.tan(math.radians(k))
    acd = (p_acd + 0.3 * (al_c - 23.5) + tan_k ** 2
           + 0.1 * m * (23.5 - al_c) ** 2 * math.tan(math.radians(0.1 * (g - al_c) ** 2))
           - 0.99166)
    rx = inp.target
    term1 = 1336.0 / (al - acd - 0.05)
    term2 = 1.336 / ((1.336 / (k + rx / (1.0 - 0.012 * rx))) - (acd + 0.05) / 1000.0)
    return term1 - term2


# --------------------------------------------------------------------------- Haigis
def haigis(inp: Inputs) -> float | None:
    if inp.acd is None:
        return None
    n = N_AQUEOUS
    r_mm = inp.r_mm
    dc = 331.5 / r_mm                          # poder corneano com índice 1.3315
    a0 = inp.a0 if inp.a0 is not None else (0.62467 * inp.a_const - 72.434)
    d = a0 + inp.a1 * inp.acd + inp.a2 * inp.al  # ELP, mm
    rx = inp.target
    z = dc + rx / (1.0 - rx * 0.012)
    l_m, d_m = inp.al / 1000.0, d / 1000.0
    return n / (l_m - d_m) - n / (n / z - d_m)


FORMULAS = {"SRK/T": srkt, "Holladay 1": holladay1, "Hoffer Q": hoffer_q, "Haigis": haigis}


def compute_all(inp: Inputs) -> dict:
    out = {}
    for name, fn in FORMULAS.items():
        try:
            val = fn(inp)
        except (ValueError, ZeroDivisionError) as exc:  # entrada fora do domínio
            out[name] = {"iol_power": None, "error": str(exc)}
            continue
        entry = {"iol_power": None if val is None else round(val, 2)}
        if name == "Haigis":
            entry["low_confidence"] = inp.a0 is None
            entry["note"] = ("a0 derivado da A-constante (a1=0.4, a2=0.1); pode desviar ~1 D. "
                             "Use tripla otimizada do IOLCon para valer." if inp.a0 is None else "tripla de constantes informada")
        out[name] = entry
    powers = [v["iol_power"] for v in out.values() if v.get("iol_power") is not None and not v.get("low_confidence")]
    envelope = {"min": min(powers), "max": max(powers), "spread": round(max(powers) - min(powers), 2)} if powers else None
    return {"inputs": asdict(inp), "k_mean_1.3375": round(_k_1_3375(inp), 2), "results": out, "envelope": envelope}


def _from_json(path: str, eye: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    e = data["eyes"][eye]
    return {
        "al": e["AL"], "k1": e["K1"]["D"], "k2": e["K2"]["D"], "acd": e.get("ACD"),
        "k_index": e.get("K_index", K_INDEX_DEFAULT),
        "a_const": data.get("plan", {}).get("A_constant"), "target": data.get("plan", {}).get("target_refraction", 0.0),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="biometria.json produzido por parse_biometry.py")
    ap.add_argument("--eye", choices=["OD", "OS"], default="OD")
    ap.add_argument("--al", type=float); ap.add_argument("--k1", type=float); ap.add_argument("--k2", type=float)
    ap.add_argument("--acd", type=float); ap.add_argument("--a-const", type=float); ap.add_argument("--target", type=float)
    ap.add_argument("--k-index", type=float, default=None, help="1.3375 (padrão) ou 1.332 (IOLMaster com índice Zeiss)")
    ap.add_argument("--a0", type=float); ap.add_argument("--a1", type=float, default=0.4); ap.add_argument("--a2", type=float, default=0.1)
    args = ap.parse_args(argv)

    base = _from_json(args.json, args.eye) if args.json else {}
    for key in ("al", "k1", "k2", "acd", "a_const", "target", "k_index"):
        cli = getattr(args, key)
        if cli is not None:
            base[key] = cli
    base.setdefault("target", 0.0)
    base.setdefault("k_index", K_INDEX_DEFAULT)
    missing = [k for k in ("al", "k1", "k2", "a_const") if base.get(k) is None]
    if missing:
        print(f"ERRO: faltam entradas obrigatórias: {missing}", file=sys.stderr)
        return 2
    inp = Inputs(al=base["al"], k1=base["k1"], k2=base["k2"], a_const=base["a_const"], target=base["target"],
                 acd=base.get("acd"), k_index=base["k_index"], a0=args.a0, a1=args.a1, a2=args.a2)
    print(json.dumps(compute_all(inp), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
