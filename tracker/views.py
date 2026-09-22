from django.urls import reverse_lazy
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Transaction, Category
from .forms import TransactionForm


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