from django import forms


class RegistryForm(forms.Form):
    address = forms.CharField(label="Registry Address", max_length=100)
