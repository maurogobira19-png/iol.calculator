# Gabarito da rodada única de perguntas (AskUserQuestion)

Use no máximo 4 perguntas. Pule as que a mensagem do médico já respondeu. Se o
checkpoint da transcrição ainda não foi feito, ele entra como 1ª pergunta e alguma das
outras sai (priorize: transcrição > LIO > alvo > calculadoras; perfil vai para "Other").

```json
{"questions": [
  {"header": "Transcrição", "question": "A transcrição do laudo (tabela acima) confere?", "multiSelect": false,
   "options": [
     {"label": "Sim, roda (Recommended)", "description": "Usar exatamente os valores da tabela"},
     {"label": "Corrigir um campo", "description": "Digite em Other: olho, campo e valor certo (ex.: OS ACD 2.14)"}]},
  {"header": "LIO", "question": "Qual LIO e constante?", "multiSelect": false,
   "options": [
     {"label": "<lente 1 de lentes_frequentes.json>", "description": "A-constante <x> (<fonte>)"},
     {"label": "<lente 2>", "description": "A-constante <y>"},
     {"label": "<lente 3>", "description": "A-constante <z>"},
     {"label": "Outra", "description": "Digite modelo e constante em Other (ex.: 'Vivinex XY1 118.9')"}]},
  {"header": "Alvo", "question": "Alvo refrativo do olho a calcular?", "multiSelect": false,
   "options": [
     {"label": "Emetropia (−0.25) (Recommended)", "description": "Padrão para visão de longe"},
     {"label": "Miopia leve (−0.50)", "description": "Margem para não ficar hipermétrope"},
     {"label": "Monovisão (−1.50)", "description": "Olho de perto"},
     {"label": "Outro", "description": "Digite o valor em Other"}]},
  {"header": "Calculadoras", "question": "Quais calculadoras rodar? (a escolha autoriza aceitar os disclaimers clínicos desses sites nesta sessão)", "multiSelect": false,
   "options": [
     {"label": "Padrão: ESCRS + Barrett + Kane (Recommended)", "description": "7 fórmulas via ESCRS + 2 confirmações independentes. ~5 min por olho"},
     {"label": "Todas as 10", "description": "Inclui Hill-RBF, EVO, Hoffer QST, K6, PEARL, ASCRS, Ladas (se tiver login). ~15 min por olho"},
     {"label": "Só ESCRS", "description": "Triagem rápida, 7 fórmulas, ~2 min"}]}
]}
```

Perfil (sexo, idade, pós-refrativa, tórica): se não veio na mensagem nem no laudo, não
gaste uma pergunta com isso quando as 4 acima forem necessárias; deixe em branco / "Not
provided" e registre no relatório que Kane/RBF/QST rodaram sem sexo. Se sobrar espaço,
use: header "Perfil", multiSelect true, opções "Mulher", "Homem", "Pós-LASIK/PRK", "Tórica".
