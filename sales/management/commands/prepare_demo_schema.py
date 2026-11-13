"""Idempotently add the demo chat, specialization and coaching tables to SQLite."""
import json

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
                for field_name in field_names:
                    field = model._meta.get_field(field_name)
                    # SQLite's schema_editor.add_field() may rebuild a table. Since
                    # this command runs against the current model (not historical
                    # migration state), nullable fields can then be duplicated in
                    # the rebuilt CREATE TABLE. ALTER TABLE ADD COLUMN is safe for
                    # the simple demo fields below and remains rerunnable.
                    with connection.cursor() as cursor:
                        columns = {
                            column.name
                            for column in connection.introspection.get_table_description(
                                cursor, model._meta.db_table
                            )
                        }
                    if field.column not in columns:
                        definition = field.db_type(connection)
                        if field.is_relation and field.db_constraint:
                            target = field.target_field
                            definition += (
                                f" REFERENCES {connection.ops.quote_name(target.model._meta.db_table)}"
                                f" ({connection.ops.quote_name(target.column)})"
                            )
                        if not field.null:
                            definition += " NOT NULL"
                            if field.has_default() or (field.empty_strings_allowed and not field.null):
                                default = field.get_default()
                                if isinstance(default, (dict, list)):
                                    default = json.dumps(default, ensure_ascii=False)
                                if isinstance(default, bool):
                                    default_sql = "1" if default else "0"
                                elif isinstance(default, (int, float)):
                                    default_sql = str(default)
                                else:
                                    default_sql = "'" + str(default).replace("'", "''") + "'"
                                definition += f" DEFAULT {default_sql}"
                        table_name = connection.ops.quote_name(model._meta.db_table)
                        column_name = connection.ops.quote_name(field.column)
                        with connection.cursor() as cursor:
                            cursor.execute(
                                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
                            )
                        self.stdout.write(f"Campo adicionado: {model.__name__}.{field_name}")

            if Sale._meta.db_table in tables:
                field = Sale._meta.get_field("product")
                with connection.cursor() as cursor:
                    description = connection.introspection.get_table_description(
                        cursor, Sale._meta.db_table
                    )
                    product_column = next((column for column in description if column.name == field.column), None)
                    product_is_not_null = bool(product_column and product_column.null_ok is False)
                if product_is_not_null:
                    old_field = field.clone()
                    old_field.set_attributes_from_name(field.name)
                    old_field.model = Sale
                    old_field.remote_field.model = Product
                    old_field.null = False
                    editor.alter_field(Sale, old_field, field, strict=False)
                    self.stdout.write("Campo atualizado: Sale.product agora aceita valores vazios")

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
