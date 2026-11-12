"""Deterministic business calculations shared by API and assistant."""
from decimal import Decimal
import calendar
from datetime import timedelta

from django.db.models import Count, Sum

from .dates import latest_data_date
from .models import Alert, Goal, KnowledgeArticle, Sale, SaleReflection, Team, TeamMembership


def visible_sales(user, role, company, start=None, end=None):
    queryset = Sale.objects.filter(company=company).select_related("seller", "team", "product")
    if role == "funcionario":
        queryset = queryset.filter(seller=user)
    elif role == "supervisor":
        teams = user.supervised_teams.filter(company=company)
        if not teams.exists():
            teams = user.team_memberships.filter(team__company=company).values_list("team_id", flat=True)
        queryset = queryset.filter(team__in=teams)
    elif role == "gerente":
        teams = Team.objects.filter(company=company, manager=user)
        queryset = queryset.filter(team__in=teams)
    if start:
        queryset = queryset.filter(sold_at__gte=start)
    if end:
        queryset = queryset.filter(sold_at__lte=end)
    return queryset


def dashboard_summary(user, role, company, start, end):
    sales = visible_sales(user, role, company, start, end).filter(status=Sale.Status.VALID)
    totals = sales.aggregate(
        amount=Sum("amount"), orders=Sum("sales_count"), pieces=Sum("pieces"),
        attendances=Sum("attendances"), daily_records=Count("id"),
    )
    revenue = totals["amount"] or Decimal("0")
    commission = revenue * Decimal("0.03")
    month_end = (end.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    if start.day == 1 and end == month_end:
        individual_goals = Goal.objects.filter(
            company=company,
            scope=Goal.Scope.USER,
            period_start__year=end.year,
            period_start__month=end.month,
            period_end__lte=end,
        )
        if role == "funcionario":
            individual_goals = individual_goals.filter(user=user)
        elif role == "supervisor":
            scoped_teams = user.supervised_teams.filter(company=company)
            if not scoped_teams.exists():
                scoped_teams = Team.objects.filter(company=company, memberships__user=user)
            eligible_sellers = TeamMembership.objects.filter(team__in=scoped_teams).values("user_id")
            individual_goals = individual_goals.filter(user_id__in=eligible_sellers)
        elif role == "gerente":
            eligible_sellers = TeamMembership.objects.filter(team__manager=user).values("user_id")
            individual_goals = individual_goals.filter(user_id__in=eligible_sellers)
        revenue_by_seller = dict(
            sales.values("seller_id").annotate(total=Sum("amount")).values_list("seller_id", "total")
        )
        for individual_goal in individual_goals:
            seller_revenue = revenue_by_seller.get(individual_goal.user_id, Decimal("0"))
            if seller_revenue >= individual_goal.target_amount:
                commission += Decimal("300")
    if role == "funcionario":
        goal = Goal.objects.filter(company=company, user=user, period_start__lte=end, period_end__gte=start).first()
    elif role == "supervisor":
        teams = user.supervised_teams.filter(company=company)
        if not teams.exists():
            teams = TeamMembership.objects.filter(user=user, team__company=company).values("team")
            goal = Goal.objects.filter(company=company, scope=Goal.Scope.TEAM, team__in=teams, period_start__year=end.year, period_start__month=end.month).aggregate(target=Sum("target_amount"))["target"]
        else:
            goal = Goal.objects.filter(company=company, scope=Goal.Scope.TEAM, team__in=teams, period_start__year=end.year, period_start__month=end.month).aggregate(target=Sum("target_amount"))["target"]
        if isinstance(goal, Decimal):
            target = goal
        else:
            target = goal.target_amount if goal else Decimal("0")
        goal = None
    elif role == "gerente":
        team_ids = Team.objects.filter(company=company, manager=user).values("id")
        target = Goal.objects.filter(company=company, scope=Goal.Scope.TEAM, team_id__in=team_ids, period_start__year=end.year, period_start__month=end.month).aggregate(target=Sum("target_amount"))["target"] or Decimal("0")
        goal = None
    else:
        goal = Goal.objects.filter(company=company, scope=Goal.Scope.COMPANY, period_start__lte=end, period_end__gte=start).first()
    if role not in {"supervisor", "gerente"}:
        target = goal.target_amount if goal else Decimal("0")
    return {
        "revenue": revenue,
        "orders": totals["orders"] or 0,
        "pieces": totals["pieces"] or 0,
        "attendances": totals["attendances"] or 0,
        "daily_records": totals["daily_records"] or 0,
        "conversion_rate_percent": round((totals["orders"] or 0) / totals["attendances"] * 100, 1) if totals["attendances"] else 0,
        "pieces_per_sale": round((totals["pieces"] or 0) / totals["orders"], 2) if totals["orders"] else 0,
        "average_item_price": revenue / totals["pieces"] if totals["pieces"] else Decimal("0"),
        "commission": commission,
        "goal": target,
        "goal_progress_percent": round(float(revenue / target * 100), 1) if target else 0,
        "remaining": max(target - revenue, Decimal("0")),
        "average_order_value": revenue / totals["orders"] if totals["orders"] else Decimal("0"),
    }


def _upsert_smart_alert(company, title, message, severity, *, user=None, team=None):
    alert, created = Alert.objects.get_or_create(
        company=company,
        title=title,
        user=user,
        team=team,
        defaults={"message": message, "severity": severity},
    )
    if not created and (alert.message != message or alert.severity != severity):
        alert.message = message
        alert.severity = severity
        alert.read_at = None
        alert.save(update_fields=["message", "severity", "read_at"])
    return alert


def _resolve_smart_alert(company, title, *, user=None, team=None):
    alert = Alert.objects.filter(
        company=company,
        title=title,
        user=user,
        team=team,
    ).exclude(message__startswith="[Resolvido]").first()
    if alert:
        alert.message = f"[Resolvido] {alert.message}"
        alert.read_at = timezone.now()
        alert.save(update_fields=["message", "read_at"])


def _refresh_employee_coaching(company, person, today, month_start, days_in_month):
    investigation = KnowledgeArticle.objects.filter(company=company, active=True, stage="investigate").first()
    objection = KnowledgeArticle.objects.filter(company=company, active=True, stage="decision").first()
    investigation_tip = (
        "Pratique perguntas abertas para confirmar situação, dificuldade e resultado desejado antes de recomendar."
        if not investigation else
        "Pratique SPIN: investigue situação, problema e resultado desejado antes de apresentar a solução."
    )
    objection_tip = (
        "Confirme a expectativa, explique limites e combine o próximo passo sem pressionar."
        if not objection else
        "Antes de responder a uma objeção, investigue se ela envolve preço, confiança, utilidade ou prazo; esclareça limites e combine um próximo passo."
    )
    employee_goal = Goal.objects.filter(
        company=company, scope=Goal.Scope.USER, user=person,
        period_start__lte=today, period_end__gte=today,
    ).first()
    if not employee_goal or employee_goal.target_amount <= 0:
        _resolve_smart_alert(company, "[Desenvolvimento] Ritmo para a meta", user=person)
        _resolve_smart_alert(company, "[Desenvolvimento] Revisar vendas canceladas", user=person)
    else:
        employee_sales = Sale.objects.filter(
            company=company, seller=person, sold_at__gte=month_start, sold_at__lte=today,
        )
        employee_revenue = employee_sales.filter(status=Sale.Status.VALID).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        employee_projection = employee_revenue / Decimal(today.day) * Decimal(days_in_month)
        remaining = max(employee_goal.target_amount - employee_revenue, Decimal("0"))
        days_left = max(days_in_month - today.day, 0)
        daily_needed = remaining / Decimal(max(days_left, 1))
        goal_title = "[Desenvolvimento] Ritmo para a meta"
        if today.day >= 5 and employee_projection < employee_goal.target_amount * Decimal("0.90"):
            _upsert_smart_alert(
                company, goal_title,
                f"Indicador de {person.get_full_name()}: projeção linear de R$ {employee_projection:,.0f} para uma meta de R$ {employee_goal.target_amount:,.0f}. Faltam R$ {remaining:,.0f}, com {days_left} dias até o fim do mês (ritmo necessário: R$ {daily_needed:,.0f}/dia). {investigation_tip}",
                Alert.Severity.WARNING, user=person,
            )
        else:
            _resolve_smart_alert(company, goal_title, user=person)

        # The challenge dataset has daily summaries and no canceled-order records.
        # Clear any stale alert produced by the earlier mock dataset.
        _resolve_smart_alert(company, "[Desenvolvimento] Revisar vendas canceladas", user=person)

    reflection = SaleReflection.objects.filter(
        company=company, seller=person, created_at__date__gte=month_start,
    ).select_related("sale").first()
    for stage, stage_label in SaleReflection.STAGES:
        title = f"[Desenvolvimento] Prática: {stage_label}"
        if not reflection or reflection.stage != stage:
            _resolve_smart_alert(company, title, user=person)
            continue
        article = KnowledgeArticle.objects.filter(company=company, active=True, stage=stage).first()
        advice = article.content[:380] if article else "Revise as perguntas e orientações desta etapa no Método de venda adaptativa."
        _upsert_smart_alert(
            company, title,
            f"Dificuldade registrada na venda #{reflection.sale_id}: {reflection.challenge} Prática sugerida com base no conteúdo comercial: {advice}",
            Alert.Severity.INFO, user=person,
        )


def refresh_smart_alerts(user, role, company):
    """Create/update data-driven notices for the selected profile's authorized scope."""
    today = latest_data_date()
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    elapsed_ratio = today.day / days_in_month
    period_sales = visible_sales(user, role, company, month_start, today)
    valid_sales = period_sales.filter(status=Sale.Status.VALID)
    current = valid_sales.aggregate(revenue=Sum("amount"), orders=Sum("sales_count"))
    revenue = current["revenue"] or Decimal("0")

    if role == "funcionario":
        goals = Goal.objects.filter(
            company=company,
            scope=Goal.Scope.USER,
            user=user,
            period_start__lte=today,
            period_end__gte=today,
        )
        alert_user = user
        alert_team = None
        label = "sua meta"
    elif role == "supervisor":
        teams = Team.objects.filter(company=company, supervisor=user)
        if not teams.exists():
            teams = Team.objects.filter(company=company, memberships__user=user)
        goals = Goal.objects.filter(
            company=company,
            scope=Goal.Scope.TEAM,
            team__in=teams,
            period_start__lte=today,
            period_end__gte=today,
        )
        alert_user = user
        alert_team = None
        label = "a meta da equipe"
    elif role == "gerente":
        teams = Team.objects.filter(company=company, manager=user)
        goals = Goal.objects.filter(
            company=company,
            scope=Goal.Scope.TEAM,
            team__in=teams,
            period_start__lte=today,
            period_end__gte=today,
        )
        alert_user = user
        alert_team = None
        label = "a meta da loja"
    else:
        goals = Goal.objects.filter(
            company=company,
            scope=Goal.Scope.COMPANY,
            period_start__lte=today,
            period_end__gte=today,
        )
        alert_user = None
        alert_team = None
        label = "a meta da empresa"

    if role in {"supervisor", "gerente"}:
        target = goals.aggregate(target=Sum("target_amount"))["target"] or Decimal("0")
    else:
        goal = goals.first()
        target = goal.target_amount if goal else Decimal("0")
    if target > 0:
        progress = revenue / target
        projected = revenue / Decimal(today.day) * Decimal(days_in_month)
        risk_title = "[Inteligente] Meta em risco"
        pace_title = "[Inteligente] Ritmo acima do esperado"
        if projected < target * Decimal("0.90") and today.day >= 5:
            _upsert_smart_alert(
                company,
                risk_title,
                f"No ritmo atual, a projeção é R$ {projected:,.0f} para {label} de R$ {target:,.0f}. Restam {max(days_in_month - today.day, 0)} dias no mês; revise o ritmo e as oportunidades abertas.",
                Alert.Severity.WARNING,
                user=alert_user,
                team=alert_team,
            )
            _resolve_smart_alert(company, pace_title, user=alert_user, team=alert_team)
        elif progress >= Decimal(str(elapsed_ratio + 0.15)) and revenue < target:
            _upsert_smart_alert(
                company,
                pace_title,
                f"As vendas válidas estão em {progress:.0%} de {label}; o avanço está acima do ritmo esperado para este ponto do mês.",
                Alert.Severity.INFO,
                user=alert_user,
                team=alert_team,
            )
            _resolve_smart_alert(company, risk_title, user=alert_user, team=alert_team)
        else:
            _resolve_smart_alert(company, risk_title, user=alert_user, team=alert_team)
            _resolve_smart_alert(company, pace_title, user=alert_user, team=alert_team)
    else:
        _resolve_smart_alert(company, "[Inteligente] Meta em risco", user=alert_user, team=alert_team)
        _resolve_smart_alert(company, "[Inteligente] Ritmo acima do esperado", user=alert_user, team=alert_team)

    # Challenge 2 does not contain canceled-sale records, so no cancellation rate is inferred.
    _resolve_smart_alert(company, "[Inteligente] Cancelamentos acima do limite", user=alert_user, team=alert_team)

    if revenue > 0 and (current["orders"] or 0) >= 5 and valid_sales.filter(product__isnull=False).exists():
        top_product = (
            valid_sales.values("product__name")
            .annotate(amount=Sum("amount"))
            .order_by("-amount")
            .first()
        )
        if top_product and top_product["amount"] / revenue >= Decimal("0.65"):
            _upsert_smart_alert(
                company,
                "[Inteligente] Vendas concentradas em um produto",
                f"{top_product['product__name']} representa {top_product['amount'] / revenue:.0%} da receita visível. Considere verificar a variedade de produtos e as necessidades dos clientes.",
                Alert.Severity.INFO,
                user=alert_user,
                team=alert_team,
            )
        else:
            _resolve_smart_alert(company, "[Inteligente] Vendas concentradas em um produto", user=alert_user, team=alert_team)
    else:
        _resolve_smart_alert(company, "[Inteligente] Vendas concentradas em um produto", user=alert_user, team=alert_team)

    if role == "funcionario":
        _refresh_employee_coaching(company, user, today, month_start, days_in_month)

    if role in {"gerente", "administrador"}:
        scoped_teams = Team.objects.filter(company=company)
        if role == "gerente":
            scoped_teams = scoped_teams.filter(manager=user)
        for team in scoped_teams:
            team_goal = Goal.objects.filter(
                company=company,
                scope=Goal.Scope.TEAM,
                team=team,
                period_start__lte=today,
                period_end__gte=today,
            ).first()
            if not team_goal or team_goal.target_amount <= 0:
                _resolve_smart_alert(company, f"[Inteligente] Meta da equipe {team.name} em risco", team=team)
                continue
            team_revenue = Sale.objects.filter(
                company=company,
                team=team,
                status=Sale.Status.VALID,
                sold_at__gte=month_start,
                sold_at__lte=today,
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            team_projection = team_revenue / Decimal(today.day) * Decimal(days_in_month)
            if team_projection < team_goal.target_amount * Decimal("0.90") and today.day >= 5:
                _upsert_smart_alert(
                    company,
                    f"[Inteligente] Meta da equipe {team.name} em risco",
                    f"No ritmo atual, {team.name} deve fechar em {team_projection:,.0f}, abaixo da meta de {team_goal.target_amount:,.0f}.",
                    Alert.Severity.WARNING,
                    team=team,
                )
            else:
                _resolve_smart_alert(company, f"[Inteligente] Meta da equipe {team.name} em risco", team=team)

    return Alert.objects.filter(company=company)
