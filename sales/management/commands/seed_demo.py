"""Load the fictional Rede Aurora dataset supplied for internship challenge 2."""
import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sales.models import (
    Alert, Company, Conversation, DemoIdentity, Goal, KnowledgeArticle,
    PriorYearStoreSales, Product, ProductDemoPerformance, ProductSpecialization,
    Sale, SaleReflection, Team, TeamMembership,
)

User = get_user_model()
AS_OF = date.fromisoformat(settings.DEMO_AS_OF_DATE)
DATA_DIR = Path(settings.BASE_DIR) / "dados" / "desafio-2-dashboards"


def read_csv(filename):
    path = DATA_DIR / filename
    if not path.is_file():
        raise CommandError(f"Arquivo do Desafio 2 não encontrado: {path}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def decimal(value):
    return Decimal(value or "0").quantize(Decimal("0.01"))


def optional_date(value):
    return date.fromisoformat(value) if value else None


def split_name(value):
    parts = value.strip().split()
    return (parts[0], " ".join(parts[1:])) if parts else ("Usuário", "")


class Command(BaseCommand):
    help = "Substitui os dados ilustrativos pela base fictícia do Desafio 2 (Rede Aurora)."

    @transaction.atomic
    def handle(self, *args, **options):
        stores = read_csv("lojas.csv")
        roster = read_csv("vendedores.csv")
        user_rows = read_csv("usuarios.csv")
        daily_rows = read_csv("vendas_diarias_vendedor.csv")
        store_goal_rows = read_csv("metas_loja.csv")
        seller_goal_rows = read_csv("metas_vendedor.csv")
        prior_rows = read_csv("vendas_loja_ano_anterior.csv")
        if not all((stores, roster, user_rows, daily_rows, store_goal_rows, seller_goal_rows, prior_rows)):
            raise CommandError("Um ou mais arquivos do Desafio 2 estão vazios.")

        company = Company.objects.order_by("id").first()
        if company is None:
            company = Company.objects.create(name="Rede Aurora")
        elif company.name != "Rede Aurora":
            company.name = "Rede Aurora"
            company.save(update_fields=["name"])

        # The demo's prior synthetic facts are replaced; participant-created knowledge
        # is reseeded below and operational conversation data is reset with the dataset.
        SaleReflection.objects.filter(company=company).delete()
        Conversation.objects.filter(company=company).delete()
        Sale.objects.filter(company=company).delete()
        PriorYearStoreSales.objects.filter(company=company).delete()
        Alert.objects.filter(company=company).delete()
        Goal.objects.filter(company=company).delete()
        ProductSpecialization.objects.filter(company=company).delete()
        ProductDemoPerformance.objects.filter(company=company).delete()
        KnowledgeArticle.objects.filter(company=company).delete()
        Product.objects.filter(company=company).delete()
        DemoIdentity.objects.filter(company=company).delete()
        Team.objects.filter(company=company).delete()

        user_by_email = {}
        user_by_external_id = {}
        identity_by_external_id = {}
        vendor_by_id = {row["vendedor_id"]: row for row in roster}
        for row in user_rows:
            first_name, last_name = split_name(row["nome"])
            email = row["email"].strip().lower()
            user, _ = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": first_name, "last_name": last_name},
            )
            update_fields = []
            for field, value in (("email", email), ("first_name", first_name), ("last_name", last_name)):
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    update_fields.append(field)
            vendor = vendor_by_id.get(row["vendedor_id"])
            termination = optional_date(vendor["data_desligamento"]) if vendor else None
            is_active = termination is None or termination >= AS_OF
            if user.is_active != is_active:
                user.is_active = is_active
                update_fields.append("is_active")
            if update_fields:
                user.save(update_fields=update_fields)
            identity, _ = DemoIdentity.objects.update_or_create(
                external_id=row["usuario_id"],
                defaults={
                    "company": company,
                    "user": user,
                    "source_role": row["papel"],
                    "scope": row["escopo"],
                    "whatsapp": row["whatsapp"],
                    "active_at_demo": is_active,
                    "hired_at": optional_date(vendor["data_admissao"]) if vendor else None,
                    "terminated_at": termination,
                },
            )
            user_by_email[email] = user
            user_by_external_id[row["usuario_id"]] = user
            identity_by_external_id[row["usuario_id"]] = identity

        vendor_user = {
            row["vendedor_id"]: user_by_email[row["email"].strip().lower()]
            for row in user_rows if row["vendedor_id"]
        }
        # The roster keeps sellers who left during the sample window, while the
        # user file only includes people still eligible to receive a dashboard.
        # Give former staff an internal, inactive identity so their dated sales
        # remain part of store/regional totals without exposing them as active users.
        for row in roster:
            vendor_id = row["vendedor_id"]
            if vendor_id in vendor_user:
                continue
            first_name, last_name = split_name(row["nome"])
            email = f"historico.{vendor_id.lower()}@aurora.example"
            person, _ = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": first_name, "last_name": last_name, "is_active": False},
            )
            DemoIdentity.objects.update_or_create(
                external_id=f"HIST-{vendor_id}",
                defaults={
                    "company": company,
                    "user": person,
                    "source_role": "vendedor_historico",
                    "scope": vendor_id,
                    "active_at_demo": False,
                    "hired_at": optional_date(row["data_admissao"]),
                    "terminated_at": optional_date(row["data_desligamento"]),
                },
            )
            vendor_user[vendor_id] = person
        regional_by_name = {
            user.get_full_name().casefold(): user
            for user in user_by_email.values()
            if user.demo_identity.source_role == "regional"
        }
        manager_by_vendor_id = {
            row["vendedor_id"]: vendor_user[row["vendedor_id"]]
            for row in roster
            if row["cargo"] == "gerente" and row["vendedor_id"] in vendor_user
        }

        teams = {}
        store_by_id = {row["loja_id"]: row for row in stores}
        for row in stores:
            regional_manager = regional_by_name.get(row["gerente_regional"].casefold())
            manager = next(
                (manager_by_vendor_id[person["vendedor_id"]] for person in roster
                 if person["loja_id"] == row["loja_id"] and person["cargo"] == "gerente"
                 and person["vendedor_id"] in manager_by_vendor_id),
                None,
            )
            team = Team.objects.create(
                company=company,
                name=row["nome"],
                external_id=row["loja_id"],
                city=row["cidade"],
                state=row["uf"],
                region_code=row["regional_id"],
                region_name=row["regional"],
                regional_manager_name=row["gerente_regional"],
                franchisee=row["franqueado"],
                store_type=row["tipo"],
                opened_at=optional_date(row["inauguracao"]),
                opens_sunday=row["abre_domingo"].strip().casefold() == "sim",
                supervisor=regional_manager,
                manager=manager,
            )
            teams[row["loja_id"]] = team

        memberships = []
        for row in roster:
            team = teams.get(row["loja_id"])
            person = vendor_user.get(row["vendedor_id"])
            if team and person:
                memberships.append(TeamMembership(team=team, user=person))
        TeamMembership.objects.bulk_create(memberships, ignore_conflicts=True, batch_size=1000)

        for row in store_goal_rows:
            team = teams[row["loja_id"]]
            period_start = date.fromisoformat(f"{row['mes']}-01")
            month_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            Goal.objects.create(
                company=company, scope=Goal.Scope.TEAM, team=team,
                period_start=period_start, period_end=month_end,
                target_amount=decimal(row["meta_valor"]),
            )
        for row in seller_goal_rows:
            person = vendor_user.get(row["vendedor_id"])
            team = teams.get(row["loja_id"])
            if not person or not team:
                continue
            period_start = date.fromisoformat(f"{row['mes']}-01")
            month_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            Goal.objects.create(
                company=company, scope=Goal.Scope.USER, user=person,
                period_start=period_start, period_end=month_end,
                target_amount=decimal(row["meta_valor"]),
            )
        company_targets = {}
        for row in store_goal_rows:
            company_targets[row["mes"]] = company_targets.get(row["mes"], Decimal("0")) + decimal(row["meta_valor"])
        for month, target in company_targets.items():
            period_start = date.fromisoformat(f"{month}-01")
            month_end = (period_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            Goal.objects.create(
                company=company, scope=Goal.Scope.COMPANY,
                period_start=period_start, period_end=month_end, target_amount=target,
            )

        sales = []
        for row in daily_rows:
            person = vendor_user.get(row["vendedor_id"])
            team = teams.get(row["loja_id"])
            if not person or not team:
                continue
            sold_at = date.fromisoformat(row["data"])
            sales.append(Sale(
                company=company,
                seller=person,
                team=team,
                product=None,
                external_id=f"daily:{row['vendedor_id']}:{row['data']}",
                customer_name="",
                amount=decimal(row["valor_vendido"]),
                commission_rate=Decimal("3.00"),
                sales_count=int(row["vendas"] or 0),
                pieces=int(row["pecas"] or 0),
                attendances=int(row["atendimentos"] or 0),
                sold_at=sold_at,
                status=Sale.Status.VALID,
            ))
        Sale.objects.bulk_create(sales, batch_size=1000)

        prior_sales = []
        for row in prior_rows:
            team = teams.get(row["loja_id"])
            if not team:
                continue
            prior_sales.append(PriorYearStoreSales(
                company=company,
                team=team,
                sold_at=date.fromisoformat(row["data"]),
                amount=decimal(row["valor_vendido"]),
                sales_count=int(row["vendas"] or 0),
                pieces=int(row["pecas"] or 0),
            ))
        PriorYearStoreSales.objects.bulk_create(prior_sales, batch_size=1000)
        self._seed_sales_method(company)
        self._seed_demo_products(company)

        self.stdout.write(self.style.SUCCESS(
            f"Rede Aurora carregada: {len(teams)} lojas, {len(user_rows)} usuários, "
            f"{len(sales)} registros vendedor-dia, {len(store_goal_rows) + len(seller_goal_rows) + len(company_targets)} metas "
            f"e {len(prior_sales)} registros de comparação anual."
        ))
        self.stdout.write("Perfis de demonstração: Bianca Rocha (funcionária), Patrícia Lemos (regional), Diego Furtado (gerente) e Marcos Albuquerque (diretoria).")
        self.stdout.write("Catálogo e desempenho de produtos são simulados e ficam separados das vendas dos vendedores.")

    @staticmethod
    def _seed_demo_products(company):
        products = [
            {
                "sku": "DEMO-VEST-001", "name": "Camiseta Essencial", "category": "Vestuário",
                "description": "Camiseta de malha de algodão, modelagem regular, tamanhos PP a XG.",
                "units": 146, "orders": 126, "revenue": "18900.00",
                "audience": "Pessoas que procuram uma peça casual para uso cotidiano.",
                "differentiators": "Malha de algodão e modelagem regular; tamanhos PP a XG.",
                "limitations": "Não há preço, cores disponíveis, certificação têxtil ou instrução de lavagem cadastrados.",
                "questions": "Qual modelagem costuma preferir? Há alguma cor, tamanho ou faixa de preço que devo considerar?",
                "guidance": "Confirme tamanho, caimento e faixa de preço antes de apresentar opções; não presuma que algodão seja a única prioridade.",
            },
            {
                "sku": "DEMO-VEST-002", "name": "Calça Jeans Reta", "category": "Vestuário",
                "description": "Calça jeans de modelagem reta, composição informada de algodão com elastano, tamanhos 36 a 48.",
                "units": 112, "orders": 102, "revenue": "34440.00",
                "audience": "Pessoas que procuram uma calça jeans de modelagem reta.",
                "differentiators": "Modelagem reta, composição cadastrada de algodão com elastano e tamanhos 36 a 48.",
                "limitations": "Percentual da composição, cores, preço e medidas da peça não estão cadastrados.",
                "questions": "Prefere cintura mais alta ou média? Qual numeração e tipo de caimento costuma funcionar melhor?",
                "guidance": "Ajude a confirmar numeração e caimento; ofereça prova e compare apenas características cadastradas.",
            },
            {
                "sku": "DEMO-CALC-003", "name": "Tênis Casual Urbano", "category": "Calçados",
                "description": "Tênis casual com cabedal sintético e solado de EVA, numeração 34 a 44.",
                "units": 95, "orders": 95, "revenue": "42750.00",
                "audience": "Pessoas que procuram um calçado casual para uso urbano.",
                "differentiators": "Cabedal sintético e solado de EVA; numeração 34 a 44.",
                "limitations": "Não há preço, peso, resistência à água, indicação esportiva ou política de garantia cadastrados.",
                "questions": "Em quais situações pretende usar o tênis? O que pesa mais para você: ajuste, material, estilo ou preço?",
                "guidance": "Investigue o uso pretendido e o ajuste. Não apresente o modelo como próprio para corrida nem prometa impermeabilidade.",
            },
            {
                "sku": "DEMO-VEST-004", "name": "Jaqueta Leve", "category": "Vestuário",
                "description": "Jaqueta leve de poliéster, modelagem regular, tamanhos P a GG.",
                "units": 74, "orders": 68, "revenue": "24480.00",
                "audience": "Pessoas que procuram uma terceira peça leve para compor o vestuário.",
                "differentiators": "Tecido de poliéster e modelagem regular, conforme cadastro demonstrativo.",
                "limitations": "Não há informação sobre impermeabilidade, forro, temperatura de uso, cores ou preço.",
                "questions": "Você procura uma camada para qual clima e ocasião? Há uma preferência de caimento ou tamanho?",
                "guidance": "Explique apenas o material e a modelagem cadastrados; confirme com a loja qualquer proteção contra chuva ou frio.",
            },
        ]
        period_start = date(2026, 10, 1)
        period_end = date(2026, 10, 31)
        for data in products:
            product, _ = Product.objects.update_or_create(
                company=company, sku=data["sku"],
                defaults={
                    "name": data["name"], "category": data["category"],
                    "description": data["description"], "active": True,
                },
            )
            ProductDemoPerformance.objects.update_or_create(
                company=company, product=product, period_start=period_start, period_end=period_end,
                defaults={
                    "units_sold": data["units"], "orders": data["orders"],
                    "revenue": decimal(data["revenue"]),
                    "scenario_label": "Cenário simulado de demonstração",
                },
            )
            specialization, _ = ProductSpecialization.objects.update_or_create(
                company=company, title=f"{data['name']} · exemplo demonstrativo",
                defaults={
                    "category": data["category"], "audience": data["audience"],
                    "differentiators": data["differentiators"], "limitations": data["limitations"],
                    "recommended_questions": data["questions"], "sales_guidance": data["guidance"],
                    "active": True,
                },
            )
            specialization.products.set([product])

    @staticmethod
    def _seed_sales_method(company):
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
