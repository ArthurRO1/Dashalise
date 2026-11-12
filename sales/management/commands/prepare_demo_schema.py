"""Idempotently add the demo chat, specialization and coaching tables to SQLite."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from sales.models import (
    AssistantFeedback,
    ChatMessage,
    Conversation,
    DemoIdentity,
    KnowledgeArticle,
    Product,
    ProductSpecialization,
    PriorYearStoreSales,
    Sale,
    SaleReflection,
    Team,
)


class Command(BaseCommand):
    help = "Atualiza com segurança o esquema SQLite local da demonstração."

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError("Este comando é apenas para a demonstração SQLite.")

        with connection.schema_editor() as editor:
            tables = set(connection.introspection.table_names())

            for model, field_names in (
                (Product, ("category", "description")),
                (KnowledgeArticle, ("stage", "category")),
                (Team, (
                    "manager", "external_id", "city", "state", "region_code", "region_name",
                    "regional_manager_name", "franchisee", "store_type", "opened_at", "opens_sunday",
                )),
                (Sale, ("sales_count", "pieces", "attendances")),
                (ChatMessage, ("evidence",)),
            ):
                if model._meta.db_table not in tables:
                    continue
                with connection.cursor() as cursor:
                    columns = {
                        column.name
                        for column in connection.introspection.get_table_description(
                            cursor, model._meta.db_table
                        )
                    }
                for field_name in field_names:
                    field = model._meta.get_field(field_name)
                    if field.column not in columns:
                        editor.add_field(model, field)
                        columns.add(field.column)
                        self.stdout.write(f"Campo adicionado: {model.__name__}.{field_name}")

            if Sale._meta.db_table in tables:
                field = Sale._meta.get_field("product")
                with connection.cursor() as cursor:
                    columns = {
                        column.name
                        for column in connection.introspection.get_table_description(
                            cursor, Sale._meta.db_table
                        )
                    }
                if field.column in columns and not field.null:
                    nullable_field = field.clone()
                    nullable_field.null = True
                    editor.alter_field(Sale, field, nullable_field, strict=False)

            for model in (
                DemoIdentity, PriorYearStoreSales, ProductSpecialization, Conversation,
                ChatMessage, SaleReflection, AssistantFeedback,
            ):
                if model._meta.db_table not in tables:
                    editor.create_model(model)
                    tables.add(model._meta.db_table)
                    if model is ProductSpecialization:
                        tables.add(ProductSpecialization.products.through._meta.db_table)
                    self.stdout.write(f"Tabela criada: {model._meta.db_table}")

            through = ProductSpecialization.products.through
            if through._meta.db_table not in tables:
                editor.create_model(through)
                self.stdout.write(f"Tabela criada: {through._meta.db_table}")

        self.stdout.write(self.style.SUCCESS("Esquema demonstrativo atualizado."))
