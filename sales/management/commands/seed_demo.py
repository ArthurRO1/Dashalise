"""Create a repeatable, fictional company dataset for live presentations."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from sales.models import (
    Alert, Company, Goal, KnowledgeArticle, Product, ProductSpecialization,
    Sale, Team, TeamMembership,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Cria ou atualiza os dados fictícios usados na demonstração."

    @transaction.atomic
    def handle(self, *args, **options):
        company = Company.objects.filter(name="Índigo Comércio Demonstrativo").first()
        if company:
            company.name = "Dashalise Comércio Demonstrativo"
            company.save(update_fields=["name"])
        else:
            company, _ = Company.objects.get_or_create(name="Dashalise Comércio Demonstrativo")
        users = {}
        people = [
            ("mariana@demo.local", "Mariana", "Costa"),
            ("rafael@demo.local", "Rafael", "Mendes"),
            ("camila@demo.local", "Camila", "Rocha"),
            ("alex@demo.local", "Alex", "Silva"),
            ("joao@demo.local", "João", "Pedro"),
            ("beatriz@demo.local", "Beatriz", "Lima"),
            ("caio@demo.local", "Caio", "Santos"),
            ("ana@demo.local", "Ana", "Freitas"),
            ("paula@demo.local", "Paula", "Nunes"),
            ("lucas@demo.local", "Lucas", "Almeida"),
            ("nina@demo.local", "Nina", "Ferreira"),
        ]
        for email, first, last in people:
            user, _ = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": first, "last_name": last},
            )
            users[email] = user

        aurora, _ = Team.objects.get_or_create(company=company, name="Aurora", defaults={"supervisor": users["rafael@demo.local"]})
        Team.objects.filter(pk=aurora.pk).update(supervisor=users["rafael@demo.local"])
        team_specs = [("Horizonte", "paula@demo.local"), ("Vértice", "lucas@demo.local"), ("Órbita", "nina@demo.local")]
        teams = [aurora]
        for name, supervisor_email in team_specs:
            team, _ = Team.objects.get_or_create(
                company=company, name=name, defaults={"supervisor": users[supervisor_email]}
            )
            Team.objects.filter(pk=team.pk).update(supervisor=users[supervisor_email])
            teams.append(team)

        assignments = {
            aurora: ["mariana@demo.local", "joao@demo.local", "beatriz@demo.local", "caio@demo.local", "ana@demo.local"],
            teams[1]: ["paula@demo.local"],
            teams[2]: ["lucas@demo.local"],
            teams[3]: ["nina@demo.local"],
        }
        for team, members in assignments.items():
            for email in members:
                TeamMembership.objects.get_or_create(team=team, user=users[email])

        products = []
        for sku, name in [("BAS-01", "Plano Essencial"), ("PRO-02", "Plano Pro"), ("ENT-03", "Pacote Enterprise"), ("ADD-04", "Módulo Analytics")]:
            product, _ = Product.objects.get_or_create(company=company, sku=sku, defaults={"name": name})
            products.append(product)

        default_guidance = [
            ("Planos digitais", "Assinaturas e serviços digitais", products[:2],
             "Pequenas equipes que precisam organizar processos e acompanhar resultados.",
             "Compare limites de uso, suporte e recursos incluídos; conecte cada benefício a uma necessidade confirmada.",
             "Não prometa integrações ou recursos que não estejam descritos no catálogo atualizado.",
             "Como sua equipe trabalha hoje? Quantas pessoas usarão a plataforma? Qual resultado quer melhorar?",
             "Investigue antes de recomendar. Demonstre um recurso relevante e explique limites, preço e próximos passos com clareza."),
            ("Soluções empresariais", "Tecnologia para empresas", [products[2], products[3]],
             "Empresas que avaliam segurança, escala, integrações e decisão compartilhada.",
             "Mapeie os critérios técnicos e as pessoas envolvidas; apresente evidências e um plano de implantação realista.",
             "Não afirme conformidade, SLA ou integração sem documentação aprovada.",
             "Que sistemas precisam conversar? Quem aprova a solução? Como será medido o sucesso?",
             "Use perguntas consultivas, esclareça dependências e proponha uma validação técnica antes da decisão."),
        ]
        for title, category, linked_products, audience, differentiators, limitations, questions, guidance in default_guidance:
            profile, _ = ProductSpecialization.objects.get_or_create(
                company=company,
                title=title,
                defaults={
                    "category": category,
                    "audience": audience,
                    "differentiators": differentiators,
                    "limitations": limitations,
                    "recommended_questions": questions,
                    "sales_guidance": guidance,
                },
            )
            profile.products.set(linked_products)

        today = timezone.localdate()
        start = today.replace(day=1)
        end = today
        month_end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        goal_specs = [
            (Goal.Scope.USER, users["mariana@demo.local"], None, Decimal("40000.00")),
            (Goal.Scope.TEAM, None, aurora, Decimal("38000.00")),
            (Goal.Scope.COMPANY, None, None, Decimal("120000.00")),
        ]
        for scope, user, team, target in goal_specs:
            Goal.objects.update_or_create(
                company=company, scope=scope, user=user, team=team,
                period_start=start, defaults={"period_end": month_end, "target_amount": target},
            )

        for email in ("mariana@demo.local", "joao@demo.local", "beatriz@demo.local", "caio@demo.local", "ana@demo.local", "paula@demo.local", "lucas@demo.local", "nina@demo.local"):
            Goal.objects.update_or_create(
                company=company, scope=Goal.Scope.USER, user=users[email], team=None,
                period_start=start,
                defaults={"period_end": month_end, "target_amount": Decimal("40000.00") if email == "mariana@demo.local" else Decimal("30000.00")},
            )

        sale_specs = [
            ("M-001", "mariana@demo.local", products[1], "8450.00", 2),
            ("M-002", "mariana@demo.local", products[0], "6280.00", 4),
            ("M-003", "mariana@demo.local", products[2], "5910.00", 7),
            ("M-004", "mariana@demo.local", products[1], "4360.00", 9),
            ("M-005", "mariana@demo.local", products[3], "3740.00", 11),
            ("A-006", "joao@demo.local", products[1], "6280.00", 5),
            ("A-007", "beatriz@demo.local", products[2], "5910.00", 8),
            ("A-008", "caio@demo.local", products[0], "4360.00", 10),
            ("H-009", "paula@demo.local", products[2], "7280.00", 4),
            ("V-010", "lucas@demo.local", products[0], "5150.00", 6),
            ("O-011", "nina@demo.local", products[1], "6890.00", 8),
        ]
        for external_id, email, product, amount, day in sale_specs:
            sold_at = start.replace(day=min(day, end.day))
            Sale.objects.get_or_create(
                company=company, external_id=external_id,
                defaults={
                    "seller": users[email], "team": aurora if email in assignments[aurora] else next(
                        team for team, members in assignments.items() if email in members
                    ),
                    "product": product, "amount": Decimal(amount), "sold_at": sold_at,
                    "customer_name": "Cliente demonstrativo", "commission_rate": Decimal("5.00"),
                },
            )

        alert_specs = [
            ("Meta em ritmo de atenção", "Caio Santos está abaixo do ritmo necessário para sua meta.", Alert.Severity.WARNING, aurora, users["caio@demo.local"]),
            ("Oportunidade de crescimento", "O Plano Pro apresenta procura crescente neste período.", Alert.Severity.INFO, aurora, None),
            ("Queda incomum de conversão", "A equipe Vértice requer uma revisão dos últimos resultados.", Alert.Severity.WARNING, teams[2], None),
        ]
        for title, message, severity, team, user in alert_specs:
            Alert.objects.get_or_create(
                company=company, title=title,
                defaults={"message": message, "severity": severity, "team": team, "user": user},
            )

        knowledge = [
            ("observe", "1 · Observar e preparar", "venda", "Prepare-se sem presumir: identifique se o cliente é novo ou recorrente, o produto que procura e o contexto disponível. Abra a conversa com naturalidade. O perfil de compra descreve a situação atual e não define a personalidade do cliente."),
            ("investigate", "2 · Investigar com SPIN", "spin", "SPIN: Situação — entenda como o cliente está hoje; Problema — descubra dificuldades; Implicação — explore consequências com respeito; Necessidade de solução — ajude o cliente a expressar o resultado que deseja. Use perguntas abertas e escuta ativa. Não apresente produto antes de compreender a necessidade. Confirme hipóteses em vez de presumir intenções."),
            ("classify", "3 · Classificar o momento de compra", "clientes", "Oito cenários temporários: explorador (facilite descoberta sem pressão); comparador (explique critérios e diferenças); sensível a preço (pergunte orçamento e prioridades); exigente (demonstre qualidade e evidências); indeciso (reduza opções e pergunte critérios); apressado (seja conciso); desconfiado (apresente provas e limites); recorrente (consulte histórico e experiência). São hipóteses, não rótulos fixos. Em B2B, identifique usuários, influenciadores, decisores e critérios de validação."),
            ("personalize", "4 · Personalizar a abordagem", "venda", "Adapte linguagem, quantidade de opções, evidências e ritmo ao que o cliente explicitou. Cliente apressado pode preferir uma comparação concisa; comparador pode valorizar critérios claros; cliente desconfiado precisa de provas e limitações transparentes. Em B2C, entenda a prioridade individual; em B2B, investigue impacto, requisitos, aprovação e consenso entre participantes."),
            ("value", "5 · Construir valor com Challenger", "challenger", "Ensine uma perspectiva útil (Teach), personalize a explicação (Tailor) e conduza próximos passos com segurança (Take Control). Relacione características a benefícios que importam para este cliente. Crie clareza sobre necessidades que o próprio cliente reconhece; nunca invente uma necessidade, fabrique urgência, use pressão ou prometa resultados sem evidência."),
            ("decision", "6 · Conduzir a decisão e objeções", "objeções", "Investigue o motivo real da objeção antes de responder: preço, confiança, utilidade, timing ou decisão compartilhada. Para preço, entenda orçamento antes de defender valor; para desconfiança, ofereça demonstração, garantia ou prova documentada; para indecisão, reduza opções; se outra pessoa participa, combine como envolvê-la. Compare alternativas com honestidade e deixe espaço para o cliente decidir sem pressão."),
            ("learn", "7 · Aprender e acompanhar", "pós-venda", "Registre necessidade, solução, resultado e objeções para apoiar um pós-venda útil. Observe taxa de conversão, ticket médio, identificação de necessidades, qualidade da argumentação, tratamento de objeções, satisfação, recompra e cancelamentos em conjunto. Vendas altas sem satisfação ou adequação não representam necessariamente qualidade. Feedback avaliativo deve seguir critérios transparentes e contexto suficiente."),
            ("general", "Princípios para conversas comerciais", "princípios", "A venda adaptativa combina observação, investigação, classificação circunstancial, personalização, construção de valor, condução da decisão e aprendizado. O assistente responde dúvidas e oferece roteiros como referência; não faz avaliação automática de funcionário por padrão. Nunca invente benefícios, estatísticas ou garantias."),
        ]
        for stage, title, category, content in knowledge:
            KnowledgeArticle.objects.update_or_create(
                company=company,
                title=title,
                defaults={"stage": stage, "category": category, "content": content, "active": True},
            )

        self.stdout.write(self.style.SUCCESS("Dados demonstrativos criados/atualizados com sucesso."))
        self.stdout.write("Perfis: funcionario, supervisor, gerente e administrador (sem senha; modo apresentação).")
