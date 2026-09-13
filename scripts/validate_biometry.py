#!/usr/bin/env python3
"""
Valida um biometria.json (schema em assets/biometry.schema.json) ANTES de qualquer
calculadora ser aberta. O objetivo é pegar erro de medida, de transcrição e de unidade,
que são as causas mais comuns de "surpresa refrativa" evitável.

Saída: JSON com "status" (OK | WARN | BLOCK) e lista de achados. BLOCK = não prossiga
sem o cirurgião confirmar; WARN = mostre ao cirurgião mas pode seguir.

Faixas: baseadas em populações adultas de catarata (ex.: Hoffer & Savini, Hoffer 2015;
protocolos de qualidade IOLMaster/Lenstar). São heurísticas, não diagnóstico.

Uso: python3 validate_biometry.py biometria.json
"""
from __future__ import annotations

import json
import sys

# (min_block, min_warn, max_warn, max_block)
RANGES = {
    "AL":  (18.0, 21.2, 26.6, 35.0),   # NHS SOP: repetir fora de 21.2-26.6
    "K":   (35.0, 40.0, 47.0, 52.0),   # >47 excluir ceratocone
    "ACD": (1.8, 2.6, 4.2, 5.5),       # ≤2.6 avisar cirurgião (NHS)
    "LT":  (2.5, 3.2, 5.5, 6.5),
    "WTW": (9.5, 10.8, 13.0, 14.0),
    "CCT": (380.0, 460.0, 640.0, 750.0),
}
MAX_INTEROCULAR_AL = 0.3   # mm — acima disso, biometria costuma ser repetida
MAX_INTEROCULAR_K = 0.9    # D (NHS SOP)
MAX_DELTA_K_WARN = 2.5     # D — astigmatismo corneano alto: toric? ceratocone?
SNR_IOLMASTER500_BLOCK = 1.6   # manual: <1.6 = Error
SNR_IOLMASTER500_WARN = 2.0    # 1.6-1.9 = "Borderline value!"
SNR_OA2000_WARN = 3.0
AL_SD_IOLMASTER700_WARN = 0.027  # mm; o 700 não tem SNR útil (grava 1.0)


def _check_range(name: str, value: float | None, findings: list, eye: str) -> None:
    if value is None:
        return
    lo_b, lo_w, hi_w, hi_b = RANGES[name]
    if value < lo_b or value > hi_b:
        findings.append({"level": "BLOCK", "eye": eye, "field": name, "value": value,
                         "msg": f"{name}={value} fora de faixa plausível ({lo_b}-{hi_b}). Provável erro de unidade/transcrição."})
    elif value < lo_w or value > hi_w:
        findings.append({"level": "WARN", "eye": eye, "field": name, "value": value,
                         "msg": f"{name}={value} atípico ({lo_w}-{hi_w}). Confirme no laudo original."})


def validate(data: dict) -> dict:
    findings: list[dict] = []
    eyes = data.get("eyes", {})
    for eye, e in eyes.items():
        if e.get("skip"):
            findings.append({"level": "INFO", "eye": eye, "field": "skip", "value": e["skip"],
                             "msg": f"{eye} marcado como '{e['skip']}': não entra no cálculo."})
            continue
        k1, k2 = e["K1"]["D"], e["K2"]["D"]
        _check_range("AL", e.get("AL"), findings, eye)
        for k in (k1, k2):
            _check_range("K", k, findings, eye)
        for f in ("ACD", "LT", "WTW", "CCT"):
            _check_range(f, e.get(f), findings, eye)

        delta_k = abs(k1 - k2)
        if delta_k > MAX_DELTA_K_WARN:
            findings.append({"level": "WARN", "eye": eye, "field": "ΔK", "value": round(delta_k, 2),
                             "msg": f"Astigmatismo corneano {delta_k:.2f} D. Considerar LIO tórica; excluir ectasia."})
        if k1 > k2:
            findings.append({"level": "INFO", "eye": eye, "field": "K1/K2", "value": None,
                             "msg": "K1 > K2 — convenção de alguns aparelhos. Não é erro, mas confira eixos ao usar tórica."})

        # Unidade de K: se veio em mm por engano (ex.: 7.8) o valor cai fora da faixa e já bloqueia.
        if e.get("K_index") not in (1.3375, 1.332, 1.3315, None):
            findings.append({"level": "WARN", "eye": eye, "field": "K_index", "value": e.get("K_index"),
                             "msg": "Índice ceratométrico incomum. Calculadoras assumem 1.3375; converta se necessário."})
        if e.get("K_type") == "TK":
            findings.append({"level": "WARN", "eye": eye, "field": "K_type", "value": "TK",
                             "msg": "K informado é Total Keratometry (TK). Só use TK em calculadoras que aceitam TK (ex.: Barrett TK); nas demais use SimK."})
        if e.get("ACD_reference") == "endothelium" and e.get("ACD") is not None:
            findings.append({"level": "WARN", "eye": eye, "field": "ACD", "value": e["ACD"],
                             "msg": "ACD medido do endotélio. Fórmulas modernas esperam epitélio→cristalino (some CCT/1000 ≈ +0.55 mm)."})

        snr, al_sd, device = e.get("AL_SNR"), e.get("AL_SD"), str(data.get("device", "")).lower()
        if snr is not None and "iolmaster 500" in device:
            if snr < SNR_IOLMASTER500_BLOCK:
                findings.append({"level": "BLOCK", "eye": eye, "field": "AL_SNR", "value": snr,
                                 "msg": f"IOLMaster 500: SNR {snr} < 1.6 = Error. Repetir biometria."})
            elif snr < SNR_IOLMASTER500_WARN:
                findings.append({"level": "WARN", "eye": eye, "field": "AL_SNR", "value": snr,
                                 "msg": f"IOLMaster 500: SNR {snr} borderline (1.6-1.9)."})
        elif snr is not None and "oa-2000" in device and snr < SNR_OA2000_WARN:
            findings.append({"level": "WARN", "eye": eye, "field": "AL_SNR", "value": snr,
                             "msg": f"OA-2000: SNR {snr} < 3. Qualidade de AL baixa."})
        elif snr is not None and "iolmaster 700" in device:
            pass  # o 700 grava SNR=1.0 por compatibilidade; não significa nada
        if al_sd is not None and al_sd > AL_SD_IOLMASTER700_WARN:
            findings.append({"level": "WARN", "eye": eye, "field": "AL_SD", "value": al_sd,
                             "msg": f"SD do AL = {al_sd} mm (> {AL_SD_IOLMASTER700_WARN}). Medida instável; conferir indicador de qualidade do laudo."})

        # Combinações fisiologicamente estranhas (sugerem troca de campo)
        al = e.get("AL")
        kmean = (k1 + k2) / 2
        if al is not None and ((al < 22.0 and kmean < 41.5) or (al > 26.0 and kmean > 46.0)):
            findings.append({"level": "WARN", "eye": eye, "field": "AL×K", "value": None,
                             "msg": f"Combinação incomum AL={al} / K={kmean:.2f}. Olhos curtos tendem a K alto e vice-versa. Confira se AL/K não foram trocados entre olhos."})

    if "OD" in eyes and "OS" in eyes and not eyes["OD"].get("skip") and not eyes["OS"].get("skip"):
        od, os_ = eyes["OD"], eyes["OS"]
        if od.get("AL") is not None and os_.get("AL") is not None:
            d_al = abs(od["AL"] - os_["AL"])
            if d_al > MAX_INTEROCULAR_AL:
                findings.append({"level": "WARN", "eye": "OU", "field": "ΔAL", "value": round(d_al, 2),
                                 "msg": f"Diferença interocular de AL = {d_al:.2f} mm (>{MAX_INTEROCULAR_AL}). Normal em anisometropia, mas confirme."})
        k_od = (od["K1"]["D"] + od["K2"]["D"]) / 2
        k_os = (os_["K1"]["D"] + os_["K2"]["D"]) / 2
        if abs(k_od - k_os) > MAX_INTEROCULAR_K:
            findings.append({"level": "WARN", "eye": "OU", "field": "ΔK interocular", "value": round(abs(k_od - k_os), 2),
                             "msg": "K médio difere >1 D entre olhos. Confirme."})

    plan = data.get("plan", {})
    if plan.get("A_constant") is not None and not (114.0 <= plan["A_constant"] <= 121.0):
        findings.append({"level": "BLOCK", "eye": "-", "field": "A_constant", "value": plan["A_constant"],
                         "msg": "A-constante fora de 114-121. Confira o modelo de LIO no IOLCon."})
    if plan.get("target_refraction") is not None and abs(plan["target_refraction"]) > 3.0:
        findings.append({"level": "WARN", "eye": "-", "field": "target_refraction", "value": plan["target_refraction"],
                         "msg": "Alvo refrativo >3 D em módulo. Intencional (monovisão alta / miopia prévia)?"})

    patient = data.get("patient", {})
    for forbidden in ("name", "nome", "cpf", "mrn", "prontuario"):
        if forbidden in {k.lower() for k in patient.keys()}:
            findings.append({"level": "BLOCK", "eye": "-", "field": "patient", "value": None,
                             "msg": f"Campo identificador '{forbidden}' presente. Desidentifique antes de enviar a qualquer site."})

    levels = {f["level"] for f in findings}
    status = "BLOCK" if "BLOCK" in levels else ("WARN" if "WARN" in levels else "OK")
    return {"status": status, "n_findings": len(findings), "findings": findings}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    result = validate(data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["status"] == "BLOCK" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
