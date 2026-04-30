import flet as ft
import asyncio
from app import theme as th


_TERMS_TEXT = """
TERMOS DE USO — PIZZARIA CHECK-IN

Última atualização: 29 de abril de 2026

1. ACEITAÇÃO DOS TERMOS
Ao utilizar este sistema ("Pizzaria Check-In"), você concorda com os presentes Termos de Uso. Caso não concorde, não utilize o sistema.

2. DESCRIÇÃO DO SERVIÇO
O Pizzaria Check-In é uma plataforma de gestão de checklists de turno, destinada a restaurantes e seus colaboradores. O sistema permite que funcionários registrem a execução de tarefas e que gestores acompanhem e aprovem esses registros.

3. CONTA DE USUÁRIO
• O acesso é pessoal e intransferível.
• Você é responsável pela confidencialidade de sua senha.
• Em caso de suspeita de acesso não autorizado, notifique imediatamente o administrador do sistema.

4. USO ACEITÁVEL
É proibido:
• Fornecer informações falsas nos checklists.
• Compartilhar credenciais de acesso com terceiros.
• Tentar acessar dados de outros usuários ou módulos não autorizados.
• Utilizar o sistema para fins diferentes de gestão operacional do estabelecimento.

5. CONTEÚDO E FOTOS
• Fotos enviadas devem ser relacionadas às tarefas do checklist.
• O sistema armazena as imagens para fins de auditoria interna.
• Imagens inadequadas ou que violem a privacidade de terceiros são proibidas.

6. RESPONSABILIDADE
• O sistema é fornecido "como está", sem garantias de disponibilidade ininterrupta.
• O estabelecimento contratante é responsável pelo correto uso do sistema por seus colaboradores.
• Não nos responsabilizamos por decisões tomadas com base nos dados registrados.

7. MODIFICAÇÕES
Estes termos podem ser atualizados periodicamente. O uso continuado do sistema após notificação implica aceitação das alterações.

8. ENCERRAMENTO
O acesso pode ser revogado pelo administrador a qualquer momento, sem necessidade de justificativa.

9. CONTATO
Para dúvidas sobre estes termos, entre em contato com o administrador do seu estabelecimento.
""".strip()


_PRIVACY_TEXT = """
POLÍTICA DE PRIVACIDADE — PIZZARIA CHECK-IN

Última atualização: 29 de abril de 2026

1. RESPONSÁVEL PELO TRATAMENTO
O tratamento dos dados é realizado pelo estabelecimento contratante do sistema Pizzaria Check-In, que atua como Controlador de Dados nos termos da Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018).

2. DADOS COLETADOS
Coletamos os seguintes dados pessoais:
• Nome completo e endereço de e-mail (cadastro de usuário)
• Fotos de perfil (opcional)
• Fotos relacionadas às tarefas de checklist
• Registros de atividade: horários de login, execução de tarefas, envio de checklists
• Endereço IP (logs de acesso)

3. FINALIDADE DO TRATAMENTO
Os dados são utilizados exclusivamente para:
• Autenticação e controle de acesso ao sistema
• Gestão operacional dos turnos e tarefas do estabelecimento
• Auditoria interna das atividades realizadas
• Comunicação entre gestores e colaboradores dentro do sistema

4. BASE LEGAL
O tratamento está fundamentado no legítimo interesse do empregador na gestão operacional do estabelecimento (art. 7º, IX da LGPD) e no cumprimento de obrigações trabalhistas.

5. COMPARTILHAMENTO
Seus dados NÃO são compartilhados com terceiros, exceto:
• Quando exigido por lei ou ordem judicial
• Com provedores de infraestrutura tecnológica, sob acordo de confidencialidade

6. RETENÇÃO
Os dados são mantidos enquanto o colaborador estiver ativo no sistema. Após desligamento, os registros de auditoria são mantidos por até 5 anos para fins legais.

7. SEUS DIREITOS (LGPD)
Como titular dos dados, você tem direito a:
• Confirmar a existência de tratamento de seus dados
• Acessar os dados que temos sobre você
• Corrigir dados incompletos ou desatualizados
• Solicitar a eliminação dos dados pessoais
• Revogar o consentimento, quando aplicável

Para exercer seus direitos, entre em contato com o administrador do seu estabelecimento.

8. SEGURANÇA
Adotamos medidas técnicas e organizacionais para proteger seus dados:
• Senhas armazenadas com criptografia (hash bcrypt)
• Comunicação via HTTPS (em produção)
• Acesso restrito por perfil de usuário

9. COOKIES
O sistema utiliza armazenamento local (localStorage) apenas para manter sua sessão ativa. Não utilizamos cookies de rastreamento ou publicidade.

10. CONTATO
Em caso de dúvidas sobre o tratamento de seus dados pessoais, contate o administrador do estabelecimento ou o DPO responsável.
""".strip()


def build_terms_view(page: ft.Page, back_route: str = "/login", show_tab: str = "terms") -> ft.View:
    tab_idx = [0 if show_tab == "terms" else 1]

    tabs = ft.Tabs(
        selected_index=tab_idx[0],
        animation_duration=150,
        tabs=[
            ft.Tab(text="Termos de Uso"),
            ft.Tab(text="Privacidade"),
        ],
    )

    terms_body = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        content=ft.Text(_TERMS_TEXT, size=13, color=th.ON_SURFACE,
                        selectable=True),
    )
    privacy_body = ft.Container(
        padding=ft.Padding.symmetric(horizontal=16, vertical=12),
        content=ft.Text(_PRIVACY_TEXT, size=13, color=th.ON_SURFACE,
                        selectable=True),
    )

    scroll = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        controls=[terms_body],
    )

    def on_tab_change(e):
        scroll.controls = [terms_body if tabs.selected_index == 0 else privacy_body]
        page.update()

    tabs.on_change = on_tab_change
    scroll.controls = [terms_body if tab_idx[0] == 0 else privacy_body]

    def on_back(_):
        asyncio.create_task(page.push_route(back_route))

    return ft.View(
        route="/terms",
        bgcolor=th.BACKGROUND,
        padding=0,
        appbar=ft.AppBar(
            leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=on_back),
            title=ft.Text("Termos e Privacidade", size=17, weight=ft.FontWeight.W_600),
            bgcolor=th.SURFACE,
            elevation=1,
        ),
        controls=[
            ft.Column(
                [tabs, scroll],
                expand=True, spacing=0,
            )
        ],
    )
