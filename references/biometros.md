# Laudos de biometria por aparelho: o que ler, o que não confundir

Leia a seção do aparelho detectado por `parse_biometry.py` (campo `device`). O que está
marcado **[não verificado]** veio de literatura secundária, não do manual do fabricante:
confira no laudo real na primeira vez.

## Índice
- Regras que valem para todos
- Zeiss IOLMaster 700
- Zeiss IOLMaster 500
- Haag-Streit Lenstar LS900 / EyeSuite
- Alcon Argos
- Heidelberg Anterion
- Oculus Pentacam AXL / AXL Wave
- Topcon Aladdin · Nidek AL-Scan · Tomey OA-2000
- Índice ceratométrico que cada fórmula espera
- Faixas de sanidade (fonte do validador)
- Parsers open-source úteis

## Regras que valem para todos
1. **ACD que as fórmulas querem = epitélio → cristalino (inclui CCT).** Alguns aparelhos
   imprimem a profundidade aquosa (endotélio → cristalino) com outro nome: `AD` (Lenstar),
   `AQD` (Anterion), `ACD (int.)` (Pentacam). Se só houver essa, ACD = AD + CCT/1000.
   O parser grava `ACD_reference` e o validador avisa.
2. **K padrão = SimK anterior no índice do laudo.** Não cole TK/TSE (IOLMaster 700) nem
   TCP/TrueNetPower (Anterion/Pentacam) em campo K comum. Só em campo rotulado TK
   (Barrett TK, EVO/Kane "posterior K" em campo próprio).
3. **K pode vir em mm (raio R1/R2).** D = (n − 1)·1000 / r; com 1.3375 → 337.5 / r.
   Use o índice impresso no laudo ("n = 1.3375"). O parser converte e sinaliza.
4. **Lateralidade:** OD/OS (Zeiss, Haag-Streit, Heidelberg); R/L provável em Tomey/Nidek
   [não verificado]. Laudos em colunas lado a lado: 1º valor = OD, 2º = OS — confira
   visualmente sempre, é o erro clássico.
5. **Idade e sexo** entram em Kane, Hill-RBF, Hoffer QST e ESCRS. O laudo traz data de
   nascimento; grave só idade em anos no JSON.

## Zeiss IOLMaster 700 (SS-OCT)
- **Exportações:** PDF (2 páginas), **CSV** ("BiometryData.csv", uma linha por medida/olho —
  melhor fonte se disponível), XML (HIC SOAP, PhacoOptics), DICOM (OAM `…78.7`,
  Keratometry `…78.3`, IOL calc `…78.8`, PDF encapsulado; tags privadas `771B` "CZM IOLM").
- **Layout do PDF:** cabeçalho com LS (status do cristalino), Vitreous, LVC, Target ref., SIA.
  Por olho, em colunas OD | OS: `AL` (mm, com SD), `ACD` (mm, SD), `LT` (mm, SD), `WTW`,
  `CCT`; bloco de K: `SE, K1, K2, ΔK, eixo` e, se licenciado, `TSE, TK1, TK2, ΔTK`.
- **ACD:** DICOM "Front Of Cornea To Front Of Lens" = epitélio → cristalino. Use direto.
- **Qualidade:** **não tem SNR útil** (grava "1.0" por compatibilidade). Use o SD: AL SD >
  0.027 mm é alerta na literatura; indicadores pass/warning/fail no laudo. O validador
  ignora SNR neste aparelho e usa `AL_SD` se presente.
- **Índice:** 1.3375 de fábrica; pode estar em 1.332 (configuração) — leia "n =" no laudo.
- Argos-style "sum of segments"? Não; o 700 usa índice equivalente. Não marque flag Argos.

## Zeiss IOLMaster 500 (PCI)
- **Exportações:** impressão, texto CSV (separador configurável), XML, DICOM (PDF
  encapsulado + tags privadas `771B`; importador OpenEyes lê `771B1001`, `771B1034`).
- **Layout:** `AL`, `ACD`, `WTW`, `K1`, `K2` (D + eixo), `ΔK`, R1/R2 em mm; leitura editada
  marcada com `*`, cálculo com `**`.
- **ACD:** secção óptica, epitélio → cristalino (só fácicos).
- **Qualidade (manual):** SNR por leitura: **< 1.6 = Error**, **1.6–1.9 = "Borderline
  value!" com (!)**, > 10 muito bom; semáforo verde/amarelo/vermelho. Composto < 10 pede
  cautela; alguns SOPs exigem > 100. Validador: < 1.6 BLOCK, < 2.0 WARN.
- **Índice:** configurável; manual manda casar com o ceratômetro externo. Leia no laudo.

## Haag-Streit Lenstar LS900 / EyeSuite
- **Exportações:** texto/XML definível pelo usuário, PDF, DICOM, GDT; EyeSuite Script
  Language com tags `{AL} {CCT} {AD} {LT} {RT} {K1}/{KFLAT} {K2}/{KSTEEP} {R1} {R2}
  {AXIS1} {AXIS2} {AST} {AXISAST} {WTW} {PD}`, prefixo `OD_`/`OS_`, sufixo `_SD`. Se a
  clínica exporta texto, peça esse arquivo — é o mais fácil de parsear.
- **Armadilha principal:** imprime **`AD` = aqueous depth (endotélio → cristalino)** E
  **`ACD` = CCT + AD**. Use `ACD`. O parser prefere `ACD`; se só achar `AD`, soma CCT.
- **K:** dois anéis (1.65/2.3 mm), `R1/R2` em mm, D e eixo, `AST`; índice impresso
  ("n"), padrão 1.3375 [configurabilidade não verificada].
- **Qualidade:** sem SNR; SD por parâmetro; modo catarata densa (DCM) marca com
  triângulo/linha amarela. Manual avisa que o usuário deve conferir o olho atribuído.

## Alcon Argos (SS-OCT, sum-of-segments)
- **Exportações:** PDF/impressão, USB/LAN, integração Alcon (Vision Planner,
  SMARTCataract). XML/CSV/DICOM [não verificados] → planeje PDF/OCR.
- **AL por segmentos** (córnea 1.376, aquoso/vítreo 1.336, cristalino 1.410): marque a
  flag **"Argos (SoS) AL"** em EVO, Cooke K6 e ESCRS. Barrett/Kane não têm flag: o AL do
  Argos tende a ser mais curto em olhos longos e mais longo em curtos que o do IOLMaster
  (compensação de Wang-Koch não se aplica igual) — anote no relatório.
- **K:** anel 16 LEDs 2.2 mm, n = 1.3375. **ACD:** epitélio → cristalino [redação da
  IFU não verificada]; lê ~0.1 mm mais fundo que o IOLMaster 700.
- Rótulos: `AL, K1, K2, CCT, ACD, LT, WTW, PS`.

## Heidelberg Anterion (Cataract App)
- **Exportações:** PDF "Cataract Key Measurement Report"; DICOM Key Measurements (OAM,
  Keratometry, IOL calc, PDF encapsulado); CSV via research export [não verificado].
- **ACD:** mede **`AQD`** (endotélio → cristalino). Rótulo `AQD (ACD)`. ACD para fórmulas
  = AQD + CCT (≈ IOLMaster + 0.07 mm). Parser: se achar `AQD`, soma CCT e marca.
- **K:** `SimK mean`/`Rmean` (anel 3 mm) é o que vai nas fórmulas; `Kmean` posterior,
  `P/A ratio`, `TCP` não. **Qualidade:** Pass/Borderline; AL SD < 0.02 mm.

## Oculus Pentacam AXL / AXL Wave
- **Exportações:** PDF; CSV/U12 do software [nomes de campo não verificados]; DICOM 2024
  (PDF encapsulado, OAM, Keratometry).
- **ACD: dois valores** — `ACD (int.)` endotélio → cristalino e `ACD (ext.)` epitélio →
  cristalino. **Use `ext.`** O parser captura o sufixo; se só vier `int.`, soma CCT.
- **K:** SimK (1.3375) para fórmulas; TrueNetPower/TCRP não. Flag `QS = OK`.

## Topcon Aladdin · Nidek AL-Scan · Tomey OA-2000
- **Aladdin:** PDF; DICOM só PDF encapsulado. Rótulos `AL, K1, K2, ACD, LT, CCT, WTW, PD`;
  K Placido 2.4–3.4 mm, 1.3375. ACD epitélio → cristalino [não verificado]. Scans de AL
  aceitáveis destacados em amarelo.
- **AL-Scan:** impressão, NAVIS-EX. `K (2.4 e 3.3 mm), AL, PS, WTW, CCT, ACD`. **ACD:
  fontes conflitam (endotélio vs epitélio)** — confira no laudo se ACD − CCT bate com
  alguma outra linha; na dúvida pergunte ao usuário como o aparelho está configurado.
- **OA-2000:** PDF; CSV/JPEG via software "DATA Transfer". `K1/K2` (mm ou D), Ave K, Cyl,
  Axis, `AL, ACD, LT, CCT, WTW, PD`; ACD epitélio → cristalino (literatura). SNR impresso;
  recomenda-se > 3 (validador: < 3 WARN). Lateralidade provável R/L.

## Índice ceratométrico que cada fórmula espera
| Fórmula | Índice | Observação |
|---|---|---|
| Barrett UII | seletor 1.3375 / 1.332 | ACD epitélio→cristalino; LT e WTW opcionais |
| Kane | seletor, padrão 1.3375 | exige sexo; LT/CCT opcionais; K posterior em campo próprio |
| Hill-RBF 3.0 | seletor `n` (1.3315…1.3380); treinado em Lenstar a 1.3375 | alvo −2.5…+1.0; K 37–52 |
| Hoffer QST | seletor 1.3375/1.332/1.3315 | pACD, não A-constante |
| EVO 2.0 | seletor 1.3375/1.3315/1.332 | flag Argos; K posterior opcional |
| Cooke K6 / PEARL-DGS | 1.3375 padrão, editável | K6 tem radio de biômetro (Argos) |
| ESCRS | 1.3375 padrão, seletor | validado a 1.3375 |
| SRK/T, Holladay 1, Hoffer Q (locais) | 337.5/r | `iol_formulas.py` reexpressa a partir de `K_index` |
| Haigis (local) | 1.3315 interno | tripla otimizada do IOLCon ou fica "baixa confiança" |

Regra prática: **alimente SimK anterior no índice do laudo e selecione esse índice no
site.** Zeiss diz explicitamente que TK não pode ir em Haigis-L / Barrett True-K LVC.

## Faixas de sanidade (fonte do validador)
| Parâmetro | Típico adulto | Alerta / repetir |
|---|---|---|
| AL | 21.5–26.4 mm | SOP NHS repete se < 21.2 ou > 26.6; interocular > 0.3 mm; scans consecutivos > 0.2 mm; limites duros 14–38 |
| K médio | 41–47 D | interocular > 0.9–1.0 D; ΔK > 2.5 D → topografia; K > 47 → excluir ceratocone |
| ACD (epi–lente) | 3.1 ± 0.5 mm | ≤ 2.6 mm avisar cirurgião (NHS); Kane: rasa ≤ 3.0, funda ≥ 3.5 |
| LT | 4.4 ± 0.4 mm | 0.17 mm de erro ≈ 1 D; cresce com idade |
| WTW | 11.0–12.8 mm | fora de 10.5–13 suspeito [convenção] |
| CCT | 474–608 µm | — |
| Qualidade | IOLMaster 500 SNR (ver acima); IOLMaster 700 AL SD > 0.027; Anterion SD < 0.02; Lenstar SD alto/DCM; OA-2000 SNR > 3 | — |
Também: diferença de poder de LIO entre olhos ≥ 0.9 D e biometria com > 4 anos → revisar.

## Parsers open-source úteis (se o regex genérico falhar)
- `OCVL/IOLM_Parser` (Python): IOLMaster PDF → CSV (ID, data, AL, K, ACD).
- `sasa233333a/zeiss-iolmaster-extractor` (Go, 2026): IOLMaster 700 e V7.7 PDF → CSV.
- `peopleatkorea-droid/IOLmaster_conversion` (Python, 2026): CSV de exportação do 700 → XLSX
  por olho; K médio de R1/R2 com 337.5.
- `AppertaFoundation/IOLMasterImport` (Java, OpenEyes): DICOM 500/700 (`771B`) + regex
  no PDF (`"ACD: (.*)"`).
- Stanford "Ocular Biometry OCR" (PMC11743993): listas de campos por aparelho (Lenstar,
  IOLMaster 500/700); código não liberado. Sem parsers públicos para Argos, Anterion,
  Pentacam, Aladdin, AL-Scan, OA-2000.
