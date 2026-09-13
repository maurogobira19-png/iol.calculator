#!/usr/bin/env python3
"""
Consolida os resultados das calculadoras web (results.json, preenchido pela skill a
partir do que foi lido na tela) com o pré-cálculo local, e produz o relatório final.

Entrada results.json (um por olho ou com ambos), formato:
{
  "patient_code": "P-001", "eye": "OD", "target_refraction": -0.25,
  "lens_model": "SN60WF", "A_constant": 118.7,
  "web": {
     "Barrett Universal II": {"iol_power": 21.0, "predicted_refraction": -0.31, "source": "calc.apacrs.org", "screenshot": "od_barrett.png"},
     "Kane": {...}, "EVO 2.0": {...}, "Hill-RBF 3.0": {...}, "Hoffer QST": {...}, "Cooke K6": {...}, "PEARL-DGS": {...}
  },
  "local": { "SRK/T": {"iol_power": 20.95}, ... }   # opcional; se ausente, calcula a partir de biometria.json
}

Regras de alerta (heurísticas, ajustáveis):
  - spread entre fórmulas modernas > 1.0 D  → WARN "olho difícil" (curto/longo/K extremo/pós-refrativa)
  - fórmula web fora do envelope local por > 1.5 D → BLOCK provável erro de digitação naquela calculadora
  - predicted_refraction de alguma fórmula com sinal oposto ao alvo em > 0.75 D → WARN

Uso: python3 crosscheck.py results_od.json [--biometry biometria.json] [--step 0.5] [--md relatorio_od.md]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from iol_formulas import Inputs, compute_all  # noqa: E402

SPREAD_WARN = 1.0
LOCAL_DEVIATION_BLOCK = 1.5
PRED_REF_WARN = 0.75


def _local_from_biometry(biometry: dict, eye: str, target: float, a_const: float, haigis: dict | None) -> dict:
    e = biometry["eyes"][eye]
    inp = Inputs(al=e["AL"], k1=e["K1"]["D"], k2=e["K2"]["D"], a_const=a_const, target=target,
                 acd=e.get("ACD"), k_index=e.get("K_index", 1.3375),
                 a0=(haigis or {}).get("a0"), a1=(haigis or {}).get("a1", 0.4), a2=(haigis or {}).get("a2", 0.1))
    return compute_all(inp)["results"]


def crosscheck(res: dict, biometry: dict | None, step: float) -> dict:
    findings = []
    web = {k: v for k, v in res.get("web", {}).items() if v.get("iol_power") is not None}
    local = res.get("local")
    if not local and biometry is not None:
        local = _local_from_biometry(biometry, res["eye"], res.get("target_refraction", 0.0),
                                     res["A_constant"], res.get("haigis"))
    local = {k: v for k, v in (local or {}).items() if v.get("iol_power") is not None}
    # Envelope só com fórmulas confiáveis (Haigis sem tripla otimizada fica fora do envelope, mas aparece na tabela)
    envelope_local = {k: v for k, v in local.items() if not v.get("low_confidence")}

    web_powers = [v["iol_power"] for v in web.values()]
    local_powers = [v["iol_power"] for v in envelope_local.values()]
    summary: dict = {"n_web": len(web), "n_local": len(local)}

    if web_powers:
        summary["web_median"] = round(statistics.median(web_powers), 2)
        summary["web_min"], summary["web_max"] = min(web_powers), max(web_powers)
        summary["web_spread"] = round(max(web_powers) - min(web_powers), 2)
        if summary["web_spread"] > SPREAD_WARN:
            findings.append({"level": "WARN", "msg": f"Fórmulas modernas divergem {summary['web_spread']} D. Olho atípico: revisar biometria e considerar a fórmula com melhor evidência para este perfil."})
    if local_powers:
        summary["local_min"], summary["local_max"] = min(local_powers), max(local_powers)
    if web_powers and local_powers:
        lo, hi = min(local_powers), max(local_powers)
        for name, v in web.items():
            p = v["iol_power"]
            dev = p - hi if p > hi else (lo - p if p < lo else 0.0)
            if dev > LOCAL_DEVIATION_BLOCK:
                findings.append({"level": "BLOCK", "formula": name,
                                 "msg": f"{name} = {p} D está {dev:.2f} D fora do envelope local ({lo}-{hi}). Provável erro de digitação/índice nessa calculadora. Refaça e confira campo a campo."})
    target = res.get("target_refraction", 0.0)
    for name, v in web.items():
        pr = v.get("predicted_refraction")
        if pr is not None and abs(pr - target) > PRED_REF_WARN:
            findings.append({"level": "WARN", "formula": name,
                             "msg": f"{name}: refração prevista {pr:+.2f} vs alvo {target:+.2f}. Confira se o poder listado é o mais próximo do alvo (não o primeiro da tabela)."})

    # Sugestão de poder disponível (passo do fabricante), ficando do lado míope do alvo
    suggestion = None
    if web_powers:
        med = summary["web_median"]
        candidate = round(med / step) * step
        suggestion = {"median_power": med, "nearest_available": candidate, "step": step,
                      "note": "Escolha final é do cirurgião: em regra prefira o poder que deixa a refração prevista levemente míope, não hipermétrope."}
    levels = {f["level"] for f in findings}
    status = "BLOCK" if "BLOCK" in levels else ("WARN" if "WARN" in levels else "OK")
    return {"status": status, "summary": summary, "web": web, "local": local, "suggestion": suggestion, "findings": findings}


def to_markdown(res: dict, out: dict) -> str:
    lines = [f"## {res.get('patient_code','?')} — {res['eye']} — LIO {res.get('lens_model','?')} (A={res.get('A_constant','?')}) — alvo {res.get('target_refraction',0):+.2f} D", "",
             f"**Status:** {out['status']}", "", "| Fórmula | Poder (D) | Refração prevista | Fonte |", "|---|---|---|---|"]
    for name, v in out["web"].items():
        pr = v.get("predicted_refraction")
        lines.append(f"| {name} | {v['iol_power']:.2f} | {pr:+.2f} | {v.get('source','web')} |" if pr is not None else f"| {name} | {v['iol_power']:.2f} | — | {v.get('source','web')} |")
    for name, v in out["local"].items():
        tag = " ⚠ baixa confiança" if v.get("low_confidence") else ""
        lines.append(f"| {name} (local, checagem{tag}) | {v['iol_power']:.2f} | — | iol_formulas.py |")
    s = out["summary"]
    if "web_median" in s:
        lines += ["", f"Mediana das fórmulas modernas: **{s['web_median']} D** (spread {s['web_spread']} D)."]
    if out["suggestion"]:
        lines += [f"Poder disponível mais próximo (passo {out['suggestion']['step']}): **{out['suggestion']['nearest_available']} D**. {out['suggestion']['note']}"]
    if out["findings"]:
        lines += ["", "### Alertas"] + [f"- **{f['level']}** {f['msg']}" for f in out["findings"]]
    lines += ["", "_Cálculo automatizado a partir de biometria desidentificada. Conferido contra o laudo original e contra as capturas de tela de cada calculadora. A decisão do implante é do cirurgião._"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("--biometry")
    ap.add_argument("--step", type=float, default=0.5)
    ap.add_argument("--md")
    args = ap.parse_args(argv)
    res = json.loads(Path(args.results).read_text(encoding="utf-8"))
    bio = json.loads(Path(args.biometry).read_text(encoding="utf-8")) if args.biometry else None
    out = crosscheck(res, bio, args.step)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if args.md:
        Path(args.md).write_text(to_markdown(res, out), encoding="utf-8")
        print(f"relatório: {args.md}", file=sys.stderr)
    return 1 if out["status"] == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main())
