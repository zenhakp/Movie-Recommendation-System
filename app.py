from flask import Flask, render_template, request, jsonify, url_for,redirect,session
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import json
from datetime import datetime
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

df_movies = pd.read_csv("tmdb_5000_movies.csv")
tfidf = TfidfVectorizer(stop_words="english")
df_movies['overview']=df_movies['overview'].fillna("")
df_movies = df_movies.fillna("")
tfidf_matrix = tfidf.fit_transform(df_movies['overview'])
cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
indices = pd.Series(df_movies.index, index=df_movies['original_title']).drop_duplicates()
df_movies['original_language'] = df_movies['original_language'].replace({'af': 'Afrikaans','ar':'Arabic','cn':'Chinese', 'cs':'Czech', 'da':'Danish', 'de':'German', 'el':'Greek', 'en':'English', 'es':'Spanish', 'fa':'Persian', 'fr':'French', 'he':'Hebrew', 'hi':'Hindi', 'hu':'Hungarian', 'id':'Indonesian', 'is':'Icelandic', 'it':'Italian', 'ja':'Japanese', 'ko':'Korean', 'ky':'Kyrgyz', 'nb':'Norwegian Bokmål', 'nl':'Dutch', 'no':'Norwegian', 'pl':'Polish', 'ps':'Pashto', 'pt':'Portuguese', 'ro':'Romanian', 'ru':'Russian', 'sl':'Slovenian', 'sv':'Swedish', 'ta':'Tamil', 'te':'Telugu', 'th':'Thai', 'tr':'Turkish', 'vi':'Vietnamese', 'xx':'No linguistic Content', 'zh':'Chinese'})
images =[]
for title in df_movies['original_title']:
    title = title.lower()
    title = "".join(char for char in title if char.isalnum())
    image_url = f"static/images/{title}.jpg"
    images.append(image_url)
df_movies['images'] = images
df_movies['reviews'] = [[] for _ in range(len(df_movies))]
sorted_df_movies = df_movies.sort_values(by='vote_average', ascending=False)

def get_recommendations(title,tot_movie_count,df_movies = df_movies, cosine_sim = cosine_sim):
    try:
      new_title = ""
      for idx, name in enumerate(df_movies["original_title"]):
        name = name.lower()
        name= "".join(char for char in name if char.isalnum())
        if title in name:
            new_title = df_movies["original_title"].iloc[idx]
            break
      if new_title:
        movies = []
        idx = indices[new_title]
        sim_scores = enumerate(cosine_sim[idx])
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[0:tot_movie_count]
        sim_index = [i[0] for i in sim_scores]
        for idx in sim_index:
          movies.append((df_movies["original_title"].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['id'].iloc[idx]))
        return movies
      else:
        return None
    except:
      return None
def format_datetime(date):
    datetime_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    time_diff = datetime.now() - datetime_obj
    if time_diff.days >= 365:
        years = int(time_diff.days / 365)
        formatted_str = f"{years} year{'' if years == 1 else 's'} ago"
    elif time_diff.days >= 30:
        months = int(time_diff.days / 30)
        formatted_str = f"{months} month{'' if months == 1 else 's'} ago"
    elif time_diff.days >= 7:
        weeks = int(time_diff.days / 7)
        formatted_str = f"{weeks} week{'' if weeks == 1 else 's'} ago"
    elif time_diff.days >= 1:
        formatted_str = f"{time_diff.days} day{'' if time_diff.days == 1 else 's'} ago"
    elif time_diff.seconds >= 3600:
        hours = int(time_diff.seconds / 3600)
        formatted_str = f"{hours} hour{'' if hours == 1 else 's'} ago"
    elif time_diff.seconds >= 60:
        minutes = int(time_diff.seconds / 60)
        formatted_str = f"{minutes} minute{'' if minutes == 1 else 's'} ago"
    elif time_diff.seconds > 0:
        formatted_str = f"{time_diff.seconds} second{'' if time_diff.seconds == 1 else 's'} ago"
    else:
        formatted_str = "just now"
    original_datetime_str = datetime_obj.strftime("%d %B %Y")
    return formatted_str, original_datetime_str
def movie_review(movie_id):
    review=[]
    for idx,id in enumerate(df_movies["id"]):
        if movie_id == id:
            for i in df_movies["reviews"].iloc[idx]:
                formatted_str, original_datetime = format_datetime(i[2])
                review.append((i[0],i[1],formatted_str, original_datetime))
    return review

app = Flask(__name__)
app.config['SECRET_KEY'] = 'flickfix339'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80))
    email = db.Column(db.String(120))

    phone_no = db.Column(db.String(15))
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(128))

    def __init__(self, name, email, phone_no, username, password):
        self.name = name
        self.email = email
        self.phone_no = phone_no
        self.username = username
        self.password = password
    def check_password(self, password):
        from werkzeug.security import check_password_hash 
        return check_password_hash(self.password, password)
def create_tables():
    with app.app_context():
        db.create_all()


create_tables()

@app.route('/')
def main():
  return render_template('mainpage.html')
@app.route('/login',methods =['POST','GET'])
def login():
   if request.method == 'POST':
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
      session['user_id'] = user.id
      return redirect(url_for('home'))
    else:
      return render_template('login.html', message="*Invalid username or password*")
   else:
    return render_template('login.html')

     
      
@app.route('/signup',methods = ['POST','GET'])
def signup():
  if request.method == 'POST':
    name = request.form['name']
    email = request.form['email']
    phoneno = request.form['number']
    username = request.form['username']
    password = request.form['password']
    hashed_password = generate_password_hash(password)
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return render_template('signup.html',message="*Username already exists*")
    user = User(name, email, phoneno, username, hashed_password)
    try:
      db.session.add(user)
      db.session.commit()
      return redirect(url_for('login')) 
    except Exception as e:
      print(e)
      return render_template('signup.html', message="*An error occurred*")
  else:
    return render_template('signup.html')
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/home',methods=['GET'])
def home():
  if request.method == 'GET':
     current_user = User.query.get(session['user_id'])
     accounts = User.query.filter_by(email=current_user.email).all()
     return render_template('home_page.html',accounts = accounts)
  else:
     return render_template('home_page.html')

@app.route('/profile')
def profile():
  current_user = User.query.get(session['user_id'])
  accounts = User.query.filter_by(email=current_user.email).all()
  return render_template('home_page.html', accounts=accounts)

@app.route('/search', methods=['POST','GET'])
def search():
  tot_movie_list = df_movies['original_title'].to_list()
  tot_movie_count = len(tot_movie_list)
  start = 0
  end = 10
  title = request.form.get('search', '')
  title1 = title.lower()
  title1 = "".join(char for char in title1 if char.isalnum())
  movies = get_recommendations(title1,tot_movie_count)
  if movies:
    return render_template("search_results.html",title = title,movies = movies ,start = start,end = end,length = tot_movie_count)
  else:
    return render_template("search_results.html",title = title,movies = movies)
@app.route('/loadmoresearch',methods=['POST','GET'])
def loadmoresearch():
  tot_movie_list = df_movies['original_title'].to_list()
  tot_movie_count = len(tot_movie_list)
  start = int(request.form['start'])
  end = int(request.form['end'])
  title = request.form.get('search', '')
  title1 = title.lower()
  title1 = "".join(char for char in title1 if char.isalnum())
  end = end + 5
  movies = get_recommendations(title1,tot_movie_count)
  if movies:
    return render_template("search_results.html",title = title,movies = movies ,start = start,end = end,length = tot_movie_count)
  else:
    return render_template("search_results.html",title = title,movies = movies)

@app.route('/language',methods=['POST','GET'])
def language():
  df_movies = sorted_df_movies
  lang = request.form.get('search', '')
  lang = lang.lower()
  movies = []
  start = 0
  end = 10
  for idx, language in enumerate(df_movies["original_language"]):
     if lang == language.lower():
        movies.append((df_movies["original_title"].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['id'].iloc[idx]))
  if movies:
     length = len(movies)
     return render_template("language.html",language = lang,movies = movies ,start = start,end = end,length = length)
  else:
     movies = None
     return render_template("language.html",language = lang,movies = movies)
@app.route('/loadmorelanguage',methods=['POST','GET'])
def loadmorelanguage():
  df_movies = sorted_df_movies
  start = int(request.form['start'])
  end = int(request.form['end'])
  lang = request.form.get('search', '')
  movies = []
  end = end + 5
  for idx, language in enumerate(df_movies["original_language"]):
     if lang == language.lower():
        movies.append((df_movies["original_title"].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['id'].iloc[idx]))
  if movies:
     length = len(movies)
     return render_template("language.html",language = lang,movies = movies ,start = start,end = end,length = length)
  else:
     movies = None
     return render_template("language.html",language = lang,movies = movies)
@app.route('/genre',methods=['POST','GET'])
def genre():
  df_movies = sorted_df_movies
  genre = request.form.get('search', '')
  genre = genre.lower()
  movies = []
  start = 0
  end = 10
  flag = 0
  for idx, row_genres in enumerate(df_movies["genres"]):
    genres = [genre_dict["name"].lower() for genre_dict in json.loads(row_genres)]  # Flatten and lowercase genres
    if genre in genres:
      flag = 1
      movies.append((df_movies["original_title"].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['id'].iloc[idx]))
  if flag==1:
    length = len(movies)
    return render_template("genre.html",genre = genre,movies = movies ,start = start,end = end,length = length)
  else:
    movies = None
    return render_template("genre.html",genre = genre,movies = movies)
@app.route('/loadmoregenre',methods=['POST','GET'])
def loadmoregenre():
  df_movies = sorted_df_movies
  start = int(request.form['start'])
  end = int(request.form['end'])
  genre = request.form.get('search', '')
  end = end + 5
  flag = 0
  movies = []
  for idx, row_genres in enumerate(df_movies["genres"]):
    genres = [genre_dict["name"].lower() for genre_dict in json.loads(row_genres)]  # Flatten and lowercase genres
    if genre in genres:
      flag = 1
      movies.append((df_movies["original_title"].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['id'].iloc[idx]))
  if flag==1:
    length = len(movies)
    return render_template("genre.html",genre = genre,movies = movies ,start = start,end = end,length = length)
  else:
    movies = None
    return render_template("genre.html",genre = genre,movies = movies)
@app.route('/popular')
def popular():
  df_movies = sorted_df_movies
  start = 0
  end = 10
  movies = []
  for idx,row in df_movies.iterrows():
    if row["vote_average"] >= 7:
      movies.append((df_movies['original_title'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['images'].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['id'].iloc[idx]))
  if movies:
    length = len(movies)
    return render_template("popular.html",movies = movies ,start = start,end = end,length = length)
  else:
    return render_template("popular.html",movies = movies)
@app.route('/loadmorepopular',methods=['POST','GET'])
def loadmorepopular():
  df_movies = sorted_df_movies
  start = int(request.form['start'])
  end = int(request.form['end'])
  end = end + 5
  movies = []
  for idx,row in df_movies.iterrows():
    if row["vote_average"] >= 7:
      movies.append((df_movies['original_title'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies['images'].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['id'].iloc[idx]))
  if movies:
    length = len(movies)
    return render_template("popular.html",movies = movies ,start = start,end = end,length = length)
  else:
    return render_template("popular.html",movies = movies ,start = start,end = end)

@app.route('/recent')
def recent():
  start = 0
  end = 10
  movies = []
  sorted_movies = df_movies.sort_values(by='release_date', ascending=False)
  for idx,row in sorted_movies.iterrows():
    movies.append((df_movies['original_title'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['id'].iloc[idx]))
  return render_template("recent.html",movies = movies,start = start,end = end)
@app.route('/loadmorerecent',methods=['POST','GET'])
def loadmorerecent():
  start = int(request.form['start'])
  end = int(request.form['end'])
  end = end + 5
  movies = []
  sorted_movies = df_movies.sort_values(by='release_date', ascending=False)
  for idx,row in sorted_movies.iterrows():
    movies.append((df_movies['original_title'].iloc[idx],df_movies['vote_average'].iloc[idx],df_movies["images"].iloc[idx],df_movies['tagline'].iloc[idx],df_movies['id'].iloc[idx]))
  return render_template("recent.html",movies = movies,start = start,end = end)
@app.route('/movie/<int:movie_id>',methods=['POST','GET'])
def movie(movie_id):
  if request.method == "POST":
     search = request.form.get('search', '')
     start = int(request.form['start'])
     end = int(request.form['end'])
     movie=[]
     for idx,row in df_movies.iterrows():
      if movie_id == row["id"]:
         genre= [genre_dict["name"].lower() for genre_dict in json.loads(row["genres"])]
         reviews = movie_review(movie_id)
         reviews = sorted(reviews, key=lambda x: x[2], reverse=True)
         movie.extend([row["original_title"],row["images"],row["overview"],genre,row["release_date"],row["vote_average"],row["homepage"],row["original_language"],row["id"],reviews])
         return render_template("movie.html",movie = movie,search = search,start = start,end = end,movie_referrer =request.referrer )
  else:
     movie_referrer = request.args.get('movie_referrer','')
     search = request.args.get('search', '')
     start = int(request.args.get('start', 0))
     end = int(request.args.get('end', 10))
     movie=[]
     for idx,row in df_movies.iterrows():
      if movie_id == row["id"]:
         genre= [genre_dict["name"].lower() for genre_dict in json.loads(row["genres"])]
         reviews = movie_review(movie_id)
         reviews = sorted(reviews, key=lambda x: x[2], reverse=True)
         movie.extend([row["original_title"],row["images"],row["overview"],genre,row["release_date"],row["vote_average"],row["homepage"],row["original_language"],row["id"],reviews])
         return render_template("movie.html",movie = movie,search = search,start = start,end = end , movie_referrer=movie_referrer)
     
@app.route('/reviews', methods=['POST'])
def reviews():
   movie_referrer = request.form['movie_referrer']
   search = request.form.get('search', '')
   start = int(request.form['start'])
   end = int(request.form['end'])
   review_content = request.form['content']
   author = request.form['author']
   movie_id = int(request.form['id'])
   time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
   for idx,id in enumerate(df_movies["id"]):
      if movie_id == id:
         review = df_movies["reviews"].iloc[idx]
         review.append((author,review_content,time))
         return redirect(url_for('movie', movie_id=movie_id, search=search, start=start, end=end, movie_referrer=movie_referrer))
if __name__ == '__main__':
  app.run(debug=True)

