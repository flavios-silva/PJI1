"""Acessibilidade do Pizzaria Check-In.

Reúne, num só lugar, os recursos de acessibilidade do aplicativo:

* tamanho do texto ajustável (100 %, 115 %, 130 % e 150 %);
* modo de alto contraste (preto sobre branco, contraste acima de 7:1);
* painel "Acessibilidade" acessível por botão e pelo atalho Alt+A;
* atalhos de teclado (Alt+A, Alt+C, Alt++, Alt+-, Alt+0);
* preferências salvas no aparelho (voltam na próxima visita);
* botão de acessibilidade em todas as telas.

O tradutor de Libras (VLibras) é carregado pelo arquivo assets/index.html
e só aparece na versão web.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import os

import flet as ft

from app import theme as th

FONT_SCALES = [1.0, 1.15, 1.3, 1.5]
FONT_LABELS = ["Normal", "Grande", "Maior", "Máximo"]
PREFS_KEY = "a11y_prefs"
_BASE_ATTR = "_a11y_base"
_LAST_ATTR = "_a11y_last"
_DEFAULT_TEXT_SIZE = 14
_DEFAULT_ICON_SIZE = 24

# Marcador para não inserir o botão de acessibilidade duas vezes.
_BTN_MARK = "a11y-button"


class Prefs:
    """Preferências de acessibilidade da pessoa usuária."""

    def __init__(self) -> None:
        self.font_index: int = 0
        self.high_contrast: bool = False

    @property
    def scale(self) -> float:
        return FONT_SCALES[self.font_index]

    def to_json(self) -> str:
        return json.dumps(
            {"font_index": self.font_index, "high_contrast": self.high_contrast}
        )

    def load_json(self, raw: str | None) -> None:
        if not raw:
            return
        try:
            data = json.loads(raw)
            idx = int(data.get("font_index", 0))
            self.font_index = max(0, min(idx, len(FONT_SCALES) - 1))
            self.high_contrast = bool(data.get("high_contrast", False))
        except (ValueError, TypeError):
            pass


class _Session:
    """Estado de UMA sessão (uma aba/pessoa). O servidor web atende várias
    pessoas ao mesmo tempo, então nada disto pode ser global."""

    def __init__(self) -> None:
        self.prefs = Prefs()
        self.storage: ft.SharedPreferences | None = None
        self.rebuild = None        # reconstrói as telas (definida em main.py)
        self.panel_open = False


# Preferências da sessão que está sendo atendida AGORA. É trocada por
# activate(page) no começo de cada ação. O código do app é síncrono entre um
# "await" e outro, então cada ação enxerga as preferências da sua própria sessão.
prefs = Prefs()


def _sess(page: ft.Page) -> _Session:
    s = page.__dict__.get("_a11y_state")
    if s is None:
        s = _Session()
        object.__setattr__(page, "_a11y_state", s)
    return s


def activate(page: ft.Page) -> None:
    """Passa a usar as preferências (texto e contraste) desta sessão."""
    global prefs
    s = _sess(page)
    prefs = s.prefs
    if th.HIGH_CONTRAST != s.prefs.high_contrast:
        th.set_high_contrast(s.prefs.high_contrast)


# ── Escala de texto ───────────────────────────────────────────────────────
def _scale_size(ctrl, default: int) -> None:
    """Aplica a escala ao tamanho de um Text/Icon, guardando o tamanho original."""
    scale = prefs.scale
    current = getattr(ctrl, "size", None)
    last = ctrl.__dict__.get(_LAST_ATTR)
    # Se o código da tela mudou o tamanho depois, o novo valor vira a base.
    if _BASE_ATTR not in ctrl.__dict__ or current != last:
        object.__setattr__(ctrl, _BASE_ATTR, current)
    base = ctrl.__dict__[_BASE_ATTR]
    if base is None and scale == 1.0:
        new = None
    else:
        new = round((base if base is not None else default) * scale, 1)
    object.__setattr__(ctrl, _LAST_ATTR, new)
    if new != current:
        ctrl.size = new


def install_scaling() -> None:
    """Faz todo Text e Icon criado no app respeitar o tamanho de texto escolhido."""
    for cls, default in ((ft.Text, _DEFAULT_TEXT_SIZE), (ft.Icon, _DEFAULT_ICON_SIZE)):
        if getattr(cls, "_a11y_patched", False):
            continue
        original = cls.before_update

        def make(orig, dflt):
            def before_update(self):
                orig(self)
                _scale_size(self, dflt)

            return before_update

        cls.before_update = make(original, default)
        cls._a11y_patched = True


def _children(ctrl):
    for f in dataclasses.fields(ctrl):
        value = getattr(ctrl, f.name, None)
        if isinstance(value, ft.Control):
            yield value
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, ft.Control):
                    yield item


def rescale_tree(root) -> None:
    """Reaplica a escala em controles que já estão na tela."""
    seen = set()
    stack = [root]
    while stack:
        c = stack.pop()
        if id(c) in seen or c is None:
            continue
        seen.add(id(c))
        if isinstance(c, ft.Text):
            _scale_size(c, _DEFAULT_TEXT_SIZE)
        elif isinstance(c, ft.Icon):
            _scale_size(c, _DEFAULT_ICON_SIZE)
        try:
            stack.extend(_children(c))
        except TypeError:
            pass


# ── Persistência ──────────────────────────────────────────────────────────
def attach_storage(page: ft.Page) -> None:
    s = _sess(page)
    if s.storage is None:
        s.storage = ft.SharedPreferences()
        page.services.append(s.storage)


async def load_prefs(page: ft.Page) -> None:
    """Lê as preferências salvas neste aparelho e já aplica o contraste."""
    s = _sess(page)
    try:
        if s.storage is not None:
            s.prefs.load_json(await s.storage.get(PREFS_KEY))
    except Exception:
        pass
    activate(page)


async def _save_prefs(page: ft.Page) -> None:
    s = _sess(page)
    try:
        if s.storage is not None:
            await s.storage.set(PREFS_KEY, s.prefs.to_json())
    except Exception:
        pass


# ── Ações ─────────────────────────────────────────────────────────────────
def set_rebuild_callback(page: ft.Page, fn) -> None:
    _sess(page).rebuild = fn


def _apply_font(page: ft.Page, extra_roots=()) -> None:
    activate(page)
    for view in page.views:
        rescale_tree(view)
    for root in extra_roots:
        rescale_tree(root)
    page.update()


def change_font(page: ft.Page, delta: int | None, extra_roots=()) -> None:
    """delta=+1 aumenta, -1 diminui, None volta ao normal."""
    activate(page)
    if delta is None:
        prefs.font_index = 0
    else:
        prefs.font_index = max(0, min(prefs.font_index + delta, len(FONT_SCALES) - 1))
    _apply_font(page, extra_roots)
    asyncio.create_task(_save_prefs(page))


def set_contrast(page: ft.Page, enabled: bool) -> None:
    s = _sess(page)
    s.prefs.high_contrast = enabled
    activate(page)
    page.theme = th.get_theme()
    if s.rebuild:
        s.rebuild()
    asyncio.create_task(_save_prefs(page))


# ── Painel "Acessibilidade" ───────────────────────────────────────────────
def show_panel(page: ft.Page, state=None) -> None:
    sess = _sess(page)
    if sess.panel_open:
        return
    activate(page)
    sess.panel_open = True

    size_label = ft.Text(weight=ft.FontWeight.W_600, color=th.ON_SURFACE)
    size_hint = ft.Text(size=12, color=th.ON_SURFACE_VARIANT)

    def refresh_labels():
        pct = int(round(prefs.scale * 100))
        size_label.value = f"{FONT_LABELS[prefs.font_index]} ({pct}%)"
        size_hint.value = (
            "Tamanho máximo."
            if prefs.font_index == len(FONT_SCALES) - 1
            else "Toque em A+ para aumentar o texto."
        )
        minus.disabled = prefs.font_index == 0
        plus.disabled = prefs.font_index == len(FONT_SCALES) - 1

    def on_minus(e):
        change_font(page, -1, extra_roots=(dlg,))
        refresh_labels()
        page.update()

    def on_plus(e):
        change_font(page, +1, extra_roots=(dlg,))
        refresh_labels()
        page.update()

    minus = ft.OutlinedButton(
        "A−", tooltip="Diminuir o texto", on_click=on_minus,
        style=ft.ButtonStyle(color=th.PRIMARY, padding=ft.Padding.symmetric(horizontal=16, vertical=14)),
    )
    plus = ft.OutlinedButton(
        "A+", tooltip="Aumentar o texto", on_click=on_plus,
        style=ft.ButtonStyle(color=th.PRIMARY, padding=ft.Padding.symmetric(horizontal=16, vertical=14)),
    )

    def on_contrast(e):
        # Fecha e reabre o painel para ele também receber as novas cores.
        close(None)
        set_contrast(page, bool(e.control.value))
        show_panel(page, state)

    contrast_switch = ft.Switch(
        label="Alto contraste",
        value=prefs.high_contrast,
        on_change=on_contrast,
        # Cores fortes nos dois estados (ligado/desligado) e borda visível.
        active_color=ft.Colors.WHITE,
        active_track_color=th.PRIMARY,
        inactive_thumb_color=th.ON_SURFACE,
        inactive_track_color=th.SURFACE,
        track_outline_color=th.ON_SURFACE,
        track_outline_width=2,
    )

    def on_reset(e):
        was_contrast = prefs.high_contrast
        prefs.font_index = 0
        if was_contrast:
            close(None)
            set_contrast(page, False)
            show_panel(page, state)
            return
        _apply_font(page, extra_roots=(dlg,))
        refresh_labels()
        asyncio.create_task(_save_prefs(page))
        page.update()

    def open_statement(e):
        close(None)
        asyncio.create_task(page.push_route("/acessibilidade"))

    is_web = os.getenv("WEB_MODE", "0") == "1"
    libras_text = (
        "Tradução para Libras: toque no botão azul do VLibras, no canto da tela, "
        "e selecione o texto que deseja traduzir."
        if is_web
        else "Tradução para Libras (VLibras): disponível na versão web do aplicativo."
    )

    shortcuts = [
        ("Alt + A", "Abrir este painel"),
        ("Alt + C", "Ligar ou desligar o alto contraste"),
        ("Alt + +", "Aumentar o texto"),
        ("Alt + -", "Diminuir o texto"),
        ("Alt + 0", "Voltar ao tamanho normal"),
        ("Tab / Shift + Tab", "Ir para o próximo / anterior"),
        ("Enter ou Espaço", "Ativar o item selecionado"),
    ]

    def section(title: str) -> ft.Control:
        return ft.Semantics(
            header=True,
            content=ft.Text(title, size=15, weight=ft.FontWeight.BOLD, color=th.ON_SURFACE),
        )

    content = ft.Column(
        [
            section("Tamanho do texto"),
            ft.Row([minus, size_label, plus], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
            size_hint,
            ft.Divider(height=8),
            section("Cores"),
            contrast_switch,
            ft.Text("Deixa as cores mais fortes e os textos pretos.", size=12, color=th.ON_SURFACE_VARIANT),
            ft.Divider(height=8),
            section("Libras"),
            ft.Text(libras_text, size=13, color=th.ON_SURFACE),
            ft.Divider(height=8),
            section("Atalhos de teclado"),
            *[
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(k, size=12, weight=ft.FontWeight.W_600, color=th.ON_SURFACE),
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border=ft.Border.all(1, th.ON_SURFACE_VARIANT),
                            border_radius=6,
                        ),
                        ft.Text(d, size=13, color=th.ON_SURFACE, expand=True),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
                for k, d in shortcuts
            ],
            ft.Divider(height=8),
            ft.TextButton(
                "Ler a declaração de acessibilidade",
                icon=ft.Icons.ARTICLE_OUTLINED,
                on_click=open_statement,
                style=ft.ButtonStyle(color=th.PRIMARY),
            ),
        ],
        spacing=8,
        tight=True,
        scroll=ft.ScrollMode.AUTO,
        width=360,
    )

    def close(e):
        sess.panel_open = False
        dlg.open = False
        page.update()

    dlg = ft.AlertDialog(
        modal=False,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.ACCESSIBILITY_NEW, color=th.PRIMARY, semantics_label=""),
                ft.Text("Acessibilidade", weight=ft.FontWeight.BOLD, color=th.ON_SURFACE),
            ],
            spacing=8,
        ),
        content=content,
        actions=[
            ft.TextButton("Restaurar padrão", on_click=on_reset, style=ft.ButtonStyle(color=th.ON_SURFACE)),
            ft.FilledButton(
                "Fechar", on_click=close, autofocus=True,
                style=ft.ButtonStyle(bgcolor=th.PRIMARY, color=ft.Colors.WHITE),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=th.SURFACE,
        on_dismiss=lambda e: setattr(sess, "panel_open", False),
    )
    refresh_labels()
    page.show_dialog(dlg)
    rescale_tree(dlg)
    page.update()


# ── Botão e atalhos ───────────────────────────────────────────────────────
def build_button(page: ft.Page, state=None, color=ft.Colors.WHITE) -> ft.IconButton:
    btn = ft.IconButton(
        icon=ft.Icons.ACCESSIBILITY_NEW,
        icon_color=color,
        tooltip="Acessibilidade (Alt+A)",
        on_click=lambda e: show_panel(page, state),
    )
    object.__setattr__(btn, _BTN_MARK, True)
    return btn


def decorate_views(page: ft.Page, state=None) -> None:
    """Garante o botão de acessibilidade na barra superior de cada tela."""
    activate(page)
    for view in page.views:
        bar = view.appbar
        if bar is None:
            # Telas sem barra (entrada, configuração inicial): cria uma barra enxuta.
            view.appbar = ft.AppBar(
                bgcolor=th.PRIMARY,
                toolbar_height=48,
                automatically_imply_leading=False,
                title=ft.Text(""),
                actions=[build_button(page, state)],
            )
            continue
        actions = list(bar.actions or [])
        if not any(getattr(a, _BTN_MARK, False) for a in actions):
            actions.insert(0, build_button(page, state))
            bar.actions = actions


def install_keyboard_shortcuts(page: ft.Page, state=None) -> None:
    def on_key(e: ft.KeyboardEvent):
        if not e.alt or e.ctrl:
            return
        key = (e.key or "").upper()
        if key == "A":
            show_panel(page, state)
        elif key == "C":
            set_contrast(page, not prefs.high_contrast)
        elif key in ("+", "=", "ADD", "NUMPAD ADD"):
            change_font(page, +1)
        elif key in ("-", "SUBTRACT", "NUMPAD SUBTRACT", "MINUS"):
            change_font(page, -1)
        elif key in ("0", "NUMPAD 0"):
            change_font(page, None)

    page.on_keyboard_event = on_key


# ── Ajudas para as telas ──────────────────────────────────────────────────
def live_message(control: ft.Control) -> ft.Semantics:
    """Envolve uma mensagem de erro/aviso para o leitor de tela anunciá-la sozinho.

    O Container fica sempre visível (o Semantics exige conteúdo visível), mesmo
    quando o texto de dentro está oculto.
    """
    return ft.Semantics(live_region=True, content=ft.Container(content=control))
