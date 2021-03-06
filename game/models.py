from django.db import models
from django.contrib.auth.models import User 


class UpdateSchedule(models.Model):
    # Table with the last update dates for fixtures, etc.
    next_league_update = models.DateField()  # Date when the next update for leagues and teams should run
    next_fixture_update = models.DateField() # Date when the next scheduled update for fixtures should run
    last_fixture_update = models.DateTimeField() # Date and time when the fixtures were last updated from the API


class AvailableLeague(models.Model):
    # Table with api_ids of leagues are available to select in the prediction game
    api_id = models.IntegerField(unique=True)


class Country(models.Model):
    # Countries
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=5, null=True)
    flag = models.URLField(max_length=255, null=True)

    def __str__(self):
        return self.name


class League(models.Model):
    # Leagues
    api_id = models.IntegerField(unique = True)
    name = models.CharField(max_length=128)
    season = models.IntegerField(blank=True, null=True)
    season_start = models.DateField(blank=True, null=True)
    season_end = models.DateField(blank=True, null=True)
    is_current = models.BooleanField(default=False)
    logo = models.URLField(max_length=255, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    games = models.ManyToManyField('Game', through='Game_Leagues')  # Name of the object has to be used since the Game object has not been created yet

    def __str__(self):
        return self.name



class Team(models.Model):
    # Teams
    api_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=128)
    logo = models.URLField(max_length=255, null=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name



class Fixture(models.Model):
    # Fixtures
    api_id = models.IntegerField(unique = True)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    match_start = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=128, null=True)
    status_short = models.CharField(max_length=5, null=True)
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='hometeam')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='awayteam')
    home_goals = models.IntegerField(blank=True, null=True)
    away_goals = models.IntegerField(blank=True, null=True)
    home_odds = models.FloatField(blank=True, null=True)
    draw_odds = models.FloatField(blank=True, null=True)
    away_odds = models.FloatField(blank=True, null=True)



class Game(models.Model):
    # Games
    name = models.CharField(max_length=128, null=False)
    leagues = models.ManyToManyField(League, through='Game_Leagues')
    pts_exact = models.IntegerField(blank=False, null=False)
    pts_difference = models.IntegerField(blank=False, null=False)
    pts_winner = models.IntegerField(blank=False, null=False)
    pts_wrong = models.IntegerField(blank=False, null=False)
    creator = models.ForeignKey('Player', on_delete=models.CASCADE, related_name='creator')
    players = models.ManyToManyField('Player', through='Player_Games') # all players in the game

    def __str__(self):
        return self.name


class Invitation(models.Model):
    # Invitations to Games - actually not used currently
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    email = models.EmailField(max_length=255)

class Game_Leagues(models.Model):
    # Game_Leagues
    # This object/table is used to model the n:m relationship between Leagues and Games 
    # each Game can contain multiple Leagues and each League can be included in mulitple Games

    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)


class Player(models.Model):
    # Extend the standard users table to allow profile pictures, and the m:n relation to assign games to players
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    pic = models.URLField(max_length=255)
    games = models.ManyToManyField(Game, through='Player_Games')

    def __str__(self):
        return self.user.username  # This way the username is shown in the new game form


class PlayerStatus(models.Model):
    # Table for the differnt status of a player in a game Creator, Invited, Declined, Active
    name = models.CharField(max_length=20)


class Player_Games(models.Model):
    # Table used to model the n:m relationship between Games and Players
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    status = models.ForeignKey(PlayerStatus, on_delete=models.CASCADE, default=3)  # 3 is the id of the "invited" status


class Tipp(models.Model):
    # Tipps
    tipp_home = models.IntegerField(blank=False, null=False)
    tipp_away = models.IntegerField(blank=False, null=False)
    fixture = models.ForeignKey(Fixture, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    score = models.IntegerField(blank=True, null=True) # This field is used to keep the score of the tipp after a match has started or is finished
    yn_final = models.BooleanField(default=False) # This is set to True if a match is finished and therefore the score is final and does not change anymore



