from django.db import models


from django.db import models

class MenuItem(models.Model):
	name = models.CharField(max_length=100)
	unit_price_p = models.PositiveIntegerField()
	vat_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)

	def __str__(self):
		return self.name

class Tab(models.Model):
	STATUS_CHOICES = [
		('open', 'Open'),
		('closed', 'Closed'),
	]
	table_number = models.PositiveIntegerField()
	covers = models.PositiveIntegerField()
	status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
	opened_at = models.DateTimeField(auto_now_add=True)
	closed_at = models.DateTimeField(null=True, blank=True)
	subtotal_p = models.PositiveIntegerField(default=0)
	service_charge_p = models.PositiveIntegerField(default=0)
	vat_total_p = models.PositiveIntegerField(default=0)
	total_p = models.PositiveIntegerField(default=0)

	def __str__(self):
		return f"Tab {self.id} (Table {self.table_number})"

class TabItem(models.Model):
	tab = models.ForeignKey(Tab, on_delete=models.CASCADE, related_name='items')
	menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
	qty = models.PositiveIntegerField()
	unit_price_p = models.PositiveIntegerField()
	vat_rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
	vat_p = models.PositiveIntegerField()
	line_total_p = models.PositiveIntegerField()

	def __str__(self):
		return f"{self.qty} x {self.menu_item.name} for Tab {self.tab.id}"
