# iol-calculadoras

Skill para o **Claude Code** que automatiza o cálculo de lente intraocular (LIO) de ponta a
ponta: laudo de biometria → JSON desidentificado → validação de faixas → pré-cálculo local →
preenchimento das calculadoras online pelo Chrome do cirurgião → cruzamento → relatório.

> Ferramenta de apoio. A decisão do implante é do cirurgião. Nada aqui substitui a
> conferência do laudo original e das telas de cada calculadora.

## O que ela faz

1. **Lê o laudo** (IOLMaster 500/700, Lenstar, Argos, Pentacam AXL, Anterion; PDF, foto ou
   texto) com `scripts/parse_biometry.py` (PyMuPDF; OCR com tesseract se preciso) e produz
   `biometria.json` sem nome, CPF ou prontuário.
2. **Valida** faixas fisiológicas, unidades, índice ceratométrico, ACD epitélio×endotélio,
   diferenças interoculares, qualidade (SNR/SD) e presença de identificadores
   (`scripts/validate_biometry.py`).
3. **Pré-calcula localmente** SRK/T, Holladay 1, Hoffer Q e Haigis (`scripts/iol_formulas.py`)
   para ter um envelope de referência e pegar erro de digitação nos sites.
4. **Preenche as calculadoras** pelo Chrome real do usuário (extensão Claude in Chrome):
   ESCRS multi-fórmula (Barrett, Cooke K6, EVO, Hill-RBF, Hoffer QST, Kane, PEARL-DGS),
   Barrett Universal II (APACRS), Kane, e as demais sob demanda. Perguntas ao médico são
   fechadas e numa rodada só; depois roda em pipeline multi-aba até o fim.
5. **Cruza e relata** (`scripts/crosscheck.py`): tabela fórmula × poder × refração prevista ×
   fonte, mediana, alertas (spread alto, resultado fora do envelope local), constantes usadas.

## Estrutura

```
SKILL.md                      fluxo principal (perguntas fechadas, pipeline, regras)
scripts/
  parse_biometry.py           laudo → biometria.json
  validate_biometry.py        OK / WARN / BLOCK
  iol_formulas.py             SRK/T, Holladay 1, Hoffer Q, Haigis
  crosscheck.py               web × local, alertas, relatorio.md
references/
  calculadoras.md             playbook por site (URL, campos, quirks, lições de execução)
  biometros.md                layout dos laudos, definições de K/ACD por aparelho, faixas
  barreiras.md                termos, login, CAPTCHA, SPAs, unidades, pipeline multi-aba
assets/
  biometry.schema.json        schema do JSON desidentificado
  lentes_frequentes.json      catálogo de lentes (nomes exatos da ESCRS) e lente padrão
  perguntas_plan.md           gabarito da rodada única de perguntas
```

## Instalação

```bash
git clone https://github.com/maurogobira19-png/iol.calculator ~/.claude/skills/iol-calculadoras
python3 -c "import fitz, pytesseract"   # PyMuPDF e pytesseract; tesseract via brew/apt
```
Requer Claude Code (desktop ou CLI) com a extensão **Claude in Chrome** conectada.
Edite `assets/lentes_frequentes.json` → `padrao` com a sua lente de rotina.

## Uso

Cole ou anexe o laudo e diga, por exemplo: "calcula a lente desse paciente, alvo −0.25".
A skill mostra a transcrição, faz uma rodada de perguntas fechadas (alvo, calculadoras,
autorização dos disclaimers, sexo se o laudo não tiver), roda tudo e devolve o relatório.
Login e CAPTCHA são os únicos passos que voltam para o médico.

## Privacidade

- Nenhum identificador do paciente vai para site algum; só um código interno.
- A ESCRS declara armazenar dados biométricos anonimizados por pelo menos um ano; o
  Hill-RBF (Haag-Streit) declara armazenar por cinco anos. Está documentado em
  `references/calculadoras.md`.
- Termos de uso de Kane, Hill-RBF e Cooke K6 limitam o uso às operações clínicas do próprio
  usuário. Esta skill se destina a esse uso.

## Estado (2026-09)

Exercitados ao vivo: ESCRS, Barrett APACRS, Kane. Os demais sites têm levantamento de
campos mas não execução real; o que não foi verificado está marcado nos arquivos.
Limitações conhecidas: a coluna Barrett não veio na ESCRS em uma execução; a extensão do
Chrome não salva screenshots em disco (prints ficam inline no chat).

## Licença

CC BY-NC 4.0 (atribuição, uso não comercial). Ver `LICENSE`.
