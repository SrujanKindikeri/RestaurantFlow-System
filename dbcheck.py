from organizations.models import Organization
print('Count:', Organization.objects.count())
print([o.name for o in Organization.objects.order_by('-created_at')[:4]])