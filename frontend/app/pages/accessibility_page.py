"""Declaração de acessibilidade do Pizzaria Check-In (rota /acessibilidade).

Texto em linguagem simples: frases curtas, uma ideia por frase, sem jargão.
"""
import asyncio

import flet as ft

from app import theme as th
from app import a11y

# (título, [parágrafos ou itens]). Itens que começam com "• " viram lista.
_SECTIONS: list[tuple[str, list[str]]] = [
    (
        "O que fizemos",
        [
            "Queremos que todas as pessoas consigam usar o aplicativo, "
            "inclusive quem tem alguma deficiência. Seguimos as diretrizes "
            "WCAG 2.2, nível AA, e a lei brasileira de inclusão (Lei nº 13.146/2015).",
        ],
    ),
    (
        "Para quem usa leitor de tela",
        [
            "• Botões e ícones têm nome lido em voz alta.",
            "• Fotos têm descrição. A descrição diz de qual item da tarefa é a foto.",
            "• Os títulos das telas são marcados como títulos, para você pular de um para outro.",
            "• Mensagens de erro e de sucesso são anunciadas sozinhas.",
            "• O estado é dito com palavras, não só com cor. Exemplo: "
            "\"Aguardando Revisão\", \"Aprovado\".",
        ],
    ),
    (
        "Libras",
        [
            "• Na versão web, o botão azul do VLibras fica no canto da tela.",
            "• Toque nele e selecione um texto. Um avatar traduz para Libras.",
            "• O VLibras é um serviço do governo federal e precisa de internet.",
            "• O app não tem vídeos. Se passar a ter, todos terão legenda.",
        ],
    ),
    (
        "Só com o teclado",
        [
            "• Tab vai para o próximo item. Shift + Tab volta.",
            "• Enter ou Espaço ativa o item selecionado.",
            "• Esc fecha janelas.",
            "• O item selecionado tem uma borda amarela e preta, bem visível.",
            "• Alt + A abre o painel de acessibilidade, em qualquer tela.",
        ],
    ),
    (
        "Cores e letras",
        [
            "• As cores têm contraste de pelo menos 4,5 para 1 (WCAG AA).",
            "• O alto contraste chega a 7 para 1 ou mais (WCAG AAA). "
            "Atalho: Alt + C.",
            "• O texto pode ir de 100% a 150%. Atalhos: Alt + + e Alt + -.",
            "• Suas escolhas ficam salvas neste aparelho.",
            "• Nenhuma informação depende só de cor.",
            "• O app funciona em pé e deitado.",
        ],
    ),
    (
        "Linguagem",
        [
            "• Usamos frases curtas e palavras do dia a dia.",
            "• Erros dizem o que aconteceu e como resolver.",
        ],
    ),
    (
        "O que ainda não está perfeito",
        [
            "• O VLibras pode errar em palavras técnicas.",
            "• O app web é feito com Flutter. Alguns leitores de tela podem "
            "ler certas telas de forma diferente. Os melhores resultados "
            "são com NVDA ou JAWS no Chrome ou Edge, e TalkBack no Android.",
        ],
    ),
    (
        "Encontrou um problema?",
        [
            "Fale com o administrador do seu estabelecimento. Diga qual tela, "
            "o que aconteceu e qual leitor de tela ou navegador você usa. "
            "Vamos responder e corrigir o mais rápido possível.",
        ],
    ),
]


def _heading(text: str, level: int = 2, size: int = 17) -> ft.Control:
    return ft.Semantics(
        header=True,
        heading_level=level,
        content=ft.Text(text, size=size, weight=ft.FontWeight.BOLD, color=th.ON_SURFACE),
    )


def build_accessibility_view(page: ft.Page, back_route: str) -> ft.View:
    def on_back(_):
        asyncio.create_task(page.push_route(back_route))

    body: list[ft.Control] = [
        _heading("Declaração de acessibilidade", level=1, size=22),
        ft.Text(
            "Última revisão: outubro de 2026.",
            size=12, color=th.ON_SURFACE_VARIANT,
        ),
    ]
    for title, lines in _SECTIONS:
        body.append(ft.Container(height=8))
        body.append(_heading(title))
        for line in lines:
            body.append(
                ft.Text(line, size=14, color=th.ON_SURFACE, selectable=True)
            )

    body.append(ft.Container(height=8))
    body.append(
        ft.FilledButton(
            "Abrir o painel de acessibilidade",
            icon=ft.Icons.ACCESSIBILITY_NEW,
            on_click=lambda e: a11y.show_panel(page),
            style=ft.ButtonStyle(bgcolor=th.PRIMARY, color=ft.Colors.WHITE),
        )
    )

    return ft.View(
        route="/acessibilidade",
        bgcolor=th.BG,
        padding=0,
        appbar=ft.AppBar(
            leading=ft.IconButton(
                ft.Icons.ARROW_BACK,
                tooltip="Voltar",
                icon_color=ft.Colors.WHITE,
                on_click=on_back,
            ),
            title=ft.Text("Acessibilidade", color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
            bgcolor=th.PRIMARY,
        ),
        controls=[
            ft.Column(
                [ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=12),
                    content=ft.Column(body, spacing=6, horizontal_alignment=ft.CrossAxisAlignment.START),
                )],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        ],
    )
