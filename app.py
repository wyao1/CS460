######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login
import datetime

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'CS460'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost' 
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   	<h1> LOG IN </h1>
      			<form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
				 or <a href='/register'>make an account</a>
		   <p><a href='/'>Home</a></p>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		firstname = request.form.get('firstname')
		lastname = request.form.get('lastname')
		DOB = request.form.get('DOB')
		hometown = request.form.get('hometown')
		gender = request.form.get('gender')
		inputemail = request.form.get('email')
		password = request.form.get('password')

	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(inputemail)
	
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, firstName, lastName, hometown, gender, DOB) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(inputemail, password, firstname, lastname, hometown, gender, DOB)))
		conn.commit()
		#log user in
		user = User()
		user.id = inputemail
		flask_login.login_user(user)
		return render_template('hello.html', name = inputemail, message='Account Created!')
	else:
		print("couldn't find all tokens")
		return "<a href='/register'>Try again, email already in use</a>"

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('profile.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')

		current_datetime = str(datetime.datetime.now().year) + "-" + str(datetime.datetime.now().month) + "-" + str(datetime.datetime.now().day)
		print(current_datetime)

		album = request.form.get ('album')
		if(isAlbumUnique(album, uid)): #true = creating new album
			CreateAlbum(album, current_datetime, uid)
		albumID = FindAlbumID(album, uid)
		print("ALBUM ID IS " + str(albumID))

		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption, album) VALUES (%s, %s, %s, %s )''', (photo_data, uid, caption, albumID))
		conn.commit()
		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

#gets all the pictures from database
def getallpictures():
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures")
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]


#delete picture
@app.route('/deletepicture/<uid>/<picture_id>', methods=['GET', 'POST'])
def deletepicture(uid, picture_id):
	tags = getUserTags(uid)
	for tag in tags:
		deleteTags(str(tag[0]), picture_id)
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Likes WHERE photo_id='{0}'".format(photo_id))
	conn.commit()
	cursor.execute("DELETE FROM Comments WHERE photo_id='{0}'".format(photo_id))
	conn.commit()
	cursor.execute("DELETE FROM Photos WHERE user_id = '{0}' AND photo_id='{1}'".format(uid, photo_id))
	conn.commit()


#browse pictures
@app.route('/browsepictures', methods=['GET', 'POST'])
def browsepictures():
	return  render_template('browsepictures.html', name=flask_login.current_user.id, allphotos=getallpictures(), base64=base64)
#end photo uploading code

def getpicturedetail(photo):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, user_id, picture_id, caption, album FROM pictures WHERE picture_id = '{0}'".format(photo))
	photo_details = cursor.fetchone()
	print(photo)
	print(photo_details[4])

	#gets album name
	cursor.execute("SELECT title FROM Albums WHERE album_id = '{0}'".format(photo_details[4]))
	album_title = cursor.fetchone()

	#gets name
	cursor.execute("SELECT firstname, lastname FROM Users WHERE user_id = '{0}'".format(photo_details[1]))
	name = cursor.fetchone()

	numlikes = NumberofLikes(photo)

	#gets tags
	cursor.execute("SELECT T.singleword FROM Tags T, Pictures P WHERE P.user_id='{0}' AND T.picture_id = P.picture_id".format(photo_details[1]))
	tags = cursor.fetchall()
	print(tags)
	return photo_details + album_title + name + numlikes + tags


#picture details
@app.route('/picturedetail/<photo>', methods=['GET','POST']) 
def picturedetail(photo):
    return render_template('picturedetail.html', name=getUserIdFromEmail(flask_login.current_user.id), photo=getpicturedetail(photo), base64=base64)

#liking a photo
@app.route('/like/<photo>', methods=['GET','POST']) 
@flask_login.login_required
def like(photo):
	print("PHOTO ID IS")
	print(photo)
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'GET':
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Likes (picture_id, user_id) VALUES ('{0}', '{1}')".format(photo, uid))
		return render_template('picturedetail.html', message = "Liked the picture!", photo=getpicturedetail(photo), base64=base64)



def isAlbumUnique(title, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Albums WHERE title = '{0}' And user_id = '{1}'".format(title, uid)):
		return False
	else:
		return True

#gets lift of Albums, to be used for upload, etc
def ListAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT title, date_creation, album_id FROM Albums WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()

def CreateAlbum(title, date_creation, uid):
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Albums (title, date_created, user_id) VALUES ('{0}', '{1}', '{2}')".format(title, date_creation, uid))
	conn.commit()

def CheckAlbumExist(uid):
	#if there exists an album for UID then true
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Albums WHERE user_id = '{0}'".format(uid)):
		return True
	else:
		return False

def FindAlbumID(album, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT album_id FROM Albums WHERE user_id = '{0}' AND title = '{1}'".format(uid, album))
	return cursor.fetchone()
	


#returns the number of likes on a picture
def NumberofLikes(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(picture_id) FROM Likes WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchone()



#checks if tag already exists
def isTagUnique(tag, picture_id):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Tags WHERE singleword = '{0}' And user_id = '{1}'".format(tag, uid)):
		return False
	else:
		return True

def addTag(listoftags, picture_id):
	for tag in list(set(listoftags)):
		if t != "" and isTagUnique(tag, picture_id):	
			cursor = conn.cursor()
			cursor.execute("INSERT INTO Tags (singleword, picture_id) VALUES ('{0}', '{1}')".format(tag, picture_id))
			conn.commit()
	
def getUserTags(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT T.word FROM Tags T, Photos P WHERE P.user_id='{0}' AND T.photo_id = P.photo_id".format(uid))
	tags = cursor.fetchall()
	return list(set(tags))

def deleteTags(tag, picture_id):
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Tags WHERE word = '{0}' AND photo_id='{1}'".format(tag, picture_id))
	conn.commit()


#default page
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)