---
name: iol-calculadoras
description: Automatiza o cálculo de lente intraocular (LIO) de ponta a ponta — lê o laudo de biometria (IOLMaster, Lenstar, Argos, Pentacam AXL; PDF, imagem ou texto), desidentifica, valida faixas fisiológicas, pré-calcula localmente (SRK/T, Holladay 1, Hoffer Q, Haigis) e então preenche automaticamente as calculadoras online principais (ESCRS multi-fórmula, Barrett Universal II / True-K / Toric, Kane, Hill-RBF, EVO, Hoffer QST, Cooke K6, PEARL-DGS, Ladas, ASCRS pós-refrativa) pelo Chrome do usuário via MCP, lê os resultados, cruza tudo e entrega um relatório por olho com alertas. Use SEMPRE que o usuário falar em biometria, cálculo de LIO/IOL, "roda o Barrett", "joga na calculadora", "calcula a lente", planejamento de catarata, olho pós-LASIK/RK para LIO, tórica, ou pedir para comparar fórmulas para um paciente — mesmo que ele não diga "calculadora". Também use quando ele anexar um PDF/foto de IOLMaster ou Lenstar.
---

# Cálculo de LIO automatizado (biometria → calculadoras web → relatório)

Você está fazendo o trabalho que um residente faz antes da cirurgia de catarata: pegar o
laudo de biometria, digitar em várias calculadoras, comparar e montar a folha de
planejamento. A parte que dá errado na vida real é sempre a transcrição (K em mm, olho
trocado, lente errada no dropdown). Por isso o fluxo tem **checagem antes** (validador +
fórmulas locais) e **checagem depois** (crosscheck contra o envelope local, captura de
tela de cada resultado). A automação do browser é o meio; a evidência conferível é o fim.

Base da skill: `~/.claude/skills/iol-calculadoras/` (SKILL_DIR). Scripts em `SKILL_DIR/scripts`.
Trabalhe numa pasta de caso: `~/Documents/LIO/<code>/` (crie se não existir), um
`biometria.json`, um `results_<eye>.json` por olho, capturas `.png`, e `relatorio.md`.

## Regras que não se negociam

- **Sem identificação do paciente em site nenhum.** O laudo tem nome; o JSON e os
  formulários web só levam `patient.code` (ex.: `P-2026-091`). `validate_biometry.py`
  bloqueia se houver campo `name/nome/cpf/prontuario`. Se o site tiver campo "Patient
  name / ID", preencha com o code.
- **Sem senha, sem burlar termos.** Login é do médico. CAPTCHA: peça com pergunta
  fechada ("Feito" / "Pular site") e retome; não gaste turnos explicando.
- **Toda outra barreira é sua para resolver, não do médico.** Widget que não aceita
  valor, campo obrigatório inesperado, postback que limpa o form: tente as técnicas de
  `references/barreiras.md` §4 (inclui `.click()` via JS em item de lista MudBlazor)
  antes de pedir ajuda. Depois grave a solução na seção "Lições de execução" do site em
  `references/calculadoras.md` para não bater de novo.
- **Aceitar disclaimer clínico = pedir permissão uma vez por sessão**, listando os sites.
- **Nunca digite um valor que você não conferiu no laudo.** O parser é primeiro passo;
  a conferência visual da página do PDF é obrigatória (passo 2).
- **Perguntas só fechadas e só uma rodada.** `AskUserQuestion` com opções; nunca lista
  numerada em prosa pedindo resposta. O médico clica, a skill roda até o fim.
- **A decisão do implante é do cirurgião.** O relatório recomenda um envelope e um
  poder mediano com ressalvas; não "prescreve".

## Fluxo

### 0. Preparação: só perguntas fechadas, uma rodada, depois roda tudo sozinho
O médico não quer conversar; quer clicar 4 vezes e receber a folha pronta. Por isso:
**tudo que falta para o `plan` é perguntado numa única chamada de `AskUserQuestion`,
com opções fechadas**, e a partir daí a skill só volta a falar com ele por barreira
(CAPTCHA/login) ou no relatório final. Nunca faça pergunta aberta em prosa.

1. Confirme o browser: use `claude-in-chrome` (Chrome real, sessões logadas). Se as
   ferramentas estiverem deferred, carregue de uma vez com ToolSearch:
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__find,mcp__claude-in-chrome__form_input,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch`.
   Só caia para `Claude_Browser` (browser interno, sem sessões) se a extensão não estiver
   conectada, e avise que sites com login não vão funcionar.
2. Extraia da mensagem o que ele já disse (lente, alvo, "todas"). O que faltar vai para
   **uma** `AskUserQuestion` com até 4 perguntas, nesta ordem de prioridade
   (`assets/perguntas_plan.md` tem o gabarito pronto com opções):
   - **LIO** — **não pergunte** se `assets/lentes_frequentes.json` tem `padrao` e a
     mensagem não cita outra lente: use a padrão. Só pergunte se não houver padrão ou se
     ele citar uma lente diferente; nesse caso as opções vêm de `frequentes_menu` (nomes
     exatos da ESCRS) + "Outra". Constante: deixe a ESCRS preencher (otimizada IOLCon) e
     reutilize o valor mostrado no Barrett/Kane. Atualize `padrao` quando ele mudar.
   - **Alvo refrativo** — "Emetropia (−0.25)", "Miopia leve (−0.50)", "Monovisão (−1.50)", "Outro".
   - **Perfil do paciente** — multiSelect: "Mulher", "Homem", "Pós-LASIK/PRK", "Pós-RK",
     "Tórica". Idade vai no campo "Other" se ele quiser.
   - **Calculadoras + termos** — "Padrão: ESCRS + Barrett + Kane (aceitar termos)",
     "Todas as 10 (aceitar termos)", "Só ESCRS (aceitar termos)". A escolha já vale
     como autorização de sessão para aceitar os disclaimers dos sites listados.
3. Se a resposta cobrir tudo, **não pergunte mais nada**. Idade ausente → deixe em branco
   nos sites que aceitam e anote. Sexo ausente → "Not provided" onde houver a opção.

### 1. Ingestão do laudo
```bash
python3 SKILL_DIR/scripts/parse_biometry.py <laudo.pdf|png|txt> --code <code> --out ~/Documents/LIO/<code>/biometria.json
```
- PDF escaneado/foto → adicione `--ocr`. Saída ruim → `--dump-text` e monte o JSON à mão
  seguindo `assets/biometry.schema.json`.
- Layout por aparelho e armadilhas (TK vs SimK, ACD do epitélio, índice 1.332 do
  IOLMaster, Argos com AL segmentado): `references/biometros.md`. Leia a seção do
  aparelho detectado.

### 2. Conferência visual (obrigatória, mas fechada)
Abra o laudo como imagem (Read no PDF/PNG; se veio colado no chat, use a própria imagem)
e compare campo a campo com o JSON: AL, K1, K2 e eixos, ACD, LT, WTW, CCT, OD/OS, LS
(status do cristalino). Corrija o JSON. Se o laudo veio como imagem no chat, monte o JSON
à mão direto (o parser precisa de arquivo) e marque `source_file` como "transcrição manual".

**Olho pseudofácico (LS: Pseudophakic, LT < 1.5 mm, ACD > 4.5):** não é erro, é olho já
operado. Marque `"skip": "pseudofacico"` nesse olho no JSON e calcule só o outro. Só
calcule nele se o médico disser que é troca de LIO.

Mostre a tabela OD/OS compacta e feche o checkpoint com `AskUserQuestion` de uma
pergunta: "Transcrição confere?" → "Sim, roda" / "Corrigir (digito o campo em Other)".
Junte essa pergunta na mesma chamada do passo 0 quando possível (uma rodada só).

### 3. Validação e pré-cálculo local
```bash
python3 SKILL_DIR/scripts/validate_biometry.py biometria.json
python3 SKILL_DIR/scripts/iol_formulas.py --json biometria.json --eye OD   # e OS
```
- `BLOCK` → não prossiga; mostre os achados e pergunte. `WARN` → mostre e siga.
- Guarde o envelope local (min–max de SRK/T, Holladay 1, Hoffer Q) por olho. Ele é sua
  referência para pegar erro de digitação no site (passo 5).

### 4. Preencher as calculadoras — em pipeline, todas as abas de uma vez
As ações no browser são sequenciais, mas o que custa tempo é **esperar** (página
carregar, resultado renderizar, médico clicar CAPTCHA). Então não faça um site por vez:
trabalhe em fases, com todas as abas abertas, para as esperas se sobreporem. Três sites
caem de ~5 min para ~1 min; dez sites cabem em ~3 min.

**Fase A — abrir tudo.** Um `browser_batch`: `tabs_create_mcp` + `navigate` para cada
site escolhido. Depois um segundo batch: aceitar termos em todas (já autorizado na
rodada de perguntas) e `read_page`/`find` para mapear campos de cada aba.
**Fase B — preencher tudo.** Um `browser_batch` por site (ou vários sites no mesmo
batch, alternando `tabId`), preenchendo **sem** clicar Calculate e sem esperar resultado.
Termine cada aba com o eco de volta via JS (valores por nome/label).
**Fase C — calcular tudo.** Um batch clicando Calculate em cada aba. Se a ESCRS abrir o
reCAPTCHA, faça a única pergunta fechada da fase ("Feito") enquanto os outros sites já
calculam.
**Fase D — colher tudo.** Um batch com `get_page_text` + `screenshot` de cada aba.
Registre em `results_<eye>.json` e siga para o cruzamento.
Segundo olho: repita B→D nas mesmas abas (EDIT na ESCRS; sobrescrever campos nos demais).
Se um site quebrar no meio, não pare os outros: anote-o como pendente e resolva no fim.

Para cada calculadora, o **playbook de campos** (URL, ordem dos campos, unidade esperada,
como escolher a lente, onde está o resultado) está em `references/calculadoras.md`.
Padrão de operação em qualquer aba:
1. `navigate` → `wait` até renderizar → `read_page` (filter interactive) para mapear
   os campos por label. Nunca use coordenadas de screenshot para campos de formulário.
2. Preencha na ordem do site. Em SPAs: clique no campo, `type`, `Tab`.
3. **Eco de volta antes de calcular:** `read_page` e confira que cada campo mostra o
   valor certo (é aqui que se pega "23,45" virando "2345" ou o dropdown na lente errada).
4. Clique Calculate. `wait` 1–2 s. `find` pelo texto do resultado.
5. Extraia com `get_page_text`; se for imagem, `screenshot` + `zoom`. Escolha o poder cuja
   refração prevista fica mais perto do alvo (tabelas listam vários). **Sempre** tire
   `screenshot` com `save_to_disk: true` da região do resultado e copie para a pasta do
   caso como `<code>_<eye>_<calc>.png`: é o print que o médico vai querer ver.
6. Registre em `results_<eye>.json` (formato no cabeçalho de `scripts/crosscheck.py`),
   incluindo `source` e o nome do arquivo da captura.
7. Antes do próximo olho, limpe/sobrescreva **todos** os campos, inclusive opcionais.
8. Não narre cada site no chat. Fale só se bateu numa barreira que exige o médico
   (login/CAPTCHA) ou quando terminar.

Barreira (termos, login, CAPTCHA, campo que não aceita, resultado em PDF, rate limit):
seção correspondente em `references/barreiras.md`. Duas barreiras seguidas no mesmo
site → modo manual assistido (seção 11) em vez de insistir.

### 5. Cruzamento e relatório
```bash
python3 SKILL_DIR/scripts/crosscheck.py results_OD.json --biometry biometria.json --md relatorio_OD.md
```
- `BLOCK` = alguma calculadora web caiu > 1.5 D fora do envelope local: volte naquele
  site, refaça conferindo campo a campo (quase sempre é índice de K, lente ou olho
  trocado). Não entregue relatório com BLOCK sem explicar.
- `WARN` de spread > 1 D entre fórmulas modernas = olho atípico; diga qual fórmula tem
  melhor evidência para o perfil (curto: Kane/EVO/Hoffer QST; longo: Barrett/Kane/EVO;
  pós-LASIK miópico: Barrett True-K no-history / ASCRS média; K extremo: cuidado com RBF
  out-of-bounds). Não invente evidência: se não tiver certeza, diga que é regra geral.
- Entregue `relatorio.md` (OD + OS) com: tabela fórmula × poder × refração prevista ×
  fonte, mediana, poder disponível mais próximo, alertas, quais constantes foram usadas
  e de onde, lista das capturas. No chat: a tabela resumida por olho + os prints de cada
  calculadora enviados com `SendUserFile` (todos numa chamada, legenda = nome do site)
  + o caminho da pasta do caso. Nada de perguntar "quer que eu…" no final.

## Como o resultado final deve parecer (por olho)

| Fórmula | Poder (D) | Refr. prevista | Fonte |
|---|---|---|---|
| Barrett Universal II | 21.00 | −0.31 | calc.apacrs.org |
| Kane | 21.00 | −0.28 | iolformula.com |
| EVO 2.0 | 21.50 | −0.62 | ESCRS |
| SRK/T (local) | 20.94 | — | iol_formulas.py |

Mediana 21.0 D · spread 0.5 D · alvo −0.25 · LIO SN60WF A=118.7 (IOLCon otimizada) ·
alertas: nenhum · capturas: 3.

## Quando algo não se encaixa
- Laudo de aparelho que o parser não conhece: `--dump-text`, monte o JSON manualmente,
  e anote no relatório "transcrição manual conferida".
- Pós-refrativa sem dados pré-op: use os módulos "no history" (Barrett True-K, ASCRS)
  e diga isso no relatório.
- Tórica: rode Barrett Toric (APACRS) e o módulo tórico da ESCRS; inclua eixo e SIA que
  o usuário informar (pergunte SIA; padrão comum 0.1 D, mas ele decide).
- Lote de pacientes: um caso por vez, pasta por code, ESCRS como triagem, demais sites
  só nos olhos com spread > 1 D (ver barreiras §9).

## Arquivos
- `scripts/parse_biometry.py` — laudo → biometria.json (PyMuPDF; OCR tesseract se preciso)
- `scripts/validate_biometry.py` — faixas, unidades, interocular, PHI → OK/WARN/BLOCK
- `scripts/iol_formulas.py` — SRK/T, Holladay 1, Hoffer Q, Haigis (checagem local)
- `scripts/crosscheck.py` — web vs local, alertas, relatório markdown
- `references/calculadoras.md` — playbook por site (URL, campos, quirks, onde está o resultado)
- `references/biometros.md` — layout dos laudos, definições de K/ACD por aparelho, faixas
- `references/barreiras.md` — termos, login, CAPTCHA, SPA, unidades, PDF, rate limit
- `assets/biometry.schema.json` — schema do JSON desidentificado
