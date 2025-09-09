from django.db import models
from tabs.models import Tab


class Payment(models.Model):
	STATUS_CHOICES = [
		('requires_confirmation', 'Requires Confirmation'),
		('succeeded', 'Succeeded'),
		('failed', 'Failed'),
	]
	
	tab = models.ForeignKey(Tab, on_delete=models.CASCADE, related_name='payments')
	payment_intent_id = models.CharField(max_length=100, unique=True)  # Internal ID only
	amount_p = models.PositiveIntegerField()
	currency = models.CharField(max_length=3, default='gbp')
	status = models.CharField(max_length=50, choices=STATUS_CHOICES)
	failure_reason = models.CharField(max_length=200, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	confirmed_at = models.DateTimeField(null=True, blank=True)

	def __str__(self):
		return f"Payment {self.id} for Tab {self.tab.id} - {self.status}"
