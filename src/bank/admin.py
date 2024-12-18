from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Account, Transaction

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'gender', 'phone_number', 'birth_date', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('phone_number', 'gender', 'address', 'birth_date')
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'recipient', 'transaction_type', 'amount', 'date')
