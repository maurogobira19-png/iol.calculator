# Barreiras das calculadoras e como lidar com cada uma

Este arquivo é o "manual de campo". Leia-o inteiro na primeira vez que a skill rodar
numa sessão, e volte à seção específica quando bater numa barreira.

Princípio geral: **cooperar com o site, não enganá-lo.** A skill roda no Chrome do próprio
cirurgião (`claude-in-chrome`), com a conta dele, para os pacientes dele, no ritmo de um
humano rápido. Tudo que parece "burlar" (resolver CAPTCHA, esconder automação, contornar
login, raspar em massa) fica fora — além de violar termos, quebra na primeira atualização
do site e coloca em risco a conta do cirurgião. O ganho real está em eliminar digitação
manual e erro de transcrição, não em "vencer" o site.

## Índice
1. Termos de uso / disclaimer obrigatório
2. Login e sessão
3. CAPTCHA, Cloudflare e detecção de bot
4. Formulários SPA (React/Angular) que ignoram preenchimento programático
5. Dropdown de modelo de LIO e constantes
6. Unidades, índice ceratométrico, vírgula decimal
7. Limites de faixa e validação do próprio site
8. Resultado em imagem, canvas ou PDF
9. Tempo, rate limit e sessões que expiram
10. Multi-aba e ordem de execução
11. Quando desistir da automação e cair no manual assistido

---

## 1. Termos de uso / disclaimer obrigatório

**O que acontece:** quase todas (Barrett, Kane, Hill-RBF, EVO, ESCRS) exibem um aviso
"for clinical use by qualified professionals... you accept responsibility" com um botão
ou checkbox. Algumas pedem a cada carregamento; outras guardam em cookie.

**Como lidar:**
- Aceitar termos é ação que exige permissão explícita do usuário (regra do harness).
  Pergunte **uma vez no início da sessão**, listando os sites: "Vou precisar aceitar o
  disclaimer clínico de: APACRS Barrett, Kane, ESCRS. Autoriza para esta sessão?".
  Guarde o "sim" como válido só para esta sessão.
- Se o usuário já abriu a invocação dizendo "pode aceitar os termos", isso conta.
- Leia o texto do disclaimer antes de aceitar. Se ele proibir uso automatizado
  explicitamente, pare e mostre o trecho ao usuário; ele decide.
- Nunca clique "aceitar" via JavaScript escondido. Use o clique normal no elemento.

## 2. Login e sessão

**O que acontece:** Hill-RBF, ESCRS e ASCRS podem pedir conta (gratuita). Sessões expiram.

**Como lidar:**
- Nunca digite senha. Se a página mostrar formulário de login, pare: "A calculadora X
  pede login. Faça login no seu Chrome e me avise para continuar." Depois retome.
- Antes de começar a sessão, verifique com `read_page` se há indicador de usuário logado
  (nome, "logout", "my account"). Isso evita descobrir o login só na hora de submeter.
- Se a sessão cair no meio de uma lista de pacientes, salve o progresso em
  `results_<code>_<eye>.json` para cada olho já concluído; retomar é barato.

## 3. CAPTCHA, Cloudflare e detecção de bot

**O que acontece:** "Verify you are human", hCaptcha, reCAPTCHA v2/v3 invisível, página
de desafio do Cloudflare.

**Como lidar:**
- Não resolva, não tente ler a imagem, não use serviço de terceiros. Pare e diga:
  "Apareceu um CAPTCHA em <site>. Resolva no Chrome e me diga 'ok'." Depois retome.
- Use `AskUserQuestion` fechada para o pedido ("Feito" / "Pular este site"). No modo
  pipeline, dispare o Calculate dos outros sites antes de perguntar, para a espera do
  médico não travar o resto.
- Reduza a chance de aparecer: use o Chrome real do usuário (extensão), um paciente por
  vez, espere a página renderizar antes de agir, não abra 5 abas da mesma calculadora.
- reCAPTCHA v3 invisível pontua comportamento; preencher via `form_input` é aceito na
  maioria dos casos porque dispara eventos reais no DOM. Se o site rejeitar com erro
  genérico após submeter, é sinal de score baixo: peça ao usuário para clicar "Calcular"
  ele mesmo naquela aba (o resto continua automatizado).

## 4. Formulários SPA que ignoram preenchimento programático

**O que acontece:** campos React/Angular às vezes não "veem" valores setados direto no
`value`; o estado interno fica vazio e o cálculo sai com 0 ou dá erro de validação.
Sinal típico: você preenche, `read_page` mostra o valor, mas ao clicar Calculate o site
diz "campo obrigatório".

**Como lidar, nesta ordem:**
1. `find` o campo pelo label → `left_click` no campo → `type` o valor (simula digitação
   real, dispara `input`/`change`). Prefira isso a `form_input` em SPAs.
2. Após digitar, pressione `Tab` para disparar `blur` (muitos sites validam no blur).
3. Releia com `read_page` e confirme o valor **antes** de clicar em Calculate. Se o campo
   voltou a vazio, o site limpou no blur (formato inválido): veja seção 6.
4. Só em último caso use `javascript_tool` para disparar `new Event('input', {bubbles:true})`
   no elemento — e registre no relatório que precisou.

**Caso resolvido — MudBlazor `MudSelect` (ESCRS: Gender, Manufacturer):** clique por ref,
por coordenada, `form_input` (é DIV, não suportado) e teclado NÃO registram a opção. O
que funciona (verificado 2026-09-13):
```
1. left_click no combobox (abre o popover)          → wait 1 s
2. javascript_tool:
   const el=[...document.querySelectorAll('.mud-popover .mud-list-item')]
            .find(e=>e.textContent.trim()==='Female'); el && el.click()
3. conferir: [...document.querySelectorAll('.mud-select input')]
            .map(i=>i.closest('.mud-input-control')?.querySelector('label')?.textContent+'='+i.value)
```
O `MudAutocomplete` (Select IOL) aceita digitação normal + clique por ref na opção.
Para listar todas as opções de um autocomplete: clicar no campo, cmd+a, Backspace, ler
`.mud-popover .mud-list-item`.

## 5. Dropdown de modelo de LIO e constantes

**O que acontece:** a lista de lentes é longa, com nomes ligeiramente diferentes do que
o cirurgião fala ("SN60WF" vs "Alcon AcrySof IQ SN60WF"). Alguns sites usam a constante
do banco deles (ULIB/IOLCon), outros exigem que você digite a A-constante / Lens Factor.
Escolher a lente errada muda o resultado em 0,5–1,5 D e é silencioso.

**Como lidar:**
- Faça `find` com a parte inequívoca do nome (o código do fabricante: "SN60WF", "ZCB00").
  Se vier mais de um match (ex.: SN60WF vs SN6AT3), mostre as opções e escolha a exata.
- Após selecionar, leia a constante que o site preencheu e compare com `plan.A_constant`
  do biometria.json. Diferença > 0,3 é alerta: pergunte qual usar (a otimizada do cirurgião
  ou a do site) e anote no relatório qual foi usada.
- Se o site pede Lens Factor (Barrett) e você só tem A-constante, deixe o próprio site
  converter (o Barrett tem campo para A-constante que deriva o LF). Não converta à mão.
- Constantes: fonte canônica é https://iolcon.org. Nunca invente constante.

## 6. Unidades, índice ceratométrico, vírgula decimal

**O que acontece:** o erro mais perigoso e mais comum.
- K em mm (raio) onde o site espera D, ou vice-versa.
- K calculado com índice 1.332 (IOLMaster configurado assim) colado em site que assume
  1.3375: ~0,5 D de erro na LIO.
- Vírgula decimal brasileira ("23,45") rejeitada ou, pior, lida como 2345.
- ACD do endotélio (alguns tomógrafos) onde o site espera do epitélio: ~0,55 mm.
- CCT em mm em vez de µm.

**Como lidar:**
- `validate_biometry.py` roda ANTES do browser e bloqueia o óbvio.
- Digite sempre com ponto decimal e sem unidade. Se o site mostra a unidade ao lado do
  campo, leia-a com `read_page` e confirme que bate (mm/D/µm).
- Se o site tem seletor de índice ceratométrico (Barrett, ESCRS têm), configure-o para o
  índice do laudo em vez de converter o número. Se não tem, converta com
  `iol_formulas.py` (K_1.3375 = 337.5 / r_mm) e registre.
- TK (Total Keratometry, IOLMaster 700): só cole em campo que diga TK. Em campo K
  comum, use SimK.

## 7. Limites de faixa e validação do próprio site

**O que acontece:** o site rejeita AL < 18 ou > 35, K < 30, etc., ou silenciosamente
"clampa" o valor. Hill-RBF avisa "out of bounds" quando a combinação está fora do
conjunto de treino.

**Como lidar:**
- Se o site rejeitou um valor que passou no validador local, é olho extremo real:
  mostre ao usuário e siga com as outras calculadoras.
- "Out of bounds" do Hill-RBF não é erro: anote como achado ("RBF fora do domínio de
  treino; dar menos peso a este resultado").

## 7b. Prints não salvam em disco
A extensão Claude in Chrome (versão de 2026-09) ignora `save_to_disk` no screenshot e não
devolve caminho. O print aparece inline no chat, mas não vira arquivo. Compense
transcrevendo a tabela inteira poder × refração de cada site para `results_<eye>.json`
(`table`) e mostrando o print no chat. Se um dia `save_to_disk` devolver caminho, copie
para a pasta do caso.

## 8. Resultado em imagem, canvas ou PDF

**O que acontece:** Barrett e Kane mostram tabela HTML (fácil). Alguns mostram gráfico
em canvas, ou geram PDF para impressão.

**Como lidar:**
- Primeiro `get_page_text` / `read_page`. Se a tabela está no DOM, extraia dali.
- Se só há imagem: `screenshot` da região com `zoom`, leia visualmente e transcreva.
  Sempre salve a captura com nome `<code>_<eye>_<calc>.png` — é a evidência que vai no
  relatório e que o cirurgião confere.
- PDF: baixar exige permissão do usuário. Prefira ler a tabela na tela.
- Tabelas de resultado listam vários poderes com refração prevista para cada um. Pegue o
  poder cuja refração prevista é a **mais próxima do alvo**, não a primeira linha, e
  registre também o valor "exato" se o site mostrar.

## 9. Tempo, rate limit e sessões que expiram

- Um paciente (dois olhos) em ~7 calculadoras = ~14 submissões. Faça em série, esperando
  cada resultado renderizar (`wait` 1–2 s após Calculate, confirme com `find` do texto
  "IOL Power"/"Predicted").
- Se aparecer 429, "too many requests" ou a página ficar lenta, pare 60 s e continue.
  Nunca reenvie em loop.
- Listas grandes (>10 pacientes): proponha rodar só a calculadora multi-fórmula (ESCRS)
  como triagem e as demais só nos olhos com spread > 1 D.

## 10. Multi-aba em pipeline

- Uma aba por calculadora, reutilizada entre olhos e pacientes (evita re-aceitar termos).
- **Todas as abas abertas de uma vez** e trabalho por fases (abrir → preencher →
  calcular → colher), como descrito no SKILL.md §4. O ganho vem de sobrepor as esperas;
  a digitação em si é rápida. Não existe digitação simultânea em duas abas: a extensão
  executa as ações em sequência, mas alternar `tabId` dentro do mesmo `browser_batch`
  custa milissegundos.
- Ordem dentro de cada fase: ESCRS primeiro (é a que pede CAPTCHA e a mais lenta para
  renderizar), depois Barrett, Kane, e os demais.
- Se um site cair (SignalR da ESCRS, sessão expirada), siga com os outros e volte nele
  na Fase D.
- Antes de trocar de olho, limpe o formulário (botão Reset/Clear se houver; senão
  sobrescreva todos os campos, incluindo os opcionais, para não herdar LT/WTW do olho
  anterior).

## 11. Quando desistir da automação e cair no manual assistido

Se num site você bateu em 2 barreiras seguidas (ex.: CAPTCHA + campo que não aceita
valor), pare de insistir. Diga ao usuário exatamente quais valores digitar, em que campo,
e peça para ele clicar Calcular; você lê o resultado da tela e segue o fluxo normal
(captura, extração, crosscheck). O objetivo é a LIO certa com evidência, não 100% de
automação.
