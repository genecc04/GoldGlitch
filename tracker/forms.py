from django import forms
from .models import Category, Transaction, Budget, Goal


class TransactionForm(forms.ModelForm):
    DEPOSIT = 'deposit'
    WITHDRAW = 'withdraw'
    DIRECTION_CHOICES = [
        (DEPOSIT, 'Deposit (add to savings)'),
        (WITHDRAW, 'Withdraw (from savings)'),
    ]

    direction = forms.ChoiceField(
        choices=DIRECTION_CHOICES,
        required=False,
        initial=DEPOSIT,
    )

    class Meta:
        model = Transaction
        fields = ['type', 'category', 'goal', 'amount', 'date', 'description']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }
        help_texts = {
            'amount': 'Always enter a positive number.',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['goal'].queryset = Goal.objects.filter(user=user)

        if self.instance.pk and self.instance.type == Transaction.TRANSFER:
            if self.instance.amount < 0:
                self.fields['direction'].initial = self.WITHDRAW
                self.initial['amount'] = abs(self.instance.amount)
            else:
                self.fields['direction'].initial = self.DEPOSIT

    def clean(self):
        cleaned_data = super().clean()
        type_ = cleaned_data.get('type')
        amount = cleaned_data.get('amount')
        direction = cleaned_data.get('direction')

        if type_ == Transaction.TRANSFER and amount is not None:
            amount = abs(amount)
            if direction == self.WITHDRAW:
                amount = -amount
            cleaned_data['amount'] = amount

        return cleaned_data


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'month']
        widgets = {
            'month': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['category'].queryset = Category.objects.filter(user=user)

    def clean_month(self):
        month = self.cleaned_data['month']
        return month.replace(day=1)


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'target_date']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']