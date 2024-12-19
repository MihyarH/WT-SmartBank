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


# def register(request):
#     if request.method == 'POST':
#         form = CustomUserRegistrationForm(request.POST)
#         if form.is_valid():
#             user = form.save(commit=False) 
#             user.set_password(form.cleaned_data['password']) 
#             user.first_name = form.cleaned_data.get('first_name')
#             user.last_name = form.cleaned_data.get('last_name')
#             user.dob = form.cleaned_data.get('dob')
#             user.phone_number = form.cleaned_data.get('phone_number')
#             user.gender = form.cleaned_data.get('gender')
#             account_type = request.POST.get('account_type')
#             user.save()  # Save to the database
#             Account.objects.create(user=user, balance=0.00)
#             return redirect('login')
#     else:
#         form = CustomUserRegistrationForm()
#     return render(request, 'bank/register.html', {'form': form})

def register(request):
    if request.method == 'POST':
        form = CustomUserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.dob = form.cleaned_data.get('dob')
            user.phone_number = form.cleaned_data.get('phone_number')
            user.gender = form.cleaned_data.get('gender')
            user.save()

            # Create the account(s)
            account_type = request.POST.get('account_type')
            Account.objects.create(user=user, type=account_type, balance=0.00)

            return redirect('login')
    else:
        form = CustomUserRegistrationForm()
    return render(request, 'bank/register.html', {'form': form})


@login_required
def add_account(request):
    if request.method == 'POST':
        account_type = request.POST.get('account_type')
        Account.objects.create(user=request.user, type=account_type, balance=0.00)
        messages.success(request, f'{account_type.capitalize()} account created successfully!')
        return redirect('dashboard')
    return render(request, 'bank/add_account.html')


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
    # Fetch all accounts for the logged-in user
    accounts = Account.objects.filter(user=request.user)

    # Calculate the total balance across all accounts
    total_balance = sum(account.balance for account in accounts)

    # Get all transactions for the user's accounts
    transactions = Transaction.objects.filter(account__in=accounts).order_by('-date')

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

    return render(request, 'bank/dashboard.html', {
        'accounts': accounts,
        'total_balance': total_balance,
        'transactions': page_obj,
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'transaction_type': transaction_type,
        }
    })


@login_required
def deposit(request):
    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        amount = request.POST.get('amount')

        try:
            # Validate and convert the amount to Decimal
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except (ValueError, InvalidOperation):
            messages.error(request, 'Invalid amount. Please enter a valid positive number.')
            return render(request, 'bank/deposit.html', {'accounts': Account.objects.filter(user=request.user)})

        try:
            # Fetch the selected account
            account = Account.objects.get(id=account_id, user=request.user)
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
        except Account.DoesNotExist:
            messages.error(request, 'Selected account does not exist.')

    return render(request, 'bank/deposit.html', {'accounts': Account.objects.filter(user=request.user)})

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
            # Fetch recipient and sender checking accounts
            recipient_user = User.objects.get(username=recipient_username)
            recipient_account = Account.objects.get(user=recipient_user, type='checking')
            sender_account = Account.objects.get(user=request.user, type='checking')

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
        except Account.DoesNotExist:
            messages.error(request, 'Recipient does not have a checking account.')
        except Exception as e:
            logging.error(f"Transfer Error: {e}")
            messages.error(request, 'An error occurred. Please try again.')

    return render(request, 'bank/transfer.html')

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

def landing_page(request):
    return render(request, 'bank/landing.html')