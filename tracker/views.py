from datetime import date
import csv
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.db.models import Sum
from django.utils import timezone
from .models import Transaction, Category, Budget, Goal
from .forms import TransactionForm, BudgetForm, GoalForm, CategoryForm


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


class AjaxFormMixin:
    modal_template_name = None

    def get_template_names(self):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return [self.modal_template_name]
        return super().get_template_names()

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return response


class TransactionCreateView(AjaxFormMixin, LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'tracker/transaction_form.html'
    modal_template_name = 'tracker/transaction_form_modal.html'
    success_url = reverse_lazy('transaction_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TransactionUpdateView(AjaxFormMixin, LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'tracker/transaction_form.html'
    modal_template_name = 'tracker/transaction_form_modal.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class TransactionDeleteView(AjaxFormMixin, LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'tracker/transaction_confirm_delete.html'
    modal_template_name = 'tracker/transaction_confirm_delete_modal.html'
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


class BudgetCreateView(AjaxFormMixin, LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'tracker/budget_form.html'
    modal_template_name = 'tracker/budget_form_modal.html'
    success_url = reverse_lazy('budget_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class BudgetUpdateView(AjaxFormMixin, LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'tracker/budget_form.html'
    modal_template_name = 'tracker/budget_form_modal.html'
    success_url = reverse_lazy('budget_list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class BudgetDeleteView(AjaxFormMixin, LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = 'tracker/budget_confirm_delete.html'
    modal_template_name = 'tracker/budget_confirm_delete_modal.html'
    success_url = reverse_lazy('budget_list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)


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
        transfers = month_transactions.filter(type=Transaction.TRANSFER).aggregate(
            total=Sum('amount'))['total'] or 0

        total_savings = Transaction.objects.filter(
            user=user, type=Transaction.TRANSFER
        ).aggregate(total=Sum('amount'))['total'] or 0

        def category_breakdown(queryset):
            rows = (
                queryset
                .values('category__name')
                .annotate(total=Sum('amount'))
                .order_by('-total')
            )
            labels = [r['category__name'] or 'Uncategorized' for r in rows]
            totals = [float(r['total']) for r in rows]
            return labels, totals

        overall_labels, overall_totals = category_breakdown(
            month_transactions.filter(type=Transaction.EXPENSE)
        )
        expense_labels, expense_totals = category_breakdown(
            month_transactions.filter(type=Transaction.EXPENSE)
        )
        income_labels, income_totals = category_breakdown(
            month_transactions.filter(type=Transaction.INCOME)
        )

        context['income'] = income
        context['expenses'] = expenses
        context['balance'] = income - expenses - transfers
        context['total_savings'] = total_savings
        context['category_labels'] = overall_labels
        context['category_totals'] = overall_totals
        context['expense_labels'] = expense_labels
        context['expense_totals'] = expense_totals
        context['income_labels'] = income_labels
        context['income_totals'] = income_totals
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


class GoalCreateView(AjaxFormMixin, LoginRequiredMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'tracker/goal_form.html'
    modal_template_name = 'tracker/goal_form_modal.html'
    success_url = reverse_lazy('goal_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = 'tracker/goal_list.html'
    context_object_name = 'goals'

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user)
        for goal in qs:
            saved = Transaction.objects.filter(
                user=self.request.user,
                goal=goal,
            ).aggregate(total=Sum('amount'))['total'] or 0
            goal.saved = saved
            goal.remaining = goal.target_amount - saved
            goal.percent = min(100, int(saved / goal.target_amount * 100)) if goal.target_amount else 0
        return qs


class GoalUpdateView(AjaxFormMixin, LoginRequiredMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = 'tracker/goal_form.html'
    modal_template_name = 'tracker/goal_form_modal.html'
    success_url = reverse_lazy('goal_list')

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class GoalDeleteView(AjaxFormMixin, LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = 'tracker/goal_confirm_delete.html'
    modal_template_name = 'tracker/goal_confirm_delete_modal.html'
    success_url = reverse_lazy('goal_list')

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


@login_required
def complete_goal(request, pk):
    goal = get_object_or_404(Goal, pk=pk, user=request.user)
    if request.method == 'POST':
        goal.is_completed = True
        goal.completed_at = timezone.now().date()
        goal.save()
    return redirect('goal_list')


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'tracker/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class CategoryCreateView(AjaxFormMixin, LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'tracker/category_form.html'
    modal_template_name = 'tracker/category_form_modal.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class CategoryUpdateView(AjaxFormMixin, LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'tracker/category_form.html'
    modal_template_name = 'tracker/category_form_modal.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class CategoryDeleteView(AjaxFormMixin, LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'tracker/category_confirm_delete.html'
    modal_template_name = 'tracker/category_confirm_delete_modal.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)