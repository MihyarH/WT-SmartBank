from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Account, Transaction
import logging
from decimal import Decimal, InvalidOperation

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']

        user = User.objects.create_user(username=username, password=password, email=email)
        Account.objects.create(user=user, balance=1000.00)
        return redirect('login')

    return render(request, 'bank/register.html')

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

    # Pass the data to the template
    return render(request, 'bank/dashboard.html', {
        'account': account,
        'transactions': transactions,
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