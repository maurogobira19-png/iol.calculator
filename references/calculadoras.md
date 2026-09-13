# Playbook por calculadora (verificado por inspeção ao vivo em 2026-09-12; o que não foi verificado está marcado)

Leia só a seção da calculadora que vai usar. A tabela-resumo diz o que esperar antes de
abrir a aba. Sites mudam: se um campo não bater com o descrito, mapeie de novo com
`read_page` e anote a diferença no relatório (e, se for grande, atualize este arquivo).

## Índice
- Resumo (tabela)
- Ordem padrão de execução
- 1 ESCRS multi-fórmula (7 fórmulas de uma vez)
- 2 Barrett Universal II (APACRS) + True-K Toric
- 3 Kane
- 4 Hill-RBF 3.0
- 5 EVO 2.0
- 6 Hoffer QST
- 7 Cooke K6
- 8 PEARL-DGS
- 9 ASCRS pós-refrativa
- 10 Ladas Super Formula AI
- 11 Holladay 2 (desktop) e IOLCon (constantes)
- Quirks transversais

## Resumo

| Calculadora | URL | Login | Gate de termos | Bot-block | Tecnologia | Batch/API |
|---|---|---|---|---|---|---|
| ESCRS (Barrett UII, Cooke K6, EVO, Hill-RBF, Hoffer QST, Kane, PEARL-DGS) | https://iolcalculator.escrs.org/ | não | botão "I AGREE" por sessão | nenhum | **Blazor Server** (SignalR, MudBlazor) — ids aleatórios | "LOAD BIOMETRY" = BiomAPI (import de aparelho), sem API aberta |
| Barrett Universal II v1.05 | https://calc.apacrs.org/barrett_universal2105/ | não | checkbox no form, a cada postback | Cloudflare (fetch fora do browser → 403; Chrome real passa) | ASP.NET WebForms | nenhum |
| Barrett True-K Toric v1.05 | https://calc.apacrs.org/TRueKToric105/truektoric.aspx | não | mesmo checkbox | idem | WebForms | nenhum |
| Barrett Toric v2.5 / True-K não-tórico | **não verificado** (caminhos antigos 404); achar link em ascrs.org/en/tools/barrett-toric-calculator no Chrome | | | | | |
| Kane | https://www.iolformula.com/ | não | "I Agree" uma vez (cookie `agreement`) | **reCAPTCHA v2 invisível** no Calculate | WordPress + jQuery, AJAX | nenhum |
| Hill-RBF 3.0 | https://rbfcalculator.com/online/ → iframe **https://iolcalculator.haag-streit.com/#/** (use este direto) | não | "I agree" por sessão | nenhum | SPA JS (hash-router) | nenhum; **dados são armazenados 5 anos na Suíça** |
| EVO 2.0 | https://www.evoiolcalculator.com/ → /Calculator.aspx | não | checkbox + "Agree" (por visita; persistência não verificada) | nenhum | WebForms | nenhum |
| Hoffer QST | https://hofferqst.com/ | não | modal existe, não aparece no load (se exige "Agree" antes de calcular: não verificado) | nenhum | Vue 2 + BootstrapVue | nenhum |
| Cooke K6 | https://cookeformula.com/ | não | seletor de modo → EULA "ACCEPT" | Cloudflare (transparente no Chrome) | React SPA (ids MUI aleatórios) | nenhum |
| PEARL-DGS | https://iolsolver.com/regular (também /complex, second-eye) | não | nenhum visto | nenhum | Vue + Vuetify (ids gerados) | só "AUTO FILL" demo |
| ASCRS pós-refrativa v4.9 | https://iolcalc.ascrs.org/ → wbfrmCalculator.aspx (miópico); botões p/ hiperópico e RK | não | "I accept." + tipo de cirurgia, por sessão | Cloudflare | WebForms | nenhum |
| Ladas Super Formula AI | https://iolcalc.com/ → /sign_in | **sim, conta obrigatória** | não verificado (atrás do login) | nenhum na landing | AngularJS 1.x | não verificado |
| Holladay 2 (HICSOAP) | https://hicsoap.com/ | licença paga | — | — | **desktop Windows-only**, sem versão web | importa IOLMaster/Lenstar |
| IOLCon | https://iolcon.org/lensesTable.php | não p/ consultar | ToS em PDF (não lido) | nenhum | PHP | download XML p/ biômetros |

Termos: Kane, Hill-RBF e Cooke K6 proíbem "operar como SaaS / service bureau" e limitam a
"operações clínicas do próprio usuário". Preencher para os próprios pacientes, no Chrome do
próprio cirurgião, cabe nisso. Não use a skill para calcular para terceiros em escala.
A ESCRS declara nos próprios termos que funciona por "web scraping" dos sites-fonte com
autorização dos autores — é o agregador sancionado, por isso é a primeira escolha.

## Ordem padrão de execução
1. **ESCRS** — 7 fórmulas numa submissão por olho. Triagem de tudo.
2. **Barrett APACRS** — referência independente; pega discrepância do agregador.
3. **Kane** (site próprio) — segunda confirmação.
4. Demais só se o usuário pediu "todas" ou se o spread da ESCRS > 1 D naquele olho.
5. Pós-refrativa: ASCRS + Barrett True-K + modo "complex" do PEARL + "Post LASIK" na ESCRS/EVO/QST/K6.

---

## 1. ESCRS multi-fórmula
**URL** https://iolcalculator.escrs.org/ · **Fórmulas:** Barrett UII, Cooke K6, EVO, Hill-RBF, Hoffer QST, Kane, PEARL-DGS (checkbox por fórmula; variantes tóricas quando "Toric" marcado).

**Campos:** Surgeon, Patient Initials, Id (use o code), Age, Gender. Por olho: checkboxes
Toric / Keratoconus / "Argos (SoS) AL" / "Post LASIK/PRK/RK"; AL, ACD, LT (mm); CCT (µm);
WTW; K1, K2 (D); **Index** (1.3375 padrão; seletor); Target Refraction; Manufacturer →
Select IOL (auto-preenche as constantes de cada fórmula) — ou constantes manuais: Barrett
A, Cooke A, EVO A, Hill-RBF A, Hoffer pACD, Kane A, PEARL-DGS A. Há toggle "Decimal (0.00)"
(aceita vírgula decimal se configurado).

**Como automatizar (Blazor Server):**
- Ids mudam a cada render (`mudinput…`). Localize sempre por label com `find`, nunca
  guarde ids entre submissões.
- Blazor só registra valor com eventos reais de teclado: clique no campo → `type` → `Tab`.
  `form_input` pode deixar o estado do servidor vazio (o eco de volta no `read_page`
  engana: o DOM mostra o valor, o servidor não recebeu). Se o resultado vier em branco ou
  igual ao olho anterior, foi isso — refaça com `type`.
- Sessão SignalR cai com ociosidade ("An error has occurred… reloaded"). Se aparecer o
  banner, recarregue, re-aceite termos (com a autorização já dada nesta sessão) e refaça
  aquele olho do zero.
- Selecione a LIO pelo Manufacturer → Select IOL e **leia as constantes preenchidas**;
  compare com `plan.A_constant`. Se o cirurgião tem constante otimizada, sobrescreva os
  campos de constante e anote.
- Resultado: tabelas HTML (uma por fórmula) + gráfico Plotly. `get_page_text` pega as
  tabelas. Cada fórmula lista poderes com refração prevista: escolha a linha mais próxima
  do alvo. Captura de tela da região das tabelas.
- Não use "LOAD BIOMETRY" (é BiomAPI para aparelho pareado, não upload de PDF).

**Lições de execução (2026-09-13, caso P-TESTE-01):**
- **Gender é obrigatório** (só Male/Female; erro "Please specify the gender"). Age não é.
  Se o laudo não traz sexo, pergunte (fechado) ANTES de abrir o site.
- Gender e Manufacturer são `MudSelect`: só registram com `.click()` via JS no
  `.mud-list-item` (barreiras §4, caso resolvido). Select IOL é autocomplete: digitar o
  código (ex. "SN60WF") + clicar na opção por ref funciona.
- Campos numéricos: clique + `type` + `Tab` funcionou de primeira; eco de volta via JS
  em `input` + label confirmou todos.
- Ao escolher a lente, o site preenche as 7 constantes (SN60WF: Barrett 118.99, Cooke
  119, EVO 119, Hill-RBF 119.02, Hoffer pACD 5.67, Kane 118.98, PEARL 119.1). Reaproveite
  esses valores nos sites individuais para os resultados serem comparáveis.
- **Calculate abre um reCAPTCHA v2 "I'm not a robot"** (não estava no levantamento).
  Pergunta fechada ao médico; no pipeline, dispare os outros Calculates antes. Depois
  dele o resultado renderiza em ~3 s.
- **Resultado:** página nova com cabeçalho (AL, ACD, LT, CCT, WTW, K1, K2, n, IOL,
  TARGET) e tabela "SE PWR (D)" × colunas por fórmula, com a linha mais próxima do alvo
  destacada. `get_page_text` devolve a tabela limpa. Botões EDIT / PRINT / SHARE; EDIT
  volta ao form com tudo preenchido (bom para o 2º olho).
- **A coluna Barrett não veio** nesta execução (6 de 7 fórmulas). Motivo desconhecido;
  por isso o Barrett APACRS direto continua obrigatório.
- Termos: "Biometric data is stored fully anonymised for at least one year".

## 2. Barrett Universal II (APACRS) + True-K Toric
**URL** https://calc.apacrs.org/barrett_universal2105/ · WebForms; Cloudflare bloqueia
qualquer coisa que não seja browser real (WebFetch → 403). Só `claude-in-chrome`.

**Campos** (names `ctl00$MainContent$…`): DoctorName, PatientName (code), PatientNo;
radio índice K `RadioButtonList1` (**1.3375 / 1.332**); **LensFactor** (−2.0 a 5.0) *ou*
**Aconstant** (112–125) *ou* dropdown `IOLModel` (38 lentes: "Personal Constant", Alcon
SN60WF…, J&J ZCB00/ZXR00, Zeiss 409M/709M, Rayner RayOne EMV, B&L MX60/ET, Hoya, SIFI
Mini WELL, Ophtec 565…). Por olho (OD sem sufixo, OS sufixo `0`): Axlength 12–38;
MeasuredK1, MeasuredK2 30–60 D; **OpticalACD** 0–6 (epitélio→cristalino); Refraction (alvo)
−10 a 10; opcionais LensThickness 2–8, WTW 8–14. Não pede CCT, idade nem sexo.

**Como automatizar:** marcar o checkbox `ConfirmCheckBox` ("Enter Data and Calculate")
antes de `Button1`, **a cada cálculo** (é o gate de termos — precisa da autorização de
sessão). Tem os dois olhos no mesmo form. Se tiver A-constante e não Lens Factor, digite
no campo Aconstant e deixe o site derivar o LF. Ponto decimal (vírgula: não verificado).

**Lições de execução (2026-09-13):**
- `form_input` funciona em todos os campos (WebForms puro). **Ordem dos refs é por
  linha:** AL(R), AL(L), K1(R), K1(L), K2(R), K2(L), ACD(R), ACD(L), Refr(R), Refr(L),
  LT(R), LT(L), WTW(R), WTW(L). Confirme por nome via JS: campos OS têm sufixo `0`
  (`Axlength0`, `MeasuredK10`, `OpticalACD0`, `Refraction0`, `LensThickness0`, `WTW0`).
- **Selecionar a lente no dropdown dispara postback e LIMPA os campos numéricos.**
  Ordem certa: cabeçalho → lente (espera 2 s) → só então os números → checkbox → Calculate.
- SN60WF no dropdown preenche LF 1.88 / A 118.99 (mesmos da ESCRS).
- Sem CAPTCHA. Resultado NÃO aparece na aba "Patient Data": após Calculate, clique na aba
  **"Universal Formula"** (link no menubar). Lá: "Recommended IOL: 26.55 (Biconvex) for
  Target Refraction:-0.50" + tabela IOL Power / Optic / Refraction (7 linhas em passos de
  0.5, a mais próxima do alvo destacada). `get_page_text` lê a tabela; o texto
  "Recommended IOL" só aparece no screenshot/DOM, não no get_page_text — leia por `find`.

**True-K Toric v1.05** https://calc.apacrs.org/TRueKToric105/truektoric.aspx — adiciona
radio +/− cilindro, olho, RefractProcedure (Myopic Lasik / Hyperopic Lasik / RK), PreLasik e
PostLasik (refração), MeasuredK/MeasuredAxis (plano) e MeasuredK0/MeasuredAxis0 (curvo),
InducedCyl (SIA 0–2), IncisionAxis 0–360, NetCornealAstig (PCA medido, opcional),
Koptional1/2, dropdown IOLPower 6–34, 19 lentes tóricas.

**Barrett Toric v2.5 e True-K não-tórico:** URLs antigas dão 404. Abra
https://www.ascrs.org/en/tools/barrett-toric-calculator no Chrome e siga o link embutido;
anote a URL nova aqui.

## 3. Kane
**URL** https://www.iolformula.com/ (acordo em /agreement/, "I Agree" grava cookie
`agreement`; com o cookie, o form abre direto).

**Campos** (input `name`): surgeon_name; `kindex` select (1.3375, 1.332, 1.3315, 1.3360,
1.3380); patient_name (code), id; **gender_1 (M) / gender_2 (F) — o Kane usa sexo**; por
olho (sufixo `_1`/`_2` ou `_right`/`_left`): radio nontoric/toric, checkbox keratoconus,
`aconstant_` *ou* `ioltype_` (30 lentes), target_ref_, al_ (18–35), k1_, k2_ (30–65),
acd_ (1.50–5.00), opcionais lt_ (2.5–8), cct_ (350–650 µm). Tórico: k1/k2 axis, sia_, inc_.

**Como automatizar:** **reCAPTCHA v2 invisível** ligado ao Calculate. No Chrome real do
usuário normalmente passa em silêncio. Se aparecer desafio visível, pare e peça ao usuário
para resolver (nunca tente). Se o submit falhar com erro genérico, peça a ele para clicar
Calculate naquela aba.

**Lições de execução (2026-09-13):**
- Termos: botão "I Agree" (coordenada; não vem como link/button no read_page interactive).
- Form jQuery simples: clique por coordenada + `type` funciona em tudo. Sexo = botões
  M / F (checkboxes `gender_1`/`gender_2` por baixo); clicar "F" marca `gender_2`.
- Digitar A-constante direto (`aconstant_2`) dispensa o dropdown IOL Type.
- reCAPTCHA passou em silêncio; resultado em ~5 s na própria página: cabeçalho com os
  inputs ecoados + tabela "IOL Power (D) / Refraction (D)" (7 linhas, passo 0.5), com a
  linha destacada **pelo lado míope** (destacou 27.0/−0.71 para alvo −0.50, embora
  26.5/−0.37 seja a mais próxima). Registre as duas. `get_page_text` lê a tabela.
- Resultado Kane do site = coluna Kane da ESCRS (mesma constante) — confirmação válida.

## 4. Hill-RBF 3.0
**URL real** https://iolcalculator.haag-streit.com/#/ (rbfcalculator.com só embute em
iframe; automatize o Haag-Streit direto para evitar cross-origin).

**Campos** (id/name): pat_id (code), pat_lastname/pat_firstname (use o code ou "-"),
pat_birthday (**DD.MM.YYYY**), pat_gender (Female/Male/Not provided — **o modelo usa
sexo**), surgeon name/email, calculation_id; por olho (`od_`/`os_`): targetRefraction
(−2.5 a +1.0!), measuringDevice select (Lenstar LS 900, Eyestar ES 900, IOLMaster 500/700,
AL-Scan, OA 2000, Aladdin…), al 19–35, cct 260–760, acd 1.25–5.25, lt 2.6–7.4, k1/k2
37–52 com k1Axis/k2Axis, `n` select (1.3315/1.3320/1.3360/1.3375/1.3380), wtw 8.8–14.5,
lens design select (Biconvex 1:1…), manufacturer, model, aconstant 100–132.

**Atenção:** alvo limitado a −2.5…+1.0; K limitado a 37–52 (K extremo → use outra
fórmula). "Out of bounds" no resultado = fora do domínio de treino: registre e dê menos
peso. **Os dados submetidos ficam armazenados (Suíça, 5 anos)** — mais um motivo para só
enviar código, não nome nem data de nascimento real (se a data for obrigatória, pergunte
ao usuário se aceita enviar; sexo e idade são inputs do modelo, o resto não).
Há botões de dev "Fill random data"/"Toggle debug" — não clique.

## 5. EVO 2.0
**URL** https://www.evoiolcalculator.com/ → Agree → /Calculator.aspx (WebForms, um olho
por submissão).

**Campos** (ids): TextBoxName (code), TextBoxID, TextBoxSurgeon, **DropDownArgos**
(No/Yes — AL do Argos por sum-of-segments), RadioButtonRLEye, txtAL, txtK1, txtK2,
txtACD ("Optical ACD"), txtLT (opc), txtCCT (opc), txtRefraction (alvo), txtAConstant
(A SRK/T ULIB/IOLCon), DropDownIOLModel (33), **DropDownKIndex** (1.3375/1.3315/1.332),
DropDownLASIK (No/Myopic/Hyperopic/RK); avançado: DropDownListPK (biômetro p/ K
posterior), txtPK1/PK2, txtPreLASIK/txtPostLASIK (EE). Limites de faixa não exibidos.

## 6. Hoffer QST
**URL** https://hofferqst.com/ · Vue SPA. Por olho: radio SE/Toric, checkbox "Post
myopic LASIK/PRK", input-right-AL, **input-right-ACD "ACD Epith to Lens"** (explícito),
K1, K2 (D), IOLModel (fabricante: Alcon, B+L, Hoya, J&J, Kowa, Md-Tech, Medicontur,
PhysIOL, Rayner, SIFI, Soleko, Zeiss) → IOLType em cascata, **pACD** ("Hoffer pACD" —
não é A-constante; o site preenche ao escolher a lente; se digitar manual, use pACD do
IOLCon), TargetRx; global: radio sexo (QST usa), índice (1.3375/1.332/1.3315).
Inputs HTML5 number com max 100/500 (não é limite clínico). Modal de disclaimer existe
mas não aparece no load; se bloquear o Calculate, aceite com a autorização da sessão.

## 7. Cooke K6
**URL** https://cookeformula.com/ · React SPA (ids MUI aleatórios → `find` por label).
Fluxo: seletor de modo (DEFAULT / POST-MYOPIC LVC / POST-HYPEROPIC LVC / POST-RK) → EULA
ACCEPT → form. Campos: Special Situation; **Name (obrigatório → use o code)**, ID, DOB,
Surgeon; Keratometric Index (1.3375 padrão); "Use Ks"; por olho: od-tgt-rx, IOL
(autocomplete) *ou* od-a-constant (obrigatório), od-k1/k2, **radio Biometer
(Lenstar/Argos/Other — Argos ajusta AL)**, od-al, od-cct (recomendado), od-acd
(obrigatório), od-lt (recomendado), od-wtw (opcional) → CONTINUE.

## 8. PEARL-DGS
**URL** https://iolsolver.com/regular (Complex: pós-LVC miópico/hiperópico, pós-RK,
pós-ICL, córnea não fisiológica; Second eye: usa refração do 1º olho). Vuetify: ids
gerados (`input-57`) → `find` por label. Campos: Patient ID/Name (code), Keratometric
Index (1.3375), Biometer, por olho: IOL Model (autocomplete; padrão "Finevision" — troque!),
A constant, Target refraction, AL, K1, K2, ACD, opcional Custom vitreous, LT, CCT.
Sem gate de termos visto. Botão AUTO FILL só preenche demo — não use.

## 9. ASCRS pós-refrativa v4.9
**URL** https://iolcalc.ascrs.org/ → "I accept." → tipo (miópico LASIK/PRK →
wbfrmCalculator.aspx; hiperópico; RK). WebForms, Cloudflare.
Campos (miópico): txtDoctorName, txtPatientName (code), txtPatientID, txtEyeLR,
txtIOLtype, txtBioTargetRef; pré-LASIK txtPreSph/txtPreCyl/txtPreVer (vértice 12.5),
txtPreK1/K2; pós-LASIK txtPstSph/Cyl/Ver; topografia opcional: txtEye (EyeSys EffRP),
txtTommy (Tomey ACCP), Nidek ACP/APP, txtGalilei (TCP2), txtAtlas4mmzone, Pentacam
(TNP_Apex_4.0), txtAtlas0–3, OCT txtNCP/txtPCP/txtCCT; biometria txtBioK1/K2, radio
índice (1.3375/1.332/Other+TextboxOther), txtBioAL, txtBioACD, LensThickness, WTW;
constantes txtBioAconst, txtBioSF (Holladay), txtBioa0/a1/a2 (Haigis).
**Regra do site:** se digitar esfera, tem que digitar cilindro (mesmo 0). Métodos
retornados (Wang-Koch-Maloney, Shammas, Haigis-L, Barrett True-K, OCT…) em tabela com
média — registre a média e o True-K separadamente.

## 10. Ladas Super Formula AI
https://iolcalc.com/ exige conta (beta-tester). Se o usuário tem login: ele entra no
Chrome, você mapeia os campos na hora (não verificados) e segue o padrão. Se não tem, pule
e diga.

## 11. Holladay 2 e IOLCon
- **Holladay 2** só existe no HICSOAP (Windows desktop, pago) ou embutido em alguns
  biômetros. Se o laudo do IOLMaster/Lenstar já traz Holladay 2, transcreva do laudo e
  marque `source: "laudo IOLMaster"`.
- **IOLCon** https://iolcon.org/lensesTable.php — consultar constantes não exige login.
  Procure a lente pelo código do fabricante; pegue A (SRK/T), pACD (Hoffer Q), SF
  (Holladay), a0/a1/a2 (Haigis) e, se houver, Barrett LF. Registre no `plan` do JSON
  com a data da consulta.

## Quirks transversais
- **Índice ceratométrico** selecionável em Barrett, Kane, RBF, EVO, QST, K6, PEARL, ESCRS,
  ASCRS: passe sempre o índice do laudo (IOLMaster = 1.3375 por padrão de fábrica, mas
  pode estar em 1.332; Lenstar = 1.3315; Pentacam/Argos variam — confira no laudo).
  Nunca converta o número à mão se o site tem seletor.
- **ACD** = óptico, epitélio→cristalino, em todos os sites que rotulam. Nenhum pede ACD
  endotelial.
- **Sexo/idade** são inputs de Kane, Hill-RBF e Hoffer QST. Idade também na ESCRS.
- **Argos** (AL por sum-of-segments) tem flag própria em EVO, K6 e ESCRS. Marque quando
  o biômetro for Argos.
- **Decimal**: ponto em todos; só a ESCRS tem toggle de formato. Não testado com vírgula.
- **Bot-protection**: Cloudflare (APACRS, ASCRS, Cooke) é transparente no Chrome real;
  reCAPTCHA no Kane. Nenhum site tem API pública.
- **Renderização dos resultados não foi exercitada** (nenhum dado foi submetido no
  levantamento). Na primeira execução real de cada site, confirme onde o resultado aparece
  e atualize a seção.
