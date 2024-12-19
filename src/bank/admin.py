from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Account, Transaction

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'phone_number', 'dob', 'is_staff')  # Use 'dob' instead of 'birth_date'
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'gender', 'address', 'dob')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('account', 'transaction_type', 'amount', 'date')
