"""Relational data model for commercial operations."""
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Team(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=100)
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervised_teams",
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_stores",
    )
    external_id = models.CharField(max_length=24, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True)
    region_code = models.CharField(max_length=12, blank=True)
    region_name = models.CharField(max_length=100, blank=True)
    regional_manager_name = models.CharField(max_length=140, blank=True)
    franchisee = models.CharField(max_length=140, blank=True)
    store_type = models.CharField(max_length=24, blank=True)
    opened_at = models.DateField(null=True, blank=True)
    opens_sunday = models.BooleanField(default=False)

    class Meta:
        unique_together = [("company", "name")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_memberships")
    joined_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = [("team", "user")]


class DemoIdentity(models.Model):
    """Fictional identity and access scope supplied by the internship challenge."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="demo_identities")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="demo_identity")
    external_id = models.CharField(max_length=24, unique=True)
    source_role = models.CharField(max_length=24)
    scope = models.CharField(max_length=160)
    whatsapp = models.CharField(max_length=40, blank=True)
    active_at_demo = models.BooleanField(default=True)
    hired_at = models.DateField(null=True, blank=True)
    terminated_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["external_id"]


class PriorYearStoreSales(models.Model):
    """Store-level daily comparison supplied by the challenge (364-day offset)."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="prior_year_sales")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="prior_year_sales")
    sold_at = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sales_count = models.PositiveIntegerField(default=0)
    pieces = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("company", "team", "sold_at")]
        ordering = ["sold_at"]


class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=140)
    sku = models.CharField(max_length=48)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "sku")]
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductSpecialization(models.Model):
    """Manager-curated product knowledge used as context for the sales assistant."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="specializations")
    title = models.CharField(max_length=140)
    category = models.CharField(max_length=100)
    products = models.ManyToManyField(Product, blank=True, related_name="specializations")
    audience = models.TextField(blank=True, help_text="Perfis de cliente e necessidades atendidas.")
    differentiators = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    recommended_questions = models.TextField(blank=True)
    sales_guidance = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]
        unique_together = [("company", "title")]

    def __str__(self):
        return self.title


class Goal(models.Model):
    class Scope(models.TextChoices):
        USER = "user", "Individual"
        TEAM = "team", "Equipe"
        COMPANY = "company", "Empresa"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="goals")
    scope = models.CharField(max_length=12, choices=Scope.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        ordering = ["-period_start"]


class Sale(models.Model):
    class Status(models.TextChoices):
        VALID = "valid", "Válida"
        PENDING = "pending", "Pendente"
        CANCELLED = "cancelled", "Cancelada"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sales")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales")
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="sales")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    external_id = models.CharField(max_length=100, blank=True)
    customer_name = models.CharField(max_length=140, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=3)
    sales_count = models.PositiveIntegerField(default=1)
    pieces = models.PositiveIntegerField(default=0)
    attendances = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.VALID)
    sold_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sold_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "external_id"],
                condition=~models.Q(external_id=""),
                name="unique_external_sale_per_company",
            )
        ]

    @property
    def commission_amount(self):
        return self.amount * self.commission_rate / 100


class SaleReflection(models.Model):
    """Seller or manager notes about a specific selling challenge and its stage."""
    STAGES = [
        ("observe", "Preparação e abertura"),
        ("investigate", "Investigação da necessidade (SPIN)"),
        ("classify", "Entendimento do momento de compra"),
        ("personalize", "Personalização da abordagem"),
        ("value", "Construção de valor"),
        ("decision", "Objeção e decisão"),
        ("learn", "Acompanhamento e pós-venda"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sale_reflections")
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="reflections")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sale_reflections")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="authored_sale_reflections")
    stage = models.CharField(max_length=16, choices=STAGES)
    challenge = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class Alert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Informativo"
        WARNING = "warning", "Atenção"
        CRITICAL = "critical", "Crítico"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="alerts")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=160)
    message = models.TextField()
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class KnowledgeArticle(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="knowledge_articles")
    title = models.CharField(max_length=180)
    stage = models.CharField(max_length=32, blank=True)
    category = models.CharField(max_length=64, default="metodologia")
    content = models.TextField()
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class Conversation(models.Model):
    class Stage(models.TextChoices):
        OBSERVE = "observe", "Observar"
        INVESTIGATE = "investigate", "Investigar"
        CLASSIFY = "classify", "Classificar"
        PERSONALIZE = "personalize", "Personalizar"
        VALUE = "value", "Construir valor"
        DECISION = "decision", "Conduzir a decisão"
        LEARN = "learn", "Aprender e evoluir"
        GENERAL = "general", "Pergunta geral"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="conversations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales_conversations")
    sale = models.ForeignKey(Sale, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations")
    stage = models.CharField(max_length=16, choices=Stage.choices, default=Stage.GENERAL)
    title = models.CharField(max_length=180, default="Nova conversa")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ChatMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Usuário"
        ASSISTANT = "assistant", "Assistente"
        SYSTEM = "system", "Sistema"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=Role.choices)
    content = models.TextField()
    sources = models.JSONField(default=list, blank=True)
    internal_links = models.JSONField(default=list, blank=True)
    source_label = models.CharField(max_length=80, blank=True)
    used_web_search = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class AssistantFeedback(models.Model):
    """Human signal used to review and improve assistant prompts and knowledge."""
    class Rating(models.TextChoices):
        HELPFUL = "helpful", "Ajudou"
        NOT_HELPFUL = "not_helpful", "Não ajudou"

    message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name="feedback")
    rating = models.CharField(max_length=16, choices=Rating.choices)
    reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AuditEvent(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
