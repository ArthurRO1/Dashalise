"""Export evaluated assistant turns as JSONL for human review and curation."""
import json

from django.core.management.base import BaseCommand

from sales.models import AssistantFeedback


class Command(BaseCommand):
    help = "Exporta avaliações do chat para revisão antes de atualizar exemplos de referência."

    def add_arguments(self, parser):
        parser.add_argument("--rating", choices=("helpful", "not_helpful"))

    def handle(self, *args, **options):
        feedback = AssistantFeedback.objects.select_related("message__conversation").order_by("created_at")
        if options["rating"]:
            feedback = feedback.filter(rating=options["rating"])
        for item in feedback.iterator():
            message = item.message
            previous_user_message = message.conversation.messages.filter(
                role="user", id__lt=message.id,
            ).order_by("-id").first()
            row = {
                "question": previous_user_message.content if previous_user_message else "",
                "answer": message.content,
                "rating": item.rating,
                "reason": item.reason,
                "stage": message.conversation.stage,
                "source": message.source_label,
                "reviewed_at": item.updated_at.isoformat(),
            }
            self.stdout.write(json.dumps(row, ensure_ascii=False))
