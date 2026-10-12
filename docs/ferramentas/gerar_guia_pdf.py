"""Gera docs/av1-guia-do-painel-2026-10-12.pdf (guia do painel para o grupo).

Uso: python docs/ferramentas/gerar_guia_pdf.py   (precisa de reportlab e pillow; veja README.md desta pasta)
Os números e textos do guia vêm de av1-grupo-3-mapen/racionalizacao.md; ao mudar o relatório, revise os textos aqui.
"""
import os
import tempfile
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table,
                                TableStyle, Image as RLImage, PageBreak, KeepTogether)

RAIZ = Path(__file__).resolve().parents[2]
EV = RAIZ / "av1-grupo-3-mapen" / "evidencias"
OUT = RAIZ / "docs" / "av1-guia-do-painel-2026-10-12.pdf"
IMG = Path(tempfile.mkdtemp(prefix="guia_img_"))

def pasta_fontes() -> str:
    """DejaVu Sans cobre os símbolos usados (×, ●, →). Aponte FONTES_DIR se ela não estiver numa pasta comum."""
    candidatas = [os.environ.get("FONTES_DIR", ""), "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu",
                  "/Library/Fonts", str(Path.home() / "Library/Fonts"), "C:/Windows/Fonts", str(Path.home() / "AppData/Local/Microsoft/Windows/Fonts")]
    for c in candidatas:
        if c and (Path(c) / "DejaVuSans.ttf").exists() and (Path(c) / "DejaVuSans-Bold.ttf").exists():
            return c
    raise SystemExit("Não achei DejaVuSans.ttf e DejaVuSans-Bold.ttf. Baixe em https://dejavu-fonts.github.io e rode com FONTES_DIR=<pasta>.")


F = pasta_fontes() + "/"
pdfmetrics.registerFont(TTFont("DV", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DV", boldItalic="DVB")

NAVY = colors.HexColor("#12263f"); ACC = colors.HexColor("#d9480f"); INK = colors.HexColor("#1c2430")
SOFT = colors.HexColor("#f1f4f8"); LINE = colors.HexColor("#c9d2de"); MUTE = colors.HexColor("#5b6675")
WARN = colors.HexColor("#fff4e6"); OK = colors.HexColor("#e8f5ec")

def st(name, **kw):
    base = dict(fontName="DV", fontSize=9.2, leading=13.2, textColor=INK, alignment=TA_LEFT)
    base.update(kw); return ParagraphStyle(name, **base)
BODY = st("body"); SMALL = st("small", fontSize=7.8, leading=10.6, textColor=MUTE)
H1 = st("h1", fontName="DVB", fontSize=16, leading=20, textColor=NAVY, spaceBefore=6, spaceAfter=4, keepWithNext=1)
H2 = st("h2", fontName="DVB", fontSize=10.6, leading=14, textColor=ACC, spaceBefore=8, spaceAfter=3, keepWithNext=1)
CELL = st("cell", fontSize=8.2, leading=11.2); CELLB = st("cellb", fontName="DVB", fontSize=8.2, leading=11.2, textColor=colors.white)
LEAD = st("lead", fontSize=10.6, leading=15, textColor=NAVY)

def P(t, s=BODY): return Paragraph(t, s)
def bullets(items, s=BODY):
    return [Paragraph(f"<font color='#d9480f'>●</font>&nbsp;&nbsp;{t}", ParagraphStyle("b", parent=s, leftIndent=12, firstLineIndent=-12, spaceAfter=2)) for t in items]
def table(rows, widths, head=True, zebra=True):
    data = [[Paragraph(str(c), CELLB if (head and i == 0) else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    sty = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
           ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
           ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if head: sty.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0: sty.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(sty)); return t
def callout(text, bg=WARN, bar=ACC):
    t = Table([[Paragraph(text, CELL)]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t
def img(path, width, caption=None):
    w, h = Image.open(path).size
    items = [RLImage(str(path), width=width, height=width * h / w)]
    if caption: items.append(Paragraph(caption, SMALL))
    return items
def crop(src, box, name):
    im = Image.open(EV / src).convert("RGB").crop(box); p = IMG / name; im.save(p); return p

# recortes do painel anotado (1240x1840)
cab = crop("painel_versao3_anotado.png", (0, 0, 1240, 525), "cab.png")
v1 = crop("painel_versao3_anotado.png", (30, 505, 725, 1140), "v1.png")
v2 = crop("painel_versao3_anotado.png", (728, 505, 1210, 1140), "v2.png")
v3 = crop("painel_versao3_anotado.png", (30, 1135, 1210, 1590), "v3.png")

PW, PH = A4; M = 18 * mm; W = PW - 2 * M

def deco(c, d):
    c.saveState()
    c.setFillColor(NAVY); c.rect(0, PH - 9 * mm, PW, 9 * mm, stroke=0, fill=1)
    c.setFillColor(ACC); c.rect(0, PH - 9.8 * mm, PW, 0.8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("DVB", 7.5); c.drawString(M, PH - 6.2 * mm, "MAPEN · AV1 · GRUPO 3 · GUIA DO PAINEL")
    c.setFont("DV", 7.5); c.setFillColor(MUTE)
    c.drawString(M, 9 * mm, "Guia interno do grupo (12/10/2026). Fonte dos números: av1-grupo-3-mapen/racionalizacao.md")
    c.drawRightString(PW - M, 9 * mm, f"{d.page}")
    c.restoreState()

doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=M, rightMargin=M, topMargin=18 * mm, bottomMargin=16 * mm,
                      title="MAPEN · AV1 · Guia do painel", author="Grupo 3 MAPEN/MAPPEN",
                      subject="O que temos na AV1 e como explicar")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(M, 16 * mm, W, PH - 34 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=deco)])

S_ = []
# ---------- Capa / resumo ----------
S_ += [Spacer(1, 4 * mm), P("Consumo observado × referência", st("t", fontName="DVB", fontSize=24, leading=28, textColor=NAVY)),
       P("O que entregamos na AV1 e como explicar", st("t2", fontSize=13, leading=17, textColor=ACC)), Spacer(1, 4 * mm),
       P("Este guia é para o grupo todo entender o painel, o pacote e os limites do que fizemos. A AV1 é avaliada só pelos arquivos entregues, sem apresentação nem arguição. Mesmo assim, qualquer um de nós precisa conseguir explicar de onde vem cada número.", LEAD),
       Spacer(1, 4 * mm)]
S_ += img(cab, W, "Cabeçalho, filtros (F) e destaque (H) do painel final. Ao lado está o selo: dado real público · referência estimada · desvio ≠ desperdício.")
S_ += [Spacer(1, 3 * mm), P("Em uma frase", H2),
       P("O painel diz <b>em quais ativos e dias o consumo ficou acima ou abaixo de uma referência estimada</b>, para o gestor de um andar escolher <b>o que investigar primeiro</b>. Ele não diz que houve desperdício nem economia."),
       P("Decisão e perguntas", H2),
       table([["ID", "Pergunta", "Ação que apoia", "Vista"],
              ["P1", "Quando o consumo se afastou da referência, e em que sentido?", "Escolher dias para checar ocupação, agenda e operação", "V1"],
              ["P2", "Em quais ativos o excesso acumulado é maior?", "Definir a ordem de investigação entre ativos", "V2"],
              ["P3", "O padrão ao longo do dia acompanha o funcionamento (dia útil × fim de semana)?", "Separar uso fora do expediente de desvio real", "V3"]],
             [10 * mm, 64 * mm, 76 * mm, 16 * mm]),
       Spacer(1, 2 * mm),
       P("Quem usa: o gestor de uma unidade (um andar de prédio comercial), toda semana. Recorte: andar 2 do CU-BEMS, 8 ativos (ar-condicionado, iluminação, tomadas), 04/11 a 01/12/2018 (28 dias).", SMALL),
       PageBreak()]

# ---------- O painel ----------
S_ += [P("1. O painel, vista por vista", H1),
       P("A página tem três vistas calculadas (V1, V2, V3), um destaque (H) e filtros (F). A leitura vai da conclusão para a evidência: H, depois V1 e V2, depois V3.")]
S_ += [callout("<b>Atenção às imagens:</b> elas são da versão 3 do painel, que mostrava só os códigos dos ativos (z1_AC1, z1_Light...). A versão atual (4) mostra o nome por extenso, com o código ao lado, e tem a página <font name='DVB'>nomes.html</font>, ligada no cabeçalho, que explica cada nome e cada termo. Ver a seção 5.", bg=WARN, bar=ACC)]
S_ += [Spacer(1, 2 * mm), P("V1 · Desvio diário (P1)", H2)]
S_ += img(v1, W * 0.74)
S_ += bullets(["<b>O que mostra:</b> consumo observado (linha azul) contra o esperado (tracejada), e embaixo o desvio do dia = observado − esperado, em kWh. Vermelho com ▲ é acima, cinza é abaixo. Fim de semana em fundo cinza.",
               "<b>Achado (z1_AC1, referência A):</b> acima da referência em 9 de 28 dias (+66,2 kWh). Maiores excessos: +13,1 kWh em 08/11 e +12,6 kWh em 22/11.",
               "<b>Escolha:</b> linhas para a trajetória no tempo, barras de desvio em escala comum a partir de zero. Dia sem dado é lacuna, nunca zero.",
               "<b>Alternativa descartada:</b> mostrar só o consumo total, que não separa “alto” de “alto para aquele dia da semana”."])
S_ += [Spacer(1, 5 * mm)]
S_ += [P("V2 · Ranking por ativo (P2)", H2)]
S_ += [Table([[img(v2, W * 0.50)[0], [P("<b>O que mostra:</b> para cada ativo, a soma dos desvios positivos (vermelho, à direita) e dos negativos (cinza, à esquerda), com o saldo numa coluna.", CELL), Spacer(1, 2 * mm),
         P("<b>Ordem:</b> pela soma dos desvios positivos, porque é isso que orienta onde investigar.", CELL), Spacer(1, 2 * mm),
         P("<b>Achado do mês:</b> z1_AC1 (+66,2 kWh), depois z4_AC1 (+38,4), z2_Light (+4,5) e z3_Light (+2,0). Os outros ficam perto de zero.", CELL), Spacer(1, 2 * mm),
         P("<b>Clicar numa linha</b> troca o ativo de V1 e V3.", CELL)]]],
            colWidths=[W * 0.53, W * 0.47], style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))]
S_ += [P("V3 · Perfil horário (P3)", H2)]
S_ += img(v3, W * 0.92)
S_ += bullets(["<b>O que mostra:</b> mediana da potência média por hora (kW), observado × referência, em dia útil e em fim de semana, na mesma escala vertical. Faixa cinza = expediente assumido (7h às 18h).",
               "<b>Achado:</b> z1_AC1 liga por volta das 7h e desliga por volta das 17h, acompanha a referência no dia útil (maior diferença −1,1 kW às 12h) e fica em 0 kW no fim de semana.",
               "<b>Cuidado:</b> aqui é potência (kW), nas outras vistas é energia (kWh). Nunca somamos as duas. O expediente é hipótese nossa, ninguém informou."])
S_ += [Spacer(1, 5 * mm)]

# ---------- Dados e qualidade ----------
S_ += [P("2. De onde vêm os números", H1),
       table([["Item", "O que é"],
              ["Fonte", "CU-BEMS, andar 2, 2018 (Pipattanasomporn et al., 2020, <i>Scientific Data</i> 7:241, CC BY 4.0; DOI do artigo 10.6084/m9.figshare.11726517, arquivo 2018Floor2.csv, id 21350166). Dado <b>real público</b>, de um prédio na Tailândia. Não é cliente do MAPEN."],
              ["Como ler o código", "z1_AC1 = zona 1 · AC (ar-condicionado) · número 1. Light = iluminação, Plug = tomadas (plug loads). Em kW por minuto. A página nomes.html do painel explica isso e cada termo."],
              ["Os 8 ativos", "8 dos 24 equipamentos do andar: quatro zonas e três tipos de carga (ar-condicionado, iluminação, tomadas), com z4_Plug de propósito (nunca consome). Os outros 16 ficaram fora e o motivo individual não foi registrado: não é amostra estatística, não generalizar para o andar."],
              ["Recorte", "09/09 a 01/12/2018, 1 linha por minuto, 120.960 linhas. Avaliado: 04/11 a 01/12 (28 dias). 8 ativos."],
              ["Bases derivadas", "<b>Diária</b> (ativo × dia, 672 linhas): kWh = potência média × 24 h. <b>Horária</b> (ativo × hora, 16.128 linhas): kW médio."],
              ["Referência (esperado)", "<b>Estimada</b>. Mediana, por ativo, da energia diária dos dias com o mesmo dia da semana, numa janela anterior. O período avaliado nunca entra."],
              ["O que é real e o que não é", "Observado: real. Esperado: estimativa nossa. Nada neste painel é simulado."]],
             [34 * mm, W - 34 * mm]),
       P("Cinco verificações de qualidade (rodadas no dado completo)", H2),
       table([["Verificação", "Resultado", "Decisão"],
              ["Chaves e duplicidade", "120.960 linhas, 0 duplicadas", "Nenhuma ação"],
              ["Ausência e códigos", "0 timestamps faltando; 113 a 193 minutos vazios por ativo", "Dia só vale com ≥ 95% dos minutos"],
              ["Tipos e unidades", "float64, (kW) = potência média por minuto", "kWh só como média diária × 24 h; kW e kWh nunca misturados"],
              ["Domínio e plausibilidade", "0 negativos; máximo 59,61 kW; z4_Plug com máximo 0", "z4_Plug mantido de propósito como caso de denominador zero"],
              ["Cobertura e junções", "1 dia (19/09) com menos de 95% em 6 ativos", "Vira ausência, fora das medianas. Não há junção"]],
             [36 * mm, 70 * mm, W - 106 * mm]),
       P("Três referências (a sensibilidade usa as três)", H2),
       table([["ID", "Hipótese", "Janela"],
              ["A (principal)", "8 semanas, todos os dias", "09/09 a 03/11/2018"],
              ["B", "Só as 4 últimas semanas", "07/10 a 03/11/2018"],
              ["C", "Como A, sem os feriados com consumo zero", "8 semanas, sem 13, 15 e 23/10"]],
             [30 * mm, 90 * mm, W - 120 * mm]),
       P("Dicionário completo: dados/dicionario.md. Registro das verificações: evidencias/verificacoes_qualidade.json.", SMALL)]
S_ += [Spacer(1, 5 * mm)]

# ---------- Indicadores e conferência ----------
S_ += [P("3. Fórmulas e conferência independente", H1),
       table([["Indicador", "Fórmula", "Regra importante"],
              ["I1 · Desvio", "desvio = observado − esperado (kWh/dia). Relativo = 100 × desvio ÷ esperado", "Relativo só quando esperado &gt; 0; senão mostra o absoluto e “n/c”. Dia inválido vira lacuna, nunca zero"],
              ["I2 · Soma dos positivos, negativos e saldo", "Σ dos desvios &gt; 0 (ordena); Σ dos &lt; 0; saldo = soma dos dois", "O saldo deixa dias abaixo compensarem dias acima. Por isso a ordem usa a soma dos positivos"],
              ["I3 · Perfil horário", "Mediana, entre os dias do tipo, da potência média por hora (kW)", "Dia útil e fim de semana separados, mesma escala"]],
             [34 * mm, 66 * mm, W - 100 * mm]),
       P("Conta feita fora do painel", H2),
       P("O script <font name='DVB'>conta_independente.py</font> usa só a biblioteca padrão do Python, lê o CSV bruto e não reaproveita código do pipeline. Esse é o ponto que o professor pede: repetir o mesmo código em outro arquivo não vale como conferência."),
       table([["Caso", "Esperado (mediana)", "Observado", "Desvio", "Pipeline mostra", "Diferença"],
              ["z1_AC1, segunda 12/11, ref. A", "284,0763 kWh", "289,4012 kWh", "+5,3248 kWh", "+5,3248 kWh", "0,00003 kWh"],
              ["z4_AC1, 19/11, ref. B", "", "", "+1,3021 kWh", "+1,3021 kWh", "igual"]],
             [44 * mm, 28 * mm, 25 * mm, 24 * mm, 26 * mm, W - 147 * mm]),
       Spacer(1, 2 * mm),
       P("As entradas da primeira conta são as oito segundas de 09/09 a 03/11: 324,89; 332,12; 266,85; 287,48; 279,77; <b>0,00 (15/10, feriado)</b>; 280,68; 317,88 kWh. A mediana ignora o zero do feriado melhor que a média.", CELL),
       P("Conferência cruzada", H2),
       P("<font name='DVB'>conferencia_cruzada.js</font> compara o cálculo do painel (JavaScript) com o do Python em 2.016 valores (3 referências × 224 pares ativo-dia × 3 grandezas). Maior diferença: 0,0001 kWh, 0 falhas nos arquivos do repositório. Há ainda 5 testes unitários (pytest); o relatório cita 4; os outros cobrem o desempate do ranking (corrigido depois) e os nomes dos ativos."),
       P("Três casos de teste do painel", H2),
       table([["Caso", "Filtros", "O que o painel mostrou"],
              ["Recorte padrão", "z1_AC1, 04/11 a 01/12, ref. A", "+66,2 kWh, 9 dias acima, saldo −257,6, observado 5.226 × esperado 5.484 kWh. Confere com o Python"],
              ["Segundo recorte", "z4_AC1, 18 a 24/11, ref. B", "Acima em 5 de 7 dias (+10,4 kWh). Os números mudam com os filtros"],
              ["Vazio / denominador zero", "z4_Plug (esperado = 0) e 10 a 20/12 (sem dados)", "“acima em 0 de 28 dias”, relativo n/c; período vazio mostra “Sem dados no período” e esconde as vistas"]],
             [32 * mm, 50 * mm, W - 82 * mm])]
S_ += [Spacer(1, 5 * mm)]

# ---------- Evidências dos casos ----------
S_ += [P("4. Os casos de teste, em imagem", H1),
       P("Cada caso foi exportado do próprio painel. Servem de prova de que ele recalcula e de que trata zero e ausência de forma explícita.")]
w3 = (W - 8 * mm) / 3
cells = []
for f, cap in [("e4_recorte2_sem3_refB_z4AC1.png", "Segundo recorte: z4_AC1, semana 3, referência B"),
               ("e4_zero_z4Plug.png", "Denominador zero: z4_Plug (esperado = 0)"),
               ("e4_sem_dados.png", "Sem dados: período 10/12 a 20/12/2018")]:
    cells.append(img(EV / f, w3, cap))
S_ += [Table([cells], colWidths=[w3 + 4 * mm] * 3, style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))]
S_ += [P("Acessibilidade aplicada", H2)] + bullets([
    "Nada depende só da cor: vermelho sempre com ▲ e sinal +; observado × esperado também por linha contínua × tracejada e ponto × quadrado vazio.",
    "Cada vista tem título que resume o resultado e uma tabela equivalente (botão “Tabela”).",
    "Contrastes calculados (WCAG): texto 16,43:1, texto de apoio 7,56:1, observado 8,14:1, vermelho 6,57:1, cinza das barras 3,77:1 (gráfico, mínimo 3:1). Foco visível e ranking navegável por Tab e Enter.",
    "<b>Não verificado:</b> auditoria automática (axe), leitor de tela real e simulador de daltonismo. O relatório declara isso."])
S_ += [Spacer(1, 5 * mm)]

# ---------- Racionalização ----------
S_ += [P("5. Como chegamos neste painel", H1),
       P("O professor quer ver o raciocínio, não só a tela pronta: qual pergunta levou a cada elemento, qual alternativa foi descartada e o que mudou. Nossa evidência tem três versões do painel.")]
w3 = (W - 8 * mm) / 3
S_ += [Table([[img(EV / "rascunho_wireframe.png", w3, "Rascunho (reconstruído)"),
               img(EV / "painel_versao1_inicial.png", w3, "Versão 1 (ranking por saldo)"),
               img(EV / "painel_versao3_final.png", w3, "Versão 3 (final)")]],
             colWidths=[w3 + 4 * mm] * 3, style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))]
S_ += [P("Revisão 1: o ranking por saldo apontava o ativo errado", H2),
       P("Na versão 1 as barras de V2 eram o <b>saldo</b> e a ordem era pelo saldo. Resultado: z4_AC1 (único com saldo positivo, +25,7 kWh) ficou em primeiro e z1_AC1 ficou em <b>penúltimo</b> (saldo −257,6 kWh), embora tenha a maior soma de desvios positivos, +66,2 kWh em 9 dias. Dias abaixo da referência compensavam os dias acima."),
       P("<b>Mudança:</b> barras de positivos e negativos separadas, ordem pela soma dos positivos, saldo numa coluna à parte. <b>Efeito:</b> z1_AC1 passou de 7º para 1º, e a sobreposição de rótulos em z1_Light sumiu."),
       P("Revisão 2: da versão 2 para a final", H2),
       P("Motivada por crítica de integrante (“verboso”, sem número dominante) e pelas regras da apostila: bloco “Investigar primeiro” com um número grande, títulos que afirmam o resultado, barras de desvio em escala comum, explicações longas movidas para botões <b>?</b>."),
       P("Revisão 3: nomes legíveis e página de nomes (versão 4)", H2),
       P("Retorno do grupo: “um monte de nome feio, nenhum explicativo”. Conferido: o painel mostrava só os códigos do dado (z1_AC1, z1_Light, z1_Plug...) e nada explicava zona, tipo nem número. <b>Mudança:</b> o nome por extenso é derivado do código em um só lugar (e usado em todo o painel, com o código ao lado) e a nova página <font name='DVB'>nomes.html</font> explica como ler o código, lista os 8 ativos e define cada termo (esperado, desvio, saldo, n/c, lacuna, expediente, kW × kWh). <b>Verificado:</b> testes novos (vermelhos antes), conferência cruzada que falha se faltar rótulo e 12 medições de rolagem horizontal sem estouro. <b>Não verificado:</b> se um leitor de fora entende os nomes sem ajuda (o teste de leitura feito não perguntou sobre eles)."),
       callout("<b>Transparência (diga isso se perguntarem):</b> o rascunho inicial foi <b>redesenhado depois da versão 1</b>, a partir do plano que a originou. Não é um papel feito antes de codar. O relatório avisa isso. Se alguém tiver um rascunho real (papel ou Figma), ele deve substituir o arquivo <font name='DVB'>rascunho_wireframe.png</font>.")]
S_ += [PageBreak()]

# ---------- Sensibilidade ----------
S_ += [P("6. Sensibilidade: o que muda se mudarmos a premissa", H1),
       P("O professor pede mostrar como uma mudança justificada na linha de base ou no calendário altera o ranking. Soma dos desvios positivos (kWh), primeiros lugares:"),
       table([["Período", "A · 8 semanas", "B · 4 semanas", "C · sem feriados"],
              ["Mês inteiro", "<b>z1_AC1 66,2</b>; z4_AC1 38,4", "<b>z1_AC1 90,3</b>; z4_AC1 33,2", "<b>z1_AC1 55,5</b>; z4_AC1 36,8"],
              ["Semana 2 (11 a 17/11)", "z1_AC1 12,72; z4_AC1 12,68", "z1_AC1 16,57; z4_AC1 11,00", "<b>z4_AC1 12,17</b>; z1_AC1 9,32"],
              ["Semana 4 (25/11 a 01/12)", "z1_AC1 5,44; z4_AC1 2,17", "z1_AC1 9,29; z1_Plug 3,38", "<b>z4_AC1 2,05</b>; z1_AC1 2,04"]],
             [42 * mm, 44 * mm, 44 * mm, W - 130 * mm]),
       Spacer(1, 2 * mm)]
S_ += bullets(["<b>Mês inteiro:</b> a prioridade não muda (z1_AC1, depois z4_AC1), mas o excesso de z1_AC1 varia de 55,5 a 90,3 kWh conforme a referência.",
               "<b>Semanas:</b> o ativo priorizado <b>muda</b> nas semanas 2 e 4 quando os feriados saem da referência (C). Na semana 2 a diferença sob A já é só de 0,04 kWh, um empate técnico.",
               "<b>Causa:</b> os feriados de 13, 15 e 23/10 têm consumo zero. Em A e B eles entram como segunda ou terça “normais”, puxam a mediana para baixo e <b>inflam</b> os desvios positivos, sobretudo em B, que tem só 4 semanas.",
               "<b>Consequência:</b> a ordem por mês é robusta, a ordem semanal não. O painel recomenda tratar o topo como candidato, olhar a referência C e confirmar com o calendário real da unidade."])
S_ += [P("Segunda premissa: horário de expediente", H2),
       P("Parcela do consumo do mês fora do expediente, sob três hipóteses. Ela muda a <b>magnitude</b>, não a ordem: z3_Light segue o ativo com mais consumo fora do expediente."),
       table([["Expediente", "z1_AC1", "z1_Light", "z1_Plug", "z2_Light", "z2_Plug", "z3_Light", "z4_AC1"],
              ["07h às 18h (adotada)", "0,0%", "2,6%", "12,8%", "2,9%", "9,7%", "<b>37,1%</b>", "0,0%"],
              ["08h às 17h", "3,4%", "11,2%", "18,1%", "11,2%", "15,0%", "<b>47,9%</b>", "3,0%"],
              ["06h às 20h", "0,0%", "0,4%", "10,5%", "0,2%", "8,0%", "<b>26,6%</b>", "0,0%"]],
             [38 * mm] + [(W - 38 * mm) / 7] * 7),
       P("Isto é consumo fora do expediente <b>assumido</b>, não consumo dispensável. Iluminação de corredor e tomadas podem alimentar cargas essenciais, e só o gestor classifica.", SMALL)]
S_ += [Spacer(1, 5 * mm)]

# ---------- Limites ----------
S_ += [P("7. O que podemos e não podemos afirmar", H1),
       Table([[ [P("<b>Podemos dizer</b>", st("g", fontName="DVB", textColor=colors.HexColor("#1f6f3f"))), Spacer(1, 2 * mm)] + bullets([
                 "Neste recorte, z1_AC1 ficou acima da referência A em 9 de 28 dias (+66,2 kWh) e z4_AC1 em segundo lugar.",
                 "É onde começar a investigar, confirmando ocupação e agenda antes de qualquer decisão.",
                 "Os números foram recalculados fora do painel e por outra linguagem.",
                 "A ordem mensal resiste às três referências; a semanal não."], CELL),
               [P("<b>Não podemos dizer</b>", st("r", fontName="DVB", textColor=ACC)), Spacer(1, 2 * mm)] + bullets([
                 "Que o excesso é desperdício ou que há economia realizável.",
                 "Que a referência é o “consumo normal” medido: ela é estimada.",
                 "Que vale para cliente real ou para o Brasil: o dado é público e da Tailândia.",
                 "Que o uso fora do expediente é dispensável: calendário não é necessidade."], CELL)]],
             colWidths=[W / 2, W / 2], style=TableStyle([("BACKGROUND", (0, 0), (0, 0), OK), ("BACKGROUND", (1, 0), (1, 0), WARN),
                                                         ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)])),
       P("Pendências do grupo (marcadas no relatório, nada foi inventado)", H2),
       table([["Pendência", "O que falta", "Quem"],
              ["Teste de leitura (seção 12)", "Feito com uma participante anonimizada. Faltam: quem aplicou, data e tempo, e decidir se refaz com a versão 4. Resultado: leu bem os gráficos, mas não citou o ativo (z1_AC1), comparou os dois painéis da V3 em vez de dois recortes e não distinguiu kW de kWh. Uma sessão, pessoa que não é o gestor previsto", "Grupo"],
              ["Contribuições individuais (seção 16)", "Preenchidas para os 7. Cada integrante confirma a própria linha e aponta uma evidência verificável (os commits saem em nome de um só)", "Cada integrante"],
              ["Motivo da escolha dos 8 ativos", "O relatório já diz o que dá para verificar (4 zonas, 3 tipos de carga, z4_Plug de propósito) e que o motivo individual não foi registrado. Quem escolheu confirma o motivo real e ajusta a frase", "Quem montou o recorte"]],
             [44 * mm, W - 74 * mm, 30 * mm]),
       P("Uso de IA (declarado na seção 17)", H2),
       P("Claude Code foi usado por João Rietra para esboçar o pipeline, o painel e o relatório. As decisões de referência e o desenho final foram revisados após críticas do grupo. A verificação foi feita por testes, conta independente e conferência cruzada.")]
S_ += [Spacer(1, 5 * mm)]

# ---------- Perguntas ----------
S_ += [P("8. Perguntas que podem aparecer, e respostas curtas", H1),
       table([["Pergunta", "Resposta"],
              ["Por que dado da Tailândia?", "Não temos medição própria nem cliente. O CU-BEMS é dado real e público, com leituras por equipamento. Está rotulado como tal no painel e no relatório. Substituir por uma unidade piloto é a próxima etapa."],
              ["De onde vem o “esperado”?", "Mediana da energia diária dos dias com o mesmo dia da semana numa janela anterior (8 semanas, na referência A). Nunca inclui o período avaliado. É estimativa, não medição."],
              ["Por que ordenar por soma dos positivos e não por saldo?", "O saldo deixa dias abaixo compensarem dias acima. Na versão 1 isso colocou z1_AC1 em penúltimo, embora tenha o maior excesso. Corrigimos e documentamos (revisão 1)."],
              ["Isso mostra economia ou desperdício?", "Não. Desvio positivo é candidato a investigação. Confirmar ocupação, agenda e necessidade operacional antes de concluir."],
              ["A conclusão muda se mudarmos a referência?", "No mês, não: z1_AC1 e depois z4_AC1 nas três referências. Por semana, sim: nas semanas 2 e 4 o primeiro lugar muda quando tiramos os feriados."],
              ["Como sabem que o cálculo está certo?", "Quatro conferências: testes unitários, conta independente só com biblioteca padrão (diferença 0,00003 kWh), conferência cruzada JavaScript × Python em 2.016 valores, e execução do painel nos três casos."],
              ["Qual a diferença entre kW e kWh no painel?", "V3 mostra potência média por hora (kW). V1 e V2 mostram energia por dia (kWh = potência média × 24 h). Nunca somamos nem misturamos no mesmo eixo."],
              ["O que acontece sem dados ou com esperado zero?", "Período sem dados mostra “Sem dados no período” e esconde as vistas. Esperado zero (z4_Plug) mostra o desvio absoluto e “n/c” no relativo. Dia incompleto vira lacuna, não zero."],
              ["O rascunho foi feito antes do painel?", "Não: foi redesenhado depois da versão 1, e o relatório declara isso. A mudança entre versões está comprovada nas imagens."],
              ["O que o grupo ainda não fez?", "Registrar quem aplicou o teste de leitura, quando e quanto durou; decidir se refaz o teste com a versão 4; cada integrante confirmar a própria contribuição; confirmar o motivo da escolha dos 8 ativos."]],
             [52 * mm, W - 52 * mm])]
S_ += [Spacer(1, 5 * mm)]

# ---------- Mapa ----------
S_ += [P("9. Onde está cada coisa no pacote", H1),
       P("Pasta <font name='DVB'>av1-grupo-3-mapen/</font>. Para abrir o painel: <font name='DVB'>dashboard/index.html</font> (duplo clique). Estado por URL: <font name='DVB'>?ativo=z1_AC1&amp;de=2018-11-04&amp;ate=2018-12-01&amp;ref=A</font>."),
       table([["Evidência (índice do professor)", "Onde está"],
              ["E1 · Recorte e fluxo", "racionalizacao.pdf, seções 1 e 2"],
              ["E2 · Dados e qualidade", "dados/ (recorte, bases, dicionario.md); seções 5 e 6; evidencias/verificacoes_qualidade.json"],
              ["E3 · Referência e contas", "Seção 7; codigo/conta_independente.py; codigo/conferencia_cruzada.js; codigo/test_av1_desvio.py"],
              ["E4 · Protótipo", "dashboard/; seções 10 e 11; evidencias/e4_*.png"],
              ["E5 · Racionalização", "Seções 8 e 9 e Anexo A; evidencias/ (rascunho, versões 1 a 3, captura anotada)"],
              ["E6 · Validação e autoria", "Seções 11 a 17: sensibilidade, teste de leitura, acessibilidade, contribuições, IA"]],
             [60 * mm, W - 60 * mm]),
       P("Para reproduzir (na pasta av1-grupo-3-mapen/)", H2),
       table([["Passo", "Comando", "O que faz"],
              ["Atalho", "python rodar.py (Windows: py rodar.py)", "Faz tudo abaixo, confere cada resultado (OK, FALHOU ou PULADO) e abre o painel no navegador. Só biblioteca padrão; <font name='DVB'>--sem-abrir</font> não abre. Cerca de 20 s. Windows verificado por simulação, não em máquina Windows"],
              ["0", "pip install -r requirements.txt", "Instala pandas, numpy e pytest (use um ambiente virtual)"],
              ["1", "python codigo/av1_desvio.py", "Recalcula as bases e o dados.js do painel a partir do recorte por minuto. Não deve alterar nada versionado"],
              ["2", "python codigo/conta_independente.py z1_AC1 2018-11-12 A", "Refaz um desvio só com a biblioteca padrão"],
              ["3", "node codigo/conferencia_cruzada.js", "Compara painel (JS) com Python: 2.016 comparações, falhas 0"],
              ["4", "python -m pytest codigo -q", "7 testes passam"]],
             [14 * mm, 86 * mm, W - 100 * mm]),
       P("Requisitos: Python 3.11 ou mais novo (testado em 3.11, 3.12 e 3.13 no Linux) e Node (só para o passo 3; sem ele o passo é pulado). O painel é um arquivo HTML local, sem porta nem servidor. O LEIA-ME tem a instalação e a saída esperada de cada passo.", SMALL),
       Spacer(1, 6 * mm),
       callout("<b>Regra de ouro para explicar:</b> pergunta → dado → cálculo → escolha visual → elemento da tela → decisão e limite. Se alguém perguntar “por que este gráfico?”, aponte a pergunta (P1 a P3) e a alternativa descartada na seção 8 do relatório.", bg=SOFT, bar=NAVY)]

doc.build(S_)
print("ok", OUT)
