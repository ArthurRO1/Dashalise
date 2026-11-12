from rest_framework import serializers

from .models import Alert, Sale, SaleReflection


class SaleReflectionSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.get_full_name", read_only=True)
    actor_name = serializers.SerializerMethodField()
    stage_label = serializers.CharField(source="get_stage_display", read_only=True)

    class Meta:
        model = SaleReflection
        fields = ["id", "seller_name", "actor_name", "stage", "stage_label", "challenge", "created_at"]

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor else ""


class SaleSerializer(serializers.ModelSerializer):
    seller_name = serializers.CharField(source="seller.get_full_name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    commission_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    reflections = SaleReflectionSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = [
            "id", "external_id", "customer_name", "seller", "seller_name", "team", "team_name",
            "product", "product_name", "amount", "commission_rate", "commission_amount",
            "status", "sold_at", "reflections",
        ]


class AlertSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True, default="")
    team_name = serializers.CharField(source="team.name", read_only=True, default="")

    class Meta:
        model = Alert
        fields = ["id", "title", "message", "severity", "read_at", "created_at", "user_id", "user_name", "team_name"]
