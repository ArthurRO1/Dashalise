"""HTTP API for the local demo. All querysets are scoped before serialization."""
import csv
import io
import calendar
import logging
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Alert, AssistantFeedback, AuditEvent, ChatMessage, Company, Conversation, Goal,
    PriorYearStoreSales, Product, ProductDemoPerformance, ProductSpecialization, Sale, SaleReflection, Team, TeamMembership,
)
from .assistant_service import generate_sales_guidance, is_contextual_follow_up, sales_answer
from .dates import default_reporting_period, latest_data_date
from .permissions import VALID_ROLES
from .serializers import AlertSerializer, SaleReflectionSerializer, SaleSerializer
from .services import dashboard_summary, refresh_smart_alerts, visible_sales

User = get_user_model()
logger = logging.getLogger(__name__)
DEMO_USERS = {
    "funcionario": "bianca.rocha@aurora.example",
    "supervisor": "patricia.lemos@aurora.example",
    "gerente": "diego.furtado@aurora.example",
    "administrador": "marcos.albuquerque@aurora.example",
}


def is_internal_data_request(question):
    """Route explicit dashboard lookups to deterministic calculations, not every sales topic."""
    normalized = " ".join(question.casefold().split())
    if any(phrase in normalized for phrase in (
        "dificuldade registrada", "desafio registrado", "anotação da venda",
        "anotacao da venda", "o que registrei na venda",
    )):
        return True

    words = set(re.findall(r"[a-záéíóúâêôãõç]+", normalized))
    coaching_intent = (
        "como melhorar", "melhorar", "melhor", "melhores", "aumentar", "estratégia", "estrategia", "como vender",
        "como conduzir", "como apresentar", "como abordar", "abordagem", "bater meta", "bater a meta",
        "atingir meta", "atingir a meta", "qual caminho", "devo", "deveria", "definir",
        "estabelecer", "o que fazer", "me ajude", "ajudar a", "dica", "técnica", "tecnica",
        "aprender", "treinar", "conselho", "sugestão", "sugestao",
    )
    hard_data_phrases = (
        "quanto falta", "quanto vendi", "quanto vendeu", "quanto recebo de comissão",
        "quanto recebo de comissao", "qual minha meta", "qual é minha meta", "qual a minha meta",
        "qual meu resultado", "qual é meu resultado", "qual foi o resultado", "qual minha comissão",
        "qual minha comissao", "quantos pedidos", "quantas vendas", "quais vendas",
        "minhas vendas neste mês", "minhas vendas neste mes", "me mostre meus indicadores",
        "produto mais vendido",
    )
    if any(phrase in normalized for phrase in hard_data_phrases):
        return True
    if any(phrase in normalized for phrase in coaching_intent):
        return False

    lookup_words = {
        "quanto", "quantos", "quantas", "qual", "quais", "mostre", "mostrar", "exibir",
        "consultar", "consulte", "alcancei", "atingi", "comparar", "compare", "ranking",
    }
    lookup_phrases = (
        "ver minhas", "veja minhas", "como está", "como esta", "falta para",
        "como estão", "como estao", "como vão", "como vao", "como ficaram",
        "qual foi", "qual tem sido", "me diga", "me informe", "quero saber",
    )
    metric_words = {
        "meta", "comissão", "comissao", "resultado", "desempenho", "faturamento",
        "ticket", "cancelamento", "cancelamentos", "pedido", "pedidos", "vendas", "vendi",
        "ritmo", "projeção", "projecao", "conversão", "conversao", "peças", "pecas", "atendimentos",
    }
    has_lookup = bool(words & lookup_words) or any(term in normalized for term in lookup_phrases)
    has_metric = bool(words & metric_words) or "ticket médio" in normalized or "ticket medio" in normalized
    if any(phrase in normalized for phrase in ("vendas da equipe", "resultado da equipe", "desempenho da equipe")):
        return has_lookup
    return has_lookup and has_metric


def demo_context(request):
    """Resolve the selected demo persona; never treat this as real authentication."""
    role = request.headers.get("X-Demo-Role", request.query_params.get("role", "funcionario"))
    if role not in VALID_ROLES:
        return None, None, None, Response({"detail": "Perfil de demonstração inválido."}, status=400)
    user = User.objects.filter(username=DEMO_USERS[role]).first()
    company = Company.objects.filter(name="Rede Aurora").first()
    if not user or not company:
        return None, None, None, Response(
            {"detail": "Dados de demonstração ainda não foram criados. Execute: python manage.py seed_demo"},
            status=503,
        )
    request.demo_role = role
    return role, user, company, None


def date_range(request):
    default_start, default_end = default_reporting_period()
    try:
        start = date.fromisoformat(request.query_params.get("start", default_start.isoformat()))
        end = date.fromisoformat(request.query_params.get("end", default_end.isoformat()))
    except ValueError:
        return None, None, Response({"detail": "Use datas ISO: AAAA-MM-DD."}, status=400)
    if start > end:
        return None, None, Response({"detail": "A data inicial deve ser anterior à final."}, status=400)
    return start, end, None


def requested_employee(request, role, user, company):
    """Permit a manager to drill into a member's personal view, within this company."""
    employee_id = request.query_params.get("employee_id") or request.data.get("employee_id")
    if not employee_id:
        return None, None
    if role not in {"gerente", "administrador"}:
        return None, Response({"detail": "Somente gerente ou administrador pode consultar outro perfil."}, status=403)
    try:
        employee_id = int(employee_id)
    except (TypeError, ValueError):
        return None, Response({"detail": "Identificador de funcionário inválido."}, status=400)
    membership = TeamMembership.objects.filter(
        user_id=employee_id,
        team__company=company,
        user__demo_identity__source_role="vendedor",
        user__demo_identity__active_at_demo=True,
    ).select_related("user", "team").first()
    if membership and role == "gerente" and membership.team.manager_id != user.id:
        membership = None
    if not membership:
        return None, Response({"detail": "Funcionário não encontrado nesta empresa."}, status=404)
    return membership.user, None


def health(request):
    return JsonResponse({"status": "ok", "service": "dashalise-sales-demo"})


@api_view(["GET"])
def dashboard(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    employee, error = requested_employee(request, role, user, company)
    if error:
        return error
    data_user = employee or user
    data_role = "funcionario" if employee else role
    start, end, error = date_range(request)
    if error:
        return error
    summary = dashboard_summary(data_user, data_role, company, start, end)
    summary = {key: str(value) if isinstance(value, Decimal) else value for key, value in summary.items()}
    sales = visible_sales(data_user, data_role, company, start, end).filter(status=Sale.Status.VALID)
    summary["role"] = role
    if employee:
        team = TeamMembership.objects.filter(user=employee, team__company=company).select_related("team").first()
        summary["employee"] = {"id": employee.id, "name": employee.get_full_name(), "team": team.team.name if team else ""}
    summary["period"] = {"start": start.isoformat(), "end": end.isoformat()}
    if role != "funcionario":
        scoped_team_ids = visible_sales(data_user, data_role, company, start, end).values("team_id").distinct()
        comparison_start = start - timedelta(days=364)
        comparison_end = end - timedelta(days=364)
        previous_revenue = PriorYearStoreSales.objects.filter(
            company=company,
            team_id__in=scoped_team_ids,
            sold_at__gte=comparison_start,
            sold_at__lte=comparison_end,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        current_revenue = Decimal(summary["revenue"])
        summary["previous_year"] = {
            "revenue": str(previous_revenue),
            "start": comparison_start.isoformat(),
            "end": comparison_end.isoformat(),
            "change_percent": round(float((current_revenue - previous_revenue) / previous_revenue * 100), 1) if previous_revenue else None,
        }
    summary["sales_by_day"] = list(
        sales.values("sold_at").annotate(amount=Sum("amount"), orders=Sum("sales_count")).order_by("sold_at")
    )
    summary["top_products"] = list(
        sales.filter(product__isnull=False).values("product__name").annotate(amount=Sum("amount"), orders=Sum("sales_count")).order_by("-amount")[:5]
    )
    summary["status_breakdown"] = list(
        visible_sales(data_user, data_role, company, start, end)
        .values("status")
        .annotate(count=Count("id"), amount=Sum("amount"))
        .order_by("status")
    )
    summary["cancellation_rate_percent"] = None
    summary["cancellation_data_available"] = False
    totals = sales.aggregate(pieces=Sum("pieces"), attendances=Sum("attendances"), records=Count("id"))
    pieces = totals["pieces"] or 0
    attendances = totals["attendances"] or 0
    summary["daily_records"] = totals["records"] or 0
    summary["pieces"] = pieces
    summary["attendances"] = attendances
    summary["conversion_rate_percent"] = round(summary["orders"] / attendances * 100, 1) if attendances else 0
    summary["pieces_per_sale"] = round(pieces / summary["orders"], 2) if summary["orders"] else 0
    summary["average_item_price"] = str(Decimal(summary["revenue"]) / pieces) if pieces else "0"
    summary["daily_average"] = str((Decimal(summary["revenue"]) / max(1, (end - start).days + 1)))
    if start.day == 1 and end == latest_data_date():
        month_days = calendar.monthrange(end.year, end.month)[1]
        summary["closing_projection"] = str(Decimal(summary["revenue"]) / max(1, end.day) * month_days)
        summary["daily_goal_pace"] = str(Decimal(summary["remaining"]) / max(1, month_days - end.day))
    else:
        summary["closing_projection"] = None
        summary["daily_goal_pace"] = None
    return Response(summary)


@api_view(["GET", "POST"])
def sales_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    employee, error = requested_employee(request, role, user, company)
    if error:
        return error
    data_user = employee or user
    data_role = "funcionario" if employee else role
    start, end, error = date_range(request)
    if error:
        return error
    if request.method == "GET":
        rows = visible_sales(data_user, data_role, company, start, end).prefetch_related("reflections__seller", "reflections__actor")
        return Response(SaleSerializer(rows[:100], many=True).data)
    if role not in {"gerente", "administrador"}:
        return Response({"detail": "Este perfil não pode cadastrar vendas."}, status=403)
    seller_id = request.data.get("seller")
    team_id = request.data.get("team")
    product_id = request.data.get("product")
    if not TeamMembership.objects.filter(
        team_id=team_id, team__company=company, user_id=seller_id
    ).exists():
        return Response({"detail": "O vendedor precisa pertencer à equipe selecionada da empresa."}, status=400)
    if not Product.objects.filter(id=product_id, company=company, active=True).exists():
        return Response({"detail": "Produto não encontrado nesta empresa."}, status=400)
    serializer = SaleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    sale = serializer.save(company=company)
    AuditEvent.objects.create(
        company=company, actor=user, action="sale.created", object_type="Sale", object_id=str(sale.pk)
    )
    return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def sale_reflection_create(request, sale_id):
    role, user, company, error = demo_context(request)
    if error:
        return error
    sale = visible_sales(user, role, company).filter(id=sale_id).first()
    if not sale:
        return Response({"detail": "Venda não encontrada no escopo deste perfil."}, status=404)
    stage = str(request.data.get("stage", "")).strip()
    challenge = str(request.data.get("challenge", "")).strip()
    if stage not in dict(SaleReflection.STAGES):
        return Response({"detail": "Selecione uma etapa válida da venda."}, status=400)
    if not challenge or len(challenge) > 500:
        return Response({"detail": "Descreva a dificuldade em até 500 caracteres."}, status=400)
    reflection = SaleReflection.objects.create(
        company=company, sale=sale, seller=sale.seller, actor=user, stage=stage, challenge=challenge,
    )
    AuditEvent.objects.create(
        company=company, actor=user, action="sale.reflection_created", object_type="SaleReflection",
        object_id=str(reflection.id), metadata={"sale_id": sale.id, "seller_id": sale.seller_id, "stage": stage},
    )
    return Response(SaleReflectionSerializer(reflection).data, status=201)


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def import_sales_csv(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    if role not in {"gerente", "administrador"}:
        return Response({"detail": "Este perfil não pode importar vendas."}, status=403)
    uploaded = request.FILES.get("file")
    if not uploaded or not uploaded.name.lower().endswith(".csv"):
        return Response({"detail": "Envie um arquivo CSV no campo 'file'."}, status=400)
    if uploaded.size > 2_000_000:
        return Response({"detail": "O limite para a demonstração é 2 MB."}, status=400)
    try:
        text = uploaded.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"external_id", "seller_email", "team", "product_sku", "amount", "sold_at"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            return Response({"detail": "Colunas obrigatórias: " + ", ".join(sorted(required))}, status=400)
        rows = list(reader)
        if len(rows) > 5000:
            return Response({"detail": "O limite por importação é 5.000 linhas."}, status=400)
    except (UnicodeDecodeError, csv.Error):
        return Response({"detail": "Não foi possível ler o CSV UTF-8."}, status=400)

    created = 0
    errors = []
    with transaction.atomic():
        for line, row in enumerate(rows, start=2):
            try:
                external_id = row["external_id"].strip()
                if not external_id:
                    raise ValueError("external_id não pode ficar vazio")
                seller = User.objects.get(username=row["seller_email"].strip().lower())
                team = Team.objects.get(company=company, name=row["team"].strip())
                product = Product.objects.get(company=company, sku=row["product_sku"].strip())
                if not TeamMembership.objects.filter(team=team, user=seller).exists():
                    raise ValueError("vendedor não pertence à equipe indicada")
                amount = Decimal(row["amount"].replace(",", "."))
                sold_at = date.fromisoformat(row["sold_at"].strip())
                if amount <= 0:
                    raise ValueError("valor deve ser positivo")
                _, was_created = Sale.objects.get_or_create(
                    company=company,
                    external_id=external_id,
                    defaults={
                        "seller": seller, "team": team, "product": product,
                        "customer_name": row.get("customer_name", "").strip(),
                        "amount": amount, "sold_at": sold_at,
                    },
                )
                created += int(was_created)
            except (User.DoesNotExist, Team.DoesNotExist, Product.DoesNotExist, ValueError, InvalidOperation) as exc:
                errors.append({"line": line, "error": str(exc) or "registro inválido"})
                if len(errors) >= 25:
                    break
    AuditEvent.objects.create(
        company=company, actor=user, action="sales.csv_imported", metadata={"created": created, "errors": len(errors)}
    )
    return Response({"created": created, "errors": errors, "error_count": len(errors)})


@api_view(["GET"])
def teams_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    teams = Team.objects.filter(company=company)
    if role == "funcionario":
        teams = teams.filter(memberships__user=user)
    elif role == "supervisor":
        teams = teams.filter(supervisor=user)
    elif role == "gerente":
        teams = teams.filter(manager=user)
    result = []
    for team in teams.distinct():
        members = TeamMembership.objects.filter(
            team=team,
            user__demo_identity__active_at_demo=True,
        ).select_related("user")
        if role == "funcionario":
            members = members.filter(user=user)
        result.append({
            "id": team.id,
            "name": team.name,
            "external_id": team.external_id,
            "city": team.city,
            "state": team.state,
            "region": team.region_name,
            "franchisee": team.franchisee,
            "store_type": team.store_type,
            "manager": team.manager.get_full_name() if team.manager else None,
            "supervisor": team.supervisor.get_full_name() if team.supervisor else None,
            "members": [{"id": m.user_id, "name": m.user.get_full_name()} for m in members],
        })
    return Response(result)


@api_view(["GET"])
def people_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    if role not in {"gerente", "administrador"}:
        return Response({"detail": "A lista de desempenho individual está disponível para gerente e administrador."}, status=403)
    month_start, month_end = default_reporting_period()
    members = TeamMembership.objects.filter(
        team__company=company,
        user__demo_identity__source_role="vendedor",
        user__demo_identity__active_at_demo=True,
    ).select_related("user", "team").order_by("user__first_name", "user__last_name")
    if role == "gerente":
        members = members.filter(team__manager=user)
    sales_by_user = {}
    scoped_sales = visible_sales(user, role, company, month_start, month_end).select_related("seller")
    for sale in scoped_sales:
        row = sales_by_user.setdefault(sale.seller_id, {"revenue": Decimal("0"), "commission": Decimal("0"), "orders": 0, "attendances": 0, "cancelled": 0})
        if sale.status == Sale.Status.VALID:
            row["revenue"] += sale.amount
            row["commission"] += sale.commission_amount
            row["orders"] += sale.sales_count
            row["attendances"] += sale.attendances
        elif sale.status == Sale.Status.CANCELLED:
            row["cancelled"] += 1
    results = []
    seen = set()
    for membership in members:
        person = membership.user
        if person.id in seen:
            continue
        seen.add(person.id)
        goal = Goal.objects.filter(company=company, scope=Goal.Scope.USER, user=person, period_start__lte=month_end, period_end__gte=month_start).first()
        stats = sales_by_user.get(person.id, {})
        revenue = stats.get("revenue", Decimal("0"))
        target = goal.target_amount if goal else Decimal("0")
        if target and revenue >= target:
            stats["commission"] = stats.get("commission", Decimal("0")) + Decimal("300")
        sales_count = stats.get("orders", 0)
        attendances = stats.get("attendances", 0)
        results.append({
            "id": person.id,
            "name": person.get_full_name(),
            "team": membership.team.name,
            "revenue": str(revenue),
            "goal": str(target),
            "goal_progress_percent": round(float(revenue / target * 100), 1) if target else 0,
            "commission": str(stats.get("commission", Decimal("0"))),
            "orders": stats.get("orders", 0),
            "attendances": attendances,
            "conversion_rate_percent": round(sales_count / attendances * 100, 1) if attendances else 0,
            "cancelled": stats.get("cancelled", 0),
        })
    results.sort(key=lambda item: (-item["goal_progress_percent"], -float(item["revenue"]), item["name"]))
    return Response(results)


@api_view(["GET", "POST"])
def products_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    if request.method == "POST":
        if role not in {"gerente", "administrador"}:
            return Response({"detail": "Somente a gerência pode organizar os produtos da empresa."}, status=403)
        name = str(request.data.get("name", "")).strip()
        sku = str(request.data.get("sku", "")).strip()
        if not name or not sku:
            return Response({"detail": "Informe nome e código/SKU do produto."}, status=400)
        product, created = Product.objects.get_or_create(
            company=company,
            sku=sku,
            defaults={
                "name": name,
                "category": str(request.data.get("category", "")).strip(),
                "description": str(request.data.get("description", "")).strip(),
            },
        )
        if not created:
            return Response({"detail": "Já existe um produto com esse código."}, status=409)
        AuditEvent.objects.create(company=company, actor=user, action="product.created", object_type="Product", object_id=str(product.id))
        return Response({"id": product.id, "sku": product.sku, "name": product.name, "category": product.category}, status=201)

    employee, error = requested_employee(request, role, user, company)
    if error:
        return error
    data_user = employee or user
    data_role = "funcionario" if employee else role
    products = Product.objects.filter(company=company, active=True)
    sales = visible_sales(data_user, data_role, company).filter(status=Sale.Status.VALID)
    rows = []
    demo_period_start, demo_period_end = default_reporting_period()
    for product in products:
        aggregate = sales.filter(product=product).aggregate(amount=Sum("amount"), orders=Sum("sales_count"))
        demo = ProductDemoPerformance.objects.filter(
            company=company, product=product,
            period_start__lte=demo_period_end, period_end__gte=demo_period_start,
        ).first()
        rows.append({
            "id": product.id, "sku": product.sku, "name": product.name,
            "category": product.category, "description": product.description,
            "amount": aggregate["amount"] or 0, "orders": aggregate["orders"] or 0,
            "real_performance_available": bool(aggregate["orders"]),
            "demo_performance": ({
                "period_start": demo.period_start.isoformat(), "period_end": demo.period_end.isoformat(),
                "revenue": str(demo.revenue), "orders": demo.orders, "units_sold": demo.units_sold,
                "scenario_label": demo.scenario_label,
            } if demo else None),
        })
    return Response(rows)


@api_view(["GET"])
def alerts_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    employee, error = requested_employee(request, role, user, company)
    if error:
        return error
    data_user = employee or user
    data_role = "funcionario" if employee else role
    refresh_smart_alerts(data_user, data_role, company)
    alerts = Alert.objects.filter(company=company)
    if employee:
        alerts = alerts.filter(Q(user=employee) | Q(team__memberships__user=employee, user__isnull=True)).distinct()
    if role == "funcionario":
        alerts = alerts.filter(Q(user=user) | Q(team__memberships__user=user, user__isnull=True)).distinct()
    elif role == "supervisor":
        alerts = alerts.filter(Q(user=user) | Q(team__supervisor=user) | Q(team__memberships__user=user)).distinct()
    elif role == "gerente" and not employee:
        alerts = alerts.filter(Q(user=user) | Q(team__manager=user)).distinct()
    return Response(AlertSerializer(alerts[:100], many=True).data)


@api_view(["POST"])
def mark_alert_read(request, alert_id):
    role, user, company, error = demo_context(request)
    if error:
        return error
    alert = Alert.objects.filter(company=company, id=alert_id)
    if role == "funcionario":
        alert = alert.filter(Q(user=user) | Q(team__memberships__user=user, user__isnull=True)).distinct()
    elif role == "supervisor":
        alert = alert.filter(Q(user=user) | Q(team__supervisor=user) | Q(team__memberships__user=user)).distinct()
    elif role == "gerente":
        alert = alert.filter(Q(user=user) | Q(team__manager=user)).distinct()
    item = alert.first()
    if not item:
        return Response({"detail": "Alerta não encontrado."}, status=404)
    item.read_at = timezone.now()
    item.save(update_fields=["read_at"])
    return Response(AlertSerializer(item).data)


@api_view(["POST"])
def assistant_legacy(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    question = str(request.data.get("question", "")).strip()
    if not question:
        return Response({"detail": "Informe uma pergunta."}, status=400)
    if len(question) > 1000:
        return Response({"detail": "A pergunta deve ter até 1.000 caracteres."}, status=400)
    start, end, error = date_range(request)
    if error:
        return error
    metrics = dashboard_summary(user, role, company, start, end)
    lower = question.casefold()
    if any(word in lower for word in ("meta", "falta", "atingir")):
        answer = (
            f"Você vendeu R$ {metrics['revenue']:,.2f} de uma meta de R$ {metrics['goal']:,.2f}. "
            f"Faltam R$ {metrics['remaining']:,.2f}.".replace(",", "X").replace(".", ",").replace("X", ".")
        )
    elif "comiss" in lower:
        answer = f"A comissão acumulada calculada sobre vendas válidas é R$ {metrics['commission']:,.2f}."
    elif any(word in lower for word in ("produto", "ranking")):
        top = (
            visible_sales(user, role, company, start, end)
            .filter(status=Sale.Status.VALID, product__isnull=False)
            .values("product__name")
            .annotate(amount=Sum("amount"))
            .order_by("-amount")
            .first()
        )
        if top:
            answer = f"Entre os produtos vinculados às vendas deste período, o maior faturamento é de {top['product__name']} (R$ {top['amount']})."
        else:
            demo_top = ProductDemoPerformance.objects.filter(
                company=company, period_start__lte=end, period_end__gte=start,
            ).select_related("product").order_by("-revenue").first()
            answer = (
                f"No cenário simulado de demonstração, {demo_top.product.name} lidera a receita com R$ {demo_top.revenue}. "
                "Esse exemplo é fictício e não representa resultados dos funcionários."
                if demo_top else
                "Ainda não há vendas vinculadas a produtos neste período. Posso consultar o catálogo e as características cadastradas."
            )
    elif any(word in lower for word in ("conversão", "conversao")):
        answer = f"A conversão no período é {metrics['conversion_rate_percent']}%: {metrics['orders']} vendas divididas por {metrics['attendances']} atendimentos."
    elif any(word in lower for word in ("peças", "pecas", "p.a.", "preço médio", "preco medio")):
        answer = f"No período houve {metrics['pieces']} peças em {metrics['orders']} vendas ({metrics['pieces_per_sale']} peças por venda). O preço médio por peça foi R$ {metrics['average_item_price']:,.2f}."
    elif any(word in lower for word in ("equipe", "vendedor")) and role == "funcionario":
        answer = "Este perfil de demonstração consulta apenas as próprias vendas. Posso ajudar com sua meta, comissão e produtos."
    else:
        answer = f"No período consultado há {metrics['orders']} pedidos válidos e R$ {metrics['revenue']} em vendas. Experimente perguntar sobre meta, comissão ou produtos."
    AuditEvent.objects.create(company=company, actor=user, action="assistant.queried", metadata={"role": role})
    return Response({"answer": answer, "source": "business_rules", "demo": True})


def _assistant_performance_evidence(user, role, company, start, end, question, *, selected_employee=False):
    """Attach exact dashboard figures when a question asks about results or coaching."""
    normalized = question.casefold()
    question_tokens = set(re.findall(r"[a-záéíóúâêôãõç]+", normalized))
    coaching_terms = (
        "melhorar minha conversão", "melhorar minha conversao", "melhorar meu resultado",
        "melhorar meu desempenho", "treinar", "treinamento", "acompanhar meu desempenho",
        "onde estou abaixo", "meu ponto fraco", "minha conversão", "minha conversao",
        "o que sugere", "sugere que eu", "o que devo fazer", "devo fazer", "o que eu faço",
        "o que faço", "que recomenda", "recomenda", "pior até agora", "pior ate agora",
        "precisa melhorar", "precisa de ajuda", "como acompanhar",
    )
    personal_scope = role == "funcionario" or selected_employee
    team_terms = (
        "quem vendeu menos", "vendeu menos", "venderam menos", "menos vendeu", "menos vendido", "menor venda", "menores vendas",
        "menor faturamento", "menores faturamentos", "menor receita", "menores receitas", "vendas mais baixas", "abaixo da meta",
        "menor conversão", "menor conversao", "precisa de acompanhamento", "diferença entre vendedores",
        "diferenças entre vendedores", "diferenca entre vendedores", "diferencas entre vendedores", "compare os vendedores",
    )
    scoped_teams = Team.objects.none()
    mentioned_sellers = set()
    if role in {"gerente", "supervisor", "administrador"} and not selected_employee:
        if role == "gerente":
            scoped_teams = Team.objects.filter(company=company, manager=user)
        elif role == "supervisor":
            scoped_teams = Team.objects.filter(company=company, supervisor=user)
            if not scoped_teams.exists():
                scoped_teams = Team.objects.filter(company=company, memberships__user=user)
        else:
            scoped_teams = Team.objects.filter(company=company)
        seller_names = TeamMembership.objects.filter(
            team__in=scoped_teams, user__demo_identity__source_role="vendedor",
            user__demo_identity__active_at_demo=True,
        ).values_list("user__first_name", flat=True).distinct()
        mentioned_sellers = {name.casefold() for name in seller_names if name.casefold() in question_tokens}
    team_question = (
        role in {"gerente", "supervisor", "administrador"} and not selected_employee
        and (any(term in normalized for term in team_terms) or len(mentioned_sellers) > 1)
    )
    if not is_internal_data_request(question) and not (personal_scope and any(term in normalized for term in coaching_terms)) and not team_question:
        return None

    metrics = dashboard_summary(user, "funcionario" if personal_scope else role, company, start, end)
    money_value = lambda value: f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    period_label = f"{start:%d/%m/%Y} a {end:%d/%m/%Y}"
    items = [
        {"label": "Vendido", "value": money_value(metrics["revenue"])},
        {"label": "Meta", "value": money_value(metrics["goal"]), "detail": f"{metrics['goal_progress_percent']:.1f}% atingida"},
        {"label": "Falta para a meta", "value": money_value(metrics["remaining"])},
        {"label": "Vendas", "value": str(metrics["orders"])},
        {"label": "Atendimentos", "value": str(metrics["attendances"])},
        {"label": "Conversão", "value": f"{metrics['conversion_rate_percent']:.1f}%", "detail": "vendas ÷ atendimentos"},
    ]
    store_conversion = None
    if personal_scope:
        membership = TeamMembership.objects.filter(
            user=user, team__company=company,
        ).select_related("team").first()
        if membership:
            team_totals = Sale.objects.filter(
                company=company, team=membership.team, status=Sale.Status.VALID,
                sold_at__gte=start, sold_at__lte=end,
            ).aggregate(orders=Sum("sales_count"), attendances=Sum("attendances"))
            team_orders = team_totals["orders"] or 0
            team_attendances = team_totals["attendances"] or 0
            team_conversion = team_orders / team_attendances * 100 if team_attendances else 0
            store_conversion = team_conversion
            difference = metrics["conversion_rate_percent"] - team_conversion
            items.append({
                "label": "Conversão agregada da loja",
                "value": f"{team_conversion:.1f}%",
                "detail": f"diferença do perfil: {difference:+.1f} p.p.",
            })
            if metrics["goal"] and metrics["goal_progress_percent"] < 100 and difference < 0:
                signal = (
                    f"Sinal descritivo para investigar: atingimento em {metrics['goal_progress_percent']:.1f}% e conversão "
                    f"{abs(difference):.1f} p.p. abaixo da conversão agregada da loja. Isso não identifica a causa; "
                    "confirme escala, fluxo, estoque, tipo de atendimento e contexto com a pessoa."
                )
            else:
                signal = "Os indicadores não mostram simultaneamente meta abaixo de 100% e conversão abaixo da loja. Isso não substitui uma conversa sobre contexto e necessidades de desenvolvimento."
        else:
            signal = "Não há loja associada suficiente para comparar o resultado com a equipe."
    else:
        signal = "Os valores são agregados para o escopo deste perfil; use a equipe para localizar recortes individuais."
    evidence = {
        "title": "Dados do período usados nesta resposta",
        "period": period_label,
        "items": items,
        "signal": signal,
        "scope": "individual e comparação com loja" if personal_scope else "agregado do perfil",
        "facts": {
            "revenue": str(metrics["revenue"]),
            "goal": str(metrics["goal"]),
            "goal_progress_percent": metrics["goal_progress_percent"],
            "remaining": str(metrics["remaining"]),
            "orders": metrics["orders"],
            "attendances": metrics["attendances"],
            "conversion_rate_percent": metrics["conversion_rate_percent"],
            "store_conversion_rate_percent": store_conversion,
        },
    }
    if team_question:
        team_ids = scoped_teams.values_list("id", flat=True)
        memberships = TeamMembership.objects.filter(
            team_id__in=team_ids,
            user__demo_identity__source_role="vendedor",
            user__demo_identity__active_at_demo=True,
        ).select_related("user", "team").order_by("team__name", "user__first_name", "user__last_name")
        member_ids = memberships.values_list("user_id", flat=True)
        sales_by_person = {
            row["seller_id"]: row for row in Sale.objects.filter(
                company=company, team_id__in=team_ids, seller_id__in=member_ids,
                status=Sale.Status.VALID, sold_at__gte=start, sold_at__lte=end,
            ).values("seller_id").annotate(
                revenue=Sum("amount"), orders=Sum("sales_count"), attendances=Sum("attendances"),
            )
        }
        goals_by_person = {
            row["user_id"]: row["target_amount"] for row in Goal.objects.filter(
                company=company, scope=Goal.Scope.USER, user_id__in=member_ids,
                period_start__lte=end, period_end__gte=start,
            ).values("user_id", "target_amount")
        }
        people = []
        visited = set()
        for membership in memberships:
            person = membership.user
            if person.id in visited:
                continue
            visited.add(person.id)
            stats = sales_by_person.get(person.id, {})
            revenue = stats.get("revenue") or Decimal("0")
            orders = stats.get("orders") or 0
            attendances = stats.get("attendances") or 0
            goal = goals_by_person.get(person.id) or Decimal("0")
            people.append({
                "id": person.id,
                "name": person.get_full_name(),
                "team": membership.team.name,
                "revenue": money_value(revenue),
                "goal_progress": f"{revenue / goal * 100:.1f}%" if goal else "Sem meta",
                "orders": orders,
                "attendances": attendances,
                "conversion": f"{orders / attendances * 100:.1f}%" if attendances else "Sem atendimentos",
            })
        mentioned_seller_ids = {
            person.id for person in memberships if person.user.first_name.casefold() in mentioned_sellers
        }
        if len(mentioned_seller_ids) > 1:
            people = [person for person in people if person["id"] in mentioned_seller_ids]
        people.sort(key=lambda row: (sales_by_person.get(row["id"], {}).get("revenue") or Decimal("0"), row["name"]))
        evidence["people"] = people[:3]
        evidence["people_title"] = "Comparação das pessoas mencionadas" if len(mentioned_seller_ids) > 1 else "Menores faturamentos no escopo deste perfil"
        evidence["signal"] = "O recorte identifica diferenças de faturamento no período. Diferença de resultado é um ponto para conversar e investigar, não prova de falha; confirme escala, fluxo, estoque e contexto antes de decidir um treinamento."
    return evidence


def _product_performance_evidence(user, role, company, start, end, question):
    normalized = question.casefold()
    sales_terms = (
        "ranking", "mais vendido", "menos vendido", "mais vendeu", "vendeu mais", "quanto vendeu",
        "quantas vendas", "unidades vendidas", "unidades", "faturamento", "receita",
    )
    demo_names = ProductDemoPerformance.objects.filter(company=company).values_list("product__name", flat=True)
    mentions_product = any(term in normalized for term in ("produto", "produtos")) or any(
        name.casefold() in normalized for name in demo_names
    )
    if not mentions_product or not any(term in normalized for term in sales_terms):
        return None

    actual_sales = visible_sales(user, role, company, start, end).filter(
        status=Sale.Status.VALID, product__isnull=False,
    ).values("product__name").annotate(
        revenue=Sum("amount"), orders=Sum("sales_count"), units=Sum("pieces"),
    ).order_by("-revenue")
    actual_rows = list(actual_sales)
    if actual_rows:
        return {
            "title": "Vendas vinculadas a produtos",
            "period": f"{start:%d/%m/%Y} a {end:%d/%m/%Y}",
            "items": [{
                "label": row["product__name"],
                "value": f"R$ {row['revenue']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "detail": f"{row['orders']} vendas · {row['units']} unidades",
            } for row in actual_rows[:4]],
            "signal": "Indicadores calculados a partir das vendas vinculadas aos produtos no período.",
            "scope": "vendas vinculadas do perfil",
        }

    demo_rows = list(ProductDemoPerformance.objects.filter(
        company=company,
        period_start__lte=end,
        period_end__gte=start,
    ).select_related("product").order_by("-revenue"))
    if not demo_rows:
        return None
    return {
        "title": "Cenário simulado de produtos",
        "period": f"{demo_rows[0].period_start:%d/%m/%Y} a {demo_rows[0].period_end:%d/%m/%Y}",
        "items": [{
            "label": row.product.name,
            "value": f"R$ {row.revenue:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "detail": f"{row.orders} vendas · {row.units_sold} unidades",
        } for row in demo_rows[:4]],
        "signal": "Estes valores são fictícios e servem apenas para demonstrar a análise de produtos. Não entram nos indicadores, metas ou comissões dos funcionários.",
        "scope": "simulação demonstrativa da empresa",
    }


def _is_performance_coaching_request(question, employee):
    """Detect advice about an employee's results, keeping ordinary sales questions separate."""
    if not employee:
        return False
    normalized = question.casefold()
    asks_for_action = any(term in normalized for term in (
        "o que sugere", "sugere que eu", "o que devo fazer", "devo fazer", "o que eu faço",
        "o que faço", "que recomenda", "recomenda", "como acompanhar", "como ajudar",
        "como desenvolver", "como treinar", "precisa de ajuda",
    ))
    performance_context = any(term in normalized for term in (
        "pior", "abaixo", "meta", "conversão", "conversao", "desempenho", "resultado",
        "faturamento", "vendas", "vendeu", "atendimentos", "precisa melhorar",
    ))
    return asks_for_action and performance_context


def _performance_coaching_answer(employee, evidence):
    facts = evidence["facts"]

    def brl(value):
        return f"R$ {Decimal(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    progress = float(facts["goal_progress_percent"])
    conversion = float(facts["conversion_rate_percent"])
    store_conversion = facts.get("store_conversion_rate_percent")
    if store_conversion is not None:
        store_conversion = float(store_conversion)
    response = (
        f"Eu não chamaria {employee.first_name} de ‘pior’: os dados permitem comparar resultados, mas não explicam a causa. "
        f"Em {evidence['period']}, {employee.first_name} vendeu {brl(facts['revenue'])} ({progress:.1f}% da meta), "
        f"com conversão de {conversion:.1f}% — {facts['orders']} vendas em {facts['attendances']} atendimentos."
    )
    if store_conversion is not None:
        difference = conversion - store_conversion
        response += f" A conversão agregada da loja foi {store_conversion:.1f}% ({difference:+.1f} p.p. para o Lucas)."
    response += (
        "\n\nSugiro uma conversa individual e objetiva:\n"
        "1. Apresente esses números como ponto de partida, sem comparar ou rotular a pessoa.\n"
        "2. Pergunte o que aconteceu nos atendimentos: fluxo, escala, disponibilidade de produtos, perfil das demandas e onde ele sentiu dificuldade.\n"
        "3. Escolham juntos uma habilidade para praticar. Se a conversão for a prioridade, treinem perguntas abertas para descobrir a necessidade antes de recomendar; os dados atuais não provam que essa seja a causa.\n"
        "4. Combinem um acompanhamento curto e revisem vendas, atendimentos e conversão em um período comparável."
        f"\n\nUma forma de começar: ‘{employee.first_name}, quero olhar seus números de outubro com você para entender o contexto e decidir como posso apoiar. O que mais dificultou seus atendimentos?’ "
        f"Você também pode abrir o painel de {employee.first_name} para consultar os indicadores e os resumos diários."
    )
    return response


@api_view(["POST"])
def assistant(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    question = str(request.data.get("question", "")).strip()
    if not question:
        return Response({"detail": "Informe uma pergunta."}, status=400)
    if len(question) > 1000:
        return Response({"detail": "A pergunta deve ter até 1.000 caracteres."}, status=400)
    employee, error = requested_employee(request, role, user, company)
    if error:
        return error
    # Let managers ask naturally about a uniquely named seller; the match stays inside their company.
    if not employee and role in {"gerente", "administrador"}:
        tokens = set(question.casefold().replace("?", " ").replace(",", " ").split())
        candidates = []
        seen_people = set()
        members = TeamMembership.objects.filter(
            team__company=company,
            user__demo_identity__source_role="vendedor",
            user__demo_identity__active_at_demo=True,
        ).select_related("user", "team")
        if role == "gerente":
            members = members.filter(team__manager=user)
        for membership in members:
            person = membership.user
            if person.pk in seen_people:
                continue
            seen_people.add(person.pk)
            first = person.first_name.casefold()
            full = person.get_full_name().casefold()
            if full and full in question.casefold() or first and first in tokens:
                candidates.append(person)
        if len(candidates) == 1:
            employee = candidates[0]
    start, end, error = date_range(request)
    if error:
        return error

    stage = request.data.get("stage", Conversation.Stage.GENERAL)
    if stage not in Conversation.Stage.values:
        return Response({"detail": "Etapa de venda inválida."}, status=400)
    sale = None
    sale_id = request.data.get("sale_id")
    if sale_id:
        sale = visible_sales(user, role, company).filter(id=sale_id).first()
        if not sale:
            return Response({"detail": "Venda não encontrada para este perfil."}, status=404)

    conversation = None
    previous_history = []
    conversation_id = request.data.get("conversation_id")
    if conversation_id:
        conversation = Conversation.objects.filter(id=conversation_id, company=company, user=user).first()
        if not conversation:
            return Response({"detail": "Conversa não encontrada neste perfil."}, status=404)
        previous_history = list(
            conversation.messages.order_by("-created_at").values("role", "content")[:6]
        )[::-1]
        if any(item["role"] == ChatMessage.Role.USER for item in previous_history):
            if is_contextual_follow_up(question, previous_history):
                sale = conversation.sale or sale
                stage = conversation.stage
            else:
                # A new subject starts with a clean context; the conversation can span topics.
                sale = None
                stage = Conversation.Stage.GENERAL
                conversation.sale = None
                conversation.stage = stage
                conversation.title = (question[:70] + "…") if len(question) > 70 else question
                conversation.save(update_fields=["sale", "stage", "title", "updated_at"])
    else:
        conversation = Conversation.objects.create(
            company=company,
            user=user,
            sale=sale,
            stage=stage,
            title=(question[:70] + "…") if len(question) > 70 else question,
        )

    if employee and sale and sale.seller_id != employee.id:
        sale = None

    user_message = ChatMessage.objects.create(conversation=conversation, role=ChatMessage.Role.USER, content=question)
    sources = []
    target_role = "funcionario" if employee else role
    evidence = _product_performance_evidence(
        employee or user, target_role, company, start, end, question,
    ) or _assistant_performance_evidence(
        employee or user, target_role, company, start, end, question,
        selected_employee=bool(employee),
    )
    is_product_performance_query = bool(evidence and evidence.get("title") in {
        "Cenário simulado de produtos", "Vendas vinculadas a produtos",
    })
    is_metric_or_record_query = is_internal_data_request(question) or is_product_performance_query
    team_ranking = bool(evidence and evidence.get("people"))
    performance_action = _is_performance_coaching_request(question, employee)
    generated = None
    if not is_metric_or_record_query and not team_ranking and not performance_action and settings.GEMINI_API_KEY:
        try:
            generated = generate_sales_guidance(
                company, question, stage, sale=sale, user=employee or user, role=target_role,
                history=previous_history,
                performance_context=evidence,
            )
        except Exception as error:
            logger.exception("Falha ao gerar resposta Gemini com busca web automática.")
            return Response({
                "detail": (
                    f"O Gemini não conseguiu responder com a busca web automática ({type(error).__name__}). "
                    "Confira o terminal do Django para ver o erro."
                )
            }, status=502)

    if performance_action and evidence:
        answer = _performance_coaching_answer(employee, evidence)
        source_label = "indicadores internos + orientação de acompanhamento"
    elif team_ranking:
        lines = [
            f"{index}. {person['name']} ({person['team']}): {person['revenue']} em vendas, "
            f"{('sem meta individual cadastrada' if person['goal_progress'] == 'Sem meta' else person['goal_progress'] + ' da meta')}, {person['conversion']} de conversão "
            f"({person['orders']} vendas / {person['attendances']} atendimentos)."
            for index, person in enumerate(evidence["people"], start=1)
        ]
        if len(evidence["people"]) > 1 and evidence["people_title"] == "Comparação das pessoas mencionadas":
            intro = f"Comparando as pessoas mencionadas no período de {evidence['period']}:\n"
        else:
            intro = f"Estes são os menores faturamentos no período de {evidence['period']}:\n"
        answer = intro + "\n".join(lines) + "\nUse a diferença como ponto de investigação, não como diagnóstico de falha."
        source_label = "dados internos agregados por vendedor e dia"
    elif generated:
        answer = generated["answer"]
        sources = generated["sources"]
        source_label = "Gemini com busca automática e base comercial"
    else:
        answer, sources, source_label = sales_answer(
            employee or user, target_role, company, question, stage,
            sale=sale, about_another=bool(employee),
        )

    assistant_message = ChatMessage.objects.create(
        conversation=conversation,
        role=ChatMessage.Role.ASSISTANT,
        content=answer,
        sources=sources,
        evidence=evidence or {},
        used_web_search=bool(generated),
    )
    conversation.save(update_fields=["updated_at"])
    AuditEvent.objects.create(company=company, actor=user, action="assistant.queried", metadata={"role": role, "web": bool(generated)})
    normalized_question = question.casefold()
    links = []
    if any(word in normalized_question for word in ("meta", "falta", "atingir", "comiss")):
        links.append({"label": "Abrir minhas metas", "page": "metas"})
    if any(word in normalized_question for word in ("produto", "plano", "catálogo")):
        links.append({"label": "Ver produtos", "page": "produtos"})
    if any(word in normalized_question for word in ("equipe", "vendedor", "supervisor")):
        links.append({"label": "Abrir equipe", "page": "equipe"})
    if any(word in normalized_question for word in ("cliente", "apressado", "pressa", "abordagem", "objeção", "objecao")):
        links.append({"label": "Abrir método de venda", "page": "treinamento"})
    if sale:
        links.append({"label": f"Abrir venda #{sale.id}", "page": "vendas", "sale_id": sale.id})
    if employee:
        links.append({"label": f"Ver desempenho de {employee.first_name}", "page": "indicadores", "employee_id": employee.id})
    elif evidence:
        links.append({"label": "Abrir painel de indicadores", "page": "indicadores"})
    if team_ranking:
        for person in evidence["people"]:
            links.append({"label": f"Ver painel de {person['name']}", "page": "indicadores", "employee_id": person["id"]})
    assistant_message = conversation.messages.filter(role=ChatMessage.Role.ASSISTANT).last()
    assistant_message.internal_links = links
    assistant_message.source_label = source_label
    assistant_message.save(update_fields=["internal_links", "source_label", "evidence"])
    return Response({
        "answer": answer,
        "source": source_label,
        "sources": sources,
        "used_web_search": bool(generated),
        "conversation_id": conversation.id,
        "sale_id": sale.id if sale else None,
        "message_id": assistant_message.id,
        "stage": stage,
        "links": links,
        "evidence": evidence,
        "demo": True,
    })


@api_view(["GET"])
def assistant_status(request):
    return Response({
        "web_search_enabled": bool(settings.GEMINI_API_KEY),
        "provider": "Gemini Google Search grounding" if settings.GEMINI_API_KEY else None,
        "demo_mode": True,
    })


@api_view(["GET", "POST"])
def conversations_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    if request.method == "GET":
        chats = Conversation.objects.filter(company=company, user=user).select_related("sale", "sale__product")[:100]
        return Response([
            {
                "id": chat.id,
                "title": chat.title,
                "sale_id": chat.sale_id,
                "sale_label": f"Resumo diário · {chat.sale.sold_at:%d/%m/%Y}" if chat.sale else "Conversa geral",
                "stage": chat.stage,
                "stage_label": chat.get_stage_display(),
                "updated_at": chat.updated_at,
            }
            for chat in chats
        ])

    stage = request.data.get("stage", Conversation.Stage.GENERAL)
    sale_id = request.data.get("sale_id")
    if stage not in Conversation.Stage.values:
        return Response({"detail": "Etapa de venda inválida."}, status=400)
    sale = None
    if sale_id:
        sale = visible_sales(user, role, company).filter(id=sale_id).first()
        if not sale:
            return Response({"detail": "Venda não encontrada para este perfil."}, status=404)
    title = str(request.data.get("title", "")).strip() or "Nova conversa"
    chat = Conversation.objects.create(company=company, user=user, sale=sale, stage=stage, title=title[:180])
    return Response({"id": chat.id, "title": chat.title, "sale_id": chat.sale_id, "stage": chat.stage}, status=201)


@api_view(["GET"])
def conversation_detail(request, conversation_id):
    role, user, company, error = demo_context(request)
    if error:
        return error
    chat = Conversation.objects.filter(id=conversation_id, company=company, user=user).select_related("sale", "sale__product").first()
    if not chat:
        return Response({"detail": "Conversa não encontrada neste perfil."}, status=404)
    return Response({
        "id": chat.id,
        "title": chat.title,
        "sale_id": chat.sale_id,
        "sale_label": f"Resumo diário · {chat.sale.sold_at:%d/%m/%Y}" if chat.sale else "Conversa geral",
        "stage": chat.stage,
        "stage_label": chat.get_stage_display(),
        "messages": [
            {"id": item.id, "role": item.role, "content": item.content, "sources": item.sources, "evidence": item.evidence, "links": item.internal_links, "source": item.source_label, "used_web_search": item.used_web_search, "feedback": ({"rating": item.feedback.rating, "reason": item.feedback.reason} if hasattr(item, "feedback") else None), "created_at": item.created_at}
            for item in chat.messages.all()
        ],
    })


@api_view(["POST"])
def assistant_feedback(request, message_id):
    role, user, company, error = demo_context(request)
    if error:
        return error
    message = ChatMessage.objects.filter(
        id=message_id, role=ChatMessage.Role.ASSISTANT,
        conversation__company=company, conversation__user=user,
    ).first()
    if not message:
        return Response({"detail": "Resposta não encontrada nesta demonstração."}, status=404)
    rating = request.data.get("rating")
    if rating not in AssistantFeedback.Rating.values:
        return Response({"detail": "Escolha se a resposta ajudou."}, status=400)
    feedback, _ = AssistantFeedback.objects.update_or_create(
        message=message,
        defaults={"rating": rating, "reason": str(request.data.get("reason", "")).strip()[:300]},
    )
    return Response({"rating": feedback.rating, "reason": feedback.reason})


def serialize_specialization(item):
    return {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "product_ids": list(item.products.values_list("id", flat=True)),
        "products": list(item.products.values("id", "name", "sku")),
        "audience": item.audience,
        "differentiators": item.differentiators,
        "limitations": item.limitations,
        "recommended_questions": item.recommended_questions,
        "sales_guidance": item.sales_guidance,
        "active": item.active,
    }


@api_view(["GET", "POST"])
def specializations_list(request):
    role, user, company, error = demo_context(request)
    if error:
        return error
    if role != "gerente":
        return Response({"detail": "A configuração de especializações é exclusiva do perfil gerente."}, status=403)
    if request.method == "GET":
        items = ProductSpecialization.objects.filter(company=company).prefetch_related("products")
        return Response([serialize_specialization(item) for item in items])
    title = str(request.data.get("title", "")).strip()
    category = str(request.data.get("category", "")).strip()
    if not title or not category:
        return Response({"detail": "Informe o nome da especialização e a categoria."}, status=400)
    if ProductSpecialization.objects.filter(company=company, title=title).exists():
        return Response({"detail": "Já existe uma especialização com esse nome."}, status=409)
    item = ProductSpecialization.objects.create(
        company=company,
        title=title,
        category=category,
        audience=str(request.data.get("audience", "")),
        differentiators=str(request.data.get("differentiators", "")),
        limitations=str(request.data.get("limitations", "")),
        recommended_questions=str(request.data.get("recommended_questions", "")),
        sales_guidance=str(request.data.get("sales_guidance", "")),
    )
    product_ids = request.data.get("product_ids", [])
    item.products.set(Product.objects.filter(company=company, id__in=product_ids))
    AuditEvent.objects.create(company=company, actor=user, action="specialization.created", object_type="ProductSpecialization", object_id=str(item.id))
    return Response(serialize_specialization(item), status=201)


@api_view(["PATCH", "DELETE"])
def specialization_detail(request, specialization_id):
    role, user, company, error = demo_context(request)
    if error:
        return error
    if role != "gerente":
        return Response({"detail": "A configuração de especializações é exclusiva do perfil gerente."}, status=403)
    item = ProductSpecialization.objects.filter(id=specialization_id, company=company).first()
    if not item:
        return Response({"detail": "Especialização não encontrada."}, status=404)
    if request.method == "DELETE":
        item.delete()
        AuditEvent.objects.create(company=company, actor=user, action="specialization.deleted", object_type="ProductSpecialization", object_id=str(specialization_id))
        return Response(status=204)
    for field in ["title", "category", "audience", "differentiators", "limitations", "recommended_questions", "sales_guidance", "active"]:
        if field in request.data:
            setattr(item, field, request.data[field])
    item.save()
    if "product_ids" in request.data:
        item.products.set(Product.objects.filter(company=company, id__in=request.data["product_ids"]))
    AuditEvent.objects.create(company=company, actor=user, action="specialization.updated", object_type="ProductSpecialization", object_id=str(item.id))
    return Response(serialize_specialization(item))
