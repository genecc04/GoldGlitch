from datetime import date
import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.db.models import Sum
from .models import Transaction, Category, Budget
from .forms import TransactionForm, BudgetForm


def home(request):
    return render(request, 'tracker/home.html')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'tracker/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'tracker/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'tracker/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'tracker/transaction_confirm_delete.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'tracker/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 20

    def get_queryset(self):
        qs = Transaction.objects.filter(user=self.request.user)

        month = self.request.GET.get('month')
        if month:
            year, mon = month.split('-')
            qs = qs.filter(date__year=year, date__month=mon)

        category_id = self.request.GET.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        type_ = self.request.GET.get('type')
        if type_:
            qs = qs.filter(type=type_)

        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(description__icontains=search)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(user=self.request.user)
        return context


class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'tracker/budget_list.html'
    context_object_name = 'budgets'

    def get_queryset(self):
        qs = Budget.objects.filter(user=self.request.user).select_related('category')
        for budget in qs:
            spent = Transaction.objects.filter(
                user=self.request.user,
                category=budget.category,
                type=Transaction.EXPENSE,
                date__year=budget.month.year,
                date__month=budget.month.month,
            ).aggregate(total=Sum('amount'))['total'] or 0
            budget.spent = spent
            budget.remaining = budget.amount - spent
        return qs


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'tracker/budget_form.html'
    success_url = reverse_lazy('budget_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'tracker/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = date.today()

        month_transactions = Transaction.objects.filter(
            user=user, date__year=today.year, date__month=today.month
        )

        income = month_transactions.filter(type=Transaction.INCOME).aggregate(
            total=Sum('amount'))['total'] or 0
        expenses = month_transactions.filter(type=Transaction.EXPENSE).aggregate(
            total=Sum('amount'))['total'] or 0

        by_category = (
            month_transactions.filter(type=Transaction.EXPENSE)
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        context['income'] = income
        context['expenses'] = expenses
        context['balance'] = income - expenses
        context['category_labels'] = [
            c['category__name'] or 'Uncategorized' for c in by_category
        ]
        context['category_totals'] = [float(c['total']) for c in by_category]
        return context


@login_required
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])

    transactions = Transaction.objects.filter(user=request.user).select_related('category')
    for t in transactions:
        writer.writerow([
            t.date,
            t.get_type_display(),
            t.category.name if t.category else 'Uncategorized',
            t.amount,
            t.description,
        ])

    return response