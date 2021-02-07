from django import forms
from django.core.exceptions import ValidationError
from django.core import validators
from game.models import League, Game, Player, Tipp

class SignUpForm(forms.Form):
    username = forms.CharField()
    email1 = forms.EmailField(label='Email address', widget=forms.TextInput(attrs={'placeholder': 'Your email address', 'required': 'true'}))
    email2 = forms.EmailField(label='Repeat Email address', widget=forms.TextInput(attrs={'placeholder': 'Repeat email address', 'required': 'true'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'required': 'true'}), label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Repeat Password', 'required': 'true'}), label='Repeat Password')

class TippForm(forms.ModelForm):
    tipp_home = forms.IntegerField(label='Home Team', widget=forms.TextInput(attrs={'placeholder': '0', 'required': 'true'}))
    tipp_away = forms.IntegerField(label='Away Team', widget=forms.TextInput(attrs={'placeholder': '0', 'required': 'true'}))
        
    class Meta:
        model = Tipp
        fields = (['tipp_home','tipp_away'])

class GameForm(forms.ModelForm):
    name = forms.CharField(label='Name of the Game', widget=forms.TextInput(attrs={'placeholder': 'MyGame', 'required': 'true'}))
    pts_exact = forms.IntegerField(label='Exact Result',  widget=forms.TextInput(attrs={'placeholder': '0', 'required': 'true'}))
    pts_difference = forms.IntegerField(label='Goal Difference',  widget=forms.TextInput(attrs={'placeholder': '0', 'required': 'true'}))
    pts_winner = forms.IntegerField(label='Winner',  widget=forms.TextInput(attrs={'placeholder': '0', 'required': 'true'}))
    pts_wrong = forms.IntegerField(label='Wrong Winner',  widget=forms.TextInput(attrs={'placeholder': '0', 'required': 'false'}))
    leagues = forms.ModelMultipleChoiceField(queryset=League.objects.all(), widget=forms.CheckboxSelectMultiple)
    players = forms.ModelMultipleChoiceField(queryset=Player.objects.all(), widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Game
        fields = (['name','pts_exact','pts_difference','pts_winner','pts_wrong','leagues','players'])
