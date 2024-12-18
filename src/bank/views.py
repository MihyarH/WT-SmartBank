from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Account, Transaction
import logging
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
import csv
from django.http import HttpResponse
from datetime import datetime
from django.contrib.auth.forms import PasswordChangeForm
from .forms import CustomUserRegistrationForm

User = get_user_model()


def register(request):
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            Account.objects.create(user=user, balance=0.00)
            return redirect('login')
    else:
        form = CustomUserRegistrationForm()
    return render(request, 'bank/register.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('dashboard')  # Redirect to the dashboard
        else:
            return render(request, 'bank/login.html', {'error': 'Invalid credentials'})

    return render(request, 'bank/login.html')


@login_required
def dashboard(request):
    # Get the logged-in user's account
    account = Account.objects.get(user=request.user)

    # Get all transactions for the user's account
    transactions = Transaction.objects.filter(account=account).order_by('-date')

    # Apply filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    transaction_type = request.GET.get('transaction_type')

    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    # Add pagination
    paginator = Paginator(transactions, 5)  # Show 5 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the paginated transactions and filters to the template
    return render(request, 'bank/dashboard.html', {
        'account': account,
        'transactions': page_obj,  # Use `page_obj` instead of `transactions`
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'transaction_type': transaction_type,
        }
    })



@login_required
def transfer(request):
    if request.method == 'POST':
        recipient_username = request.POST['recipient']
        amount = request.POST['amount']

        try:
            # Validate and convert the amount to Decimal
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except (ValueError, InvalidOperation):
            messages.error(request, 'Invalid amount. Please enter a valid positive number.')
            return render(request, 'bank/transfer.html')

        try:
            # Fetch recipient and sender accounts
            recipient_user = User.objects.get(username=recipient_username)
            recipient_account = Account.objects.get(user=recipient_user)
            sender_account = Account.objects.get(user=request.user)

            # Check if the sender has enough balance
            if sender_account.balance >= amount:
                # Deduct from sender
                sender_account.balance -= amount
                sender_account.save()

                # Add to recipient
                recipient_account.balance += amount
                recipient_account.save()

                # Log transactions
                Transaction.objects.create(
                    account=sender_account,
                    recipient=recipient_account,
                    transaction_type='debit',
                    amount=amount,
                )
                Transaction.objects.create(
                    account=recipient_account,
                    recipient=sender_account,
                    transaction_type='credit',
                    amount=amount,
                )

                messages.success(request, 'Transfer successful!')
            else:
                messages.error(request, 'Insufficient balance.')

        except User.DoesNotExist:
            messages.error(request, 'Recipient does not exist.')

        except Exception as e:
            logging.error(f"Transfer Error: {e}")
            messages.error(request, 'An error occurred. Please try again.')

    return render(request, 'bank/transfer.html')


@login_required
def deposit(request):
    if request.method == 'POST':
        amount = request.POST['amount']

        try:
            # Validate and convert the amount to Decimal
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except (ValueError, InvalidOperation):
            messages.error(request, 'Invalid amount. Please enter a valid positive number.')
            return render(request, 'bank/deposit.html')

        # Add the deposit amount to the user's account balance
        account = Account.objects.get(user=request.user)
        account.balance += amount
        account.save()

        # Log the deposit transaction
        Transaction.objects.create(
            account=account,
            transaction_type='credit',
            amount=amount,
        )

        messages.success(request, f'Deposited ${amount} successfully!')
        return redirect('dashboard')

    return render(request, 'bank/deposit.html')



@login_required
def export_transactions(request):
    # Get the logged-in user's account
    account = Account.objects.get(user=request.user)

    # Get all transactions for the user's account
    transactions = Transaction.objects.filter(account=account).order_by('-date')

    # Apply filters only if the values are valid
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    transaction_type = request.GET.get('transaction_type')

    if start_date:
        try:
            transactions = transactions.filter(date__gte=start_date)
        except ValueError:
            pass  # Ignore invalid start_date format

    if end_date:
        try:
            transactions = transactions.filter(date__lte=end_date)
        except ValueError:
            pass  # Ignore invalid end_date format

    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)

    # Create the HTTP response with a CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    # Create a CSV writer
    writer = csv.writer(response)

    # Write the header row
    writer.writerow(['Date', 'Transaction Type', 'Amount'])

    # Write data rows
    for transaction in transactions:
        writer.writerow([transaction.date, transaction.transaction_type, transaction.amount])

    return response



@login_required
def profile(request):
    user = request.user
    message = None

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            email = request.POST.get('email', '').strip()
            user.email = email
            user.save()
            message = "Profile updated successfully."

        elif 'change_password' in request.POST:
            form = PasswordChangeForm(user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  # Prevent logout after password change
                message = "Password changed successfully."
            else:
                message = "Error updating password."

    form = PasswordChangeForm(user)
    return render(request, 'bank/profile.html', {
        'user': user,
        'form': form,
        'message': message,
    })