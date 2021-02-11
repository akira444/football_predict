from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Q, F, Count, Sum
from django.utils.timezone import make_aware
import requests
from .models import League, Fixture, UpdateSchedule, Player, Player_Games, Game, Tipp
from .forms import SignUpForm, GameForm, TippForm, InviteForm, ProfileForm
from .api_data import update_fixtures
from .data_utilities import GetTippList, TippQuery
from datetime import date, timedelta, datetime
import pandas as pd

# testing 
class LeagueView(LoginRequiredMixin, View):
    def get(self, request):
        leagues = League.objects.all() #read all leagues from database

        ctx = {'leagues' : leagues}
        return render(request, 'game/leagues.html', ctx) #template

# Signup, login, logout and Profile
class SignUpView(View):
    def get(self, request):
        form = SignUpForm()
        ctx = {'form' : form}
        return render(request, 'game/signup.html', ctx)

    def post(self, request):
        form = SignUpForm(request.POST)
        
        # emails have to match
        if request.POST['email1'] != request.POST['email2']:
            ctx = {'form' : form}
            messages.error(request, 'Email addresses do not match!')
            return render(request, 'game/signup.html', ctx)

        # passwords have to match
        if request.POST['password1'] != request.POST['password2']:
            ctx = {'form' : form}
            messages.error(request, 'Passwords do not match!')
            return render(request, 'game/signup.html', ctx)
        
        try:
            user = User.objects.create_user(username=request.POST['username'], password=request.POST['password1'], email=request.POST['email1'])
            user.save()
            player = Player(user=user)
            player.save()
            login(request, user)
            return redirect('games')
        except IntegrityError:
            messages.error(request, 'Username is already taken, please try another!')
            return render(request, 'game/signup.html')

class LoginView(View):
    def get(self, request):
        #form = LoginForm()
        #ctx = {'form' : form}
        return render(request, 'game/login.html')

    def post(self, request):
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            messages.error(request, 'Incorrect username or password!')
            return render(request, 'game/login.html')
        else:
            login(request, user)
            return redirect('games')

# Logout is very simple 
def LogOutUser(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')
        


class CreateGameView(LoginRequiredMixin, View):
    # This is used to set up new games
    template = 'game/new_game.html'
    def get(self, request):
        form = GameForm()
        ctx = {'form' : form}
        return render(request, self.template, ctx)

    def post(self, request):
        form = GameForm(request.POST)
        if not form.is_valid():
            ctx = {'form' : form}
            return render(request, self.template, ctx)

        newgame = form.save(commit=False)
        creator = Player.objects.all().filter(user__username = request.user).get()
        newgame.creator = creator
        newgame.save()
        form.save_m2m() # This is necessary to save the Many to Many relationship, because this is deactivated if commit=False is used
        # The creator of the game set as an active player in the table Player_Games
        activatecreator = Player_Games.objects.all().filter(game = newgame, player=creator)
        activatecreator.update(status=2) # status = 2 means active player
        return redirect('games')

# This is the main view shown after login, showing all games of the active player
class GamesView(LoginRequiredMixin, View):
    template = 'game/games.html'

    def get(self, request):
        # Get all games of player currently logged in 
        games = Game.objects.all().filter(Q(players__user__username=request.user) & Q(player_games__status=2)) # All active games of a player
        invitations = Game.objects.all().filter(Q(players__user__username=request.user) & Q(player_games__status=3)) # All games the player is invited to

        ctx = {'games' : games, 'invitations' : invitations }

        return render(request, self.template, ctx)
    
class GameAccept(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Accept invitation to game
        accept = Player_Games.objects.all().filter(player__user__username=request.user, game_id=pk)
        accept.update(status=2)

        return redirect('games')

class GameDecline(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Decline invitation to game
        decline = Player_Games.objects.all().filter(player__user__username=request.user, game_id=pk)
        decline.update(status=4)

        return redirect('games')

# Invite view
class InviteView(LoginRequiredMixin, View):
    template = 'game/invite.html'
    def get(self, request, pk):
        game = get_object_or_404(Game, pk=pk)
        form = InviteForm(instance=game)
        ctx = {'form' : form}
        return render(request, self.template, ctx)

    def post(self, request, pk):
        # Update player information
        player = Player.objects.all().filter(user__username = request.user).get()    
        game = get_object_or_404(Game, pk=pk, player=player.id)
        
        form = InviteForm(request.POST, instance=game)  
        form.save()

        return redirect('games')


class ProfileView(LoginRequiredMixin, View):
    template = 'game/profile.html'
    def get(self, request):
        user = get_object_or_404(User, username=request.user)
        form = ProfileForm(instance=user)   
        ctx = {'form' : form}
        return render(request, self.template, ctx)

    def post(self, request):
        user = authenticate(request, username=request.user, password=request.POST['oldpassword'])
        if user is None:
            messages.error(request, 'Old password is not correct!')
            form = ProfileForm(request.POST)   
            ctx = {'form' : form}
            return render(request, self.template, ctx)
        else:
            if request.POST['password1'] != request.POST['password2']:
                form = ProfileForm(request.POST) 
                ctx = {'form' : form}
                messages.error(request, 'Passwords do not match!')
                return render(request, self.template, ctx)
        
        try:
            user = User.objects.all().filter(username=request.user)
            user.update(email=request.POST['email'], username=request.POST['username'])
            user = User.objects.get(username=request.POST['username'])
            user.set_password(request.POST['password1'])
            user.save()
            messages.success(request, 'Your Profile has been updated!')
            user = authenticate(request, username=request.POST['username'], password=request.POST['password1'])
            login(request, user)
            return redirect('games')
        except IntegrityError:
            messages.error(request, 'Username is already taken, please try another!')
            return render(request, self.template)

class GameDetail(LoginRequiredMixin, View):
    # Game Detail
    template = 'game/gamedetail.html'

    def get(self, request, pk):
        # Get info about the game
        game = Game.objects.all().filter(id=pk).get()
        rankings = Player.objects.all().filter(tipp__game_id = game.id).annotate(t_score = Sum('tipp__score'), t_tipps = Count('tipp__id')).order_by('-t_score')
        li_status = ['FT','AET','PEN', 'ABD', 'AWD']
        finished = Count('fixture', filter=Q(fixture__status_short__in=li_status))
        toplay = Count('fixture', filter=(~Q(fixture__status_short__in=li_status)))
        leagues = League.objects.all().filter(games=pk).annotate(finished=finished).annotate(toplay=toplay)
        td = date.today()
        includedays = 8
        player = Player.objects.all().filter(user__username = request.user).get()
        fixtures_started = TippQuery(player_id=player.id, game_id=game.id, from_date=td, to_date=datetime.utcnow()) # Match starts are stored in UTC in database, therefore utcnow has to be used.
        fixtures_tostart = TippQuery(player_id=player.id, game_id=game.id, from_date=datetime.utcnow(), to_date=td+timedelta(days=includedays))
        fcnt = len(list(fixtures_started)) + len(list(fixtures_tostart))
        lu = UpdateSchedule.objects.all().first()

        request.session['redirect_tipp'] = 'gamedetail'
        ctx = {'game' : game, 'leagues' : leagues, 'rankings' : rankings, 'fcnt' : fcnt, 'lupdate' : lu, 'fixtures_started' : fixtures_started, 'fixtures_tostart' : fixtures_tostart, 'days' : includedays-1 }
        return render(request, self.template, ctx)

class TodayView(LoginRequiredMixin, View):
    # Shows the screen with todays fixtures
    def get(self, request):
        td = date.today()
        includedays = 1
        player = Player.objects.all().filter(user__username = request.user).get()
        fixtures_started = TippQuery(player_id=player.id, from_date=td, to_date=datetime.utcnow()) # Match starts are stored in UTC in database, therefore utcnow has to be used.
        fixtures_tostart = TippQuery(player_id=player.id, from_date=datetime.utcnow(), to_date=td+timedelta(days=includedays))
        fcnt = len(list(fixtures_started)) + len(list(fixtures_tostart))
        lu = UpdateSchedule.objects.all().first()

        ctx = {'fixtures_started' : fixtures_started, 'fixtures_tostart' : fixtures_tostart, 'fcnt' : fcnt, 'lupdate' : lu, 'days' : includedays-1}
        request.session['redirect_tipp'] = 'today'
        return render(request, 'game/today.html', ctx)

class TodayRefreshView(LoginRequiredMixin, View):
    def post(self, request):
        # Refresh Data on Today page via API
        update_fixtures(mode='live')
        returnto = request.POST.get('next', '/')
        return redirect(returnto)

class InfoFixtureView(LoginRequiredMixin, View):
    template = 'game/info_fixture.html'
    def get(self, request, game_id, fixture_id):
        player = Player.objects.all().filter(user__username = request.user).get()
        game = Game.objects.all().filter(id=game_id).get()
        fixture = Fixture.objects.all().filter(id=fixture_id).get()
        mytipp = Tipp.objects.all().filter(game_id = game_id, fixture_id = fixture_id, player_id = player.id)
        tipps = Tipp.objects.all().filter(game_id = game_id, fixture_id = fixture_id).exclude(player_id = player.id)
        lu = UpdateSchedule.objects.all().first()  
        ctx = {'game' : game, 'mytipp' : mytipp, 'tipps' : tipps, 'fixture' : fixture, 'lupdate' : lu}
        return render(request, self.template, ctx)


class TippCreateView(LoginRequiredMixin, View):
    # View to create tipps
    template = 'game/tipp.html'
    def get(self, request, game_id, fixture_id):
        game = Game.objects.all().filter(id=game_id)
        fixture = Fixture.objects.all().filter(id=fixture_id)
        form = TippForm()
        ctx = {'game' : game.first(), 'fixture' : fixture.first(), 'form' : form}

        return render(request, self.template, ctx)

    def post(self, request, game_id, fixture_id):
        fixture = Fixture.objects.all().filter(id=fixture_id).first()
        if fixture.match_start < make_aware(datetime.now()):
            messages.error(request, 'Tipps can not be captured if the match has already started!')
        else:
            form = TippForm(request.POST)

            newtipp = form.save(commit=False)
            newtipp.player = Player.objects.all().filter(user__username = request.user).get()
            newtipp.fixture_id = fixture_id
            newtipp.game_id = game_id
            newtipp.save()

            form.save()

        if 'redirect_tipp' in request.session:
            if request.session['redirect_tipp'] == 'today':
                del request.session['redirect_tipp']
                return redirect('today')
    
        return redirect('gamedetail', game_id)


class TippUpdateView(LoginRequiredMixin, View):
    # View to update tipps
    template = 'game/tipp.html'
    def get(self, request, tipp_id):
        player = Player.objects.all().filter(user__username = request.user).get()     
        tipp = get_object_or_404(Tipp, pk=tipp_id, player=player.id)
        
        if tipp.player_id != player.id: # actually this should no longar happen - this should result in a 404
            messages.error(request, 'You cannot change Tipps owned by a another player!')
            return render(request, 'games')
        
        else:
            form = TippForm(instance=tipp)
            game = Game.objects.all().filter(pk = tipp.game_id)    
            fixture = Fixture.objects.all().filter(pk = tipp.fixture_id)
            ctx = {'game' : game.first(), 'fixture' : fixture.first(), 'form' : form}
            return render(request, self.template, ctx)

    def post(self, request, tipp_id):
        player = Player.objects.all().filter(user__username = request.user).get()    
        tipp = get_object_or_404(Tipp, pk=tipp_id, player=player.id)
        fixture = Fixture.objects.all().filter(id=tipp.fixture_id).get()
        
        if fixture.match_start < make_aware(datetime.now()):
            messages.error(request, 'Tipps can not be captured if the match has already started!')
        else:
            form = TippForm(request.POST, instance=tipp)
            form.save()

        if 'redirect_tipp' in request.session:
            if request.session['redirect_tipp'] == 'today':
                del request.session['redirect_tipp']
                return redirect('today')
    
        return redirect('gamedetail', tipp.game_id)

# View to delete Tipps
class TippDeleteView(LoginRequiredMixin, View):
    def post(self, request, tipp_id):
        player = Player.objects.all().filter(user__username = request.user).get()    
        tipp = get_object_or_404(Tipp, pk=tipp_id, player=player.id)

        tipp.delete()

        if 'redirect_tipp' in request.session:
            if request.session['redirect_tipp'] == 'today':
                del request.session['redirect_tipp']
                return redirect('today')
    
        return redirect('gamedetail', tipp.game_id)



class RankingView(LoginRequiredMixin, View):
    # View to display the ranking page if selected from Navbar
    template = 'game/ranking.html'
    def get(self, request, pk):
        player = Player.objects.all().filter(user__username = request.user).get()
        game = Game.objects.all().filter(id=pk).get()
        rankings = Tipp.objects.all().filter(game_id = game.id).values('player_id', 'player__user__username').annotate(t_score = Sum('score'), t_total = Count('id'), 
            t_exact = Count('id', filter=Q(score = F('game__pts_exact'))), t_difference = Count('id', filter=Q(score = F('game__pts_difference'))),
            t_winner = Count('id', filter=Q(score = F('game__pts_winner'))), t_wrong = Count('id', filter=Q(score = F('game__pts_wrong')))).order_by('-t_score')
        tipps = Tipp.objects.all().filter(player=player)
        ctx = {'game' : game, 'rankings' : rankings}   
        return render(request, self.template, ctx)

class RankingDetailView(LoginRequiredMixin, View):
    template = 'game/ranking_detail.html'
    def get(self, request, game_id, player_id):
        player = Player.objects.all().filter(pk=player_id).get()
        game = Game.objects.all().filter(id=game_id).get()
        results = TippQuery(player_id=player_id, game_id=game_id, to_date=datetime.utcnow(), order='DESC') 
        ctx = {'game' : game, 'results' : results, 'player' : player}
        return render(request, self.template, ctx)

# Test Functions

# API Call in mode days
def TestDay(request):
    if request.method == 'POST':
        update_fixtures(mode='days')
        messages.success(request, 'Daily update of API Data completed')
        return redirect('test_api')
