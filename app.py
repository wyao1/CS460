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
app.config['MYSQL_DATABASE_PASSWORD'] = 'wy#3HACHI251974'
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
	return render_template('profile.html', name=flask_login.current_user.id, uid = getUserIdFromEmail(flask_login.current_user.id), message="Here's your profile")

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

		album = request.form.get ('album')
		if(isAlbumUnique(album, uid)): #true = creating new album
			CreateAlbum(album, current_datetime, uid)
		albumID = FindAlbumID(album, uid)

		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption, album) VALUES (%s, %s, %s, %s )''', (photo_data, uid, caption, albumID))
		conn.commit()
		picture_id = cursor.lastrowid

		tags=str(request.form.get('tags')).lower().split(" ")
		
		addTag(tags, picture_id)

		#checking if inserted correctly
		cursor.execute("SELECT singleword FROM Tags WHERE picture_id = '{0}'".format(picture_id))
		conn.commit()
		tags2 = cursor.fetchall()
		print(tags2)
		

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

def getallpicturesfromalbum(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE album = '{0}'".format(album_id))
    return cursor.fetchall()

#delete picture
@app.route('/deletepicture/<uid>/<picture_id>')
def deletepicture(uid, picture_id):
	tags = getUserTags(uid)
	for tag in tags:
		deleteTags(str(tag[0]), picture_id)
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Likes WHERE picture_id='{0}'".format(picture_id))
	conn.commit()
	cursor.execute("DELETE FROM Comments WHERE picture_id='{0}'".format(picture_id))
	conn.commit()
	cursor.execute("DELETE FROM Pictures WHERE user_id = '{0}' AND picture_id='{1}'".format(uid, picture_id))
	conn.commit()
	return render_template('hello.html', name=flask_login.current_user.id, message='Photo deleted!', base64=base64)

#browse pictures
@app.route('/browsepictures')
def browsepictures():
	if flask_login.current_user.is_authenticated:   		
		name = getUserIdFromEmail(flask_login.current_user.id)
	else:
		name = -1
	return  render_template('browsepictures.html', name = name, allphotos=getallpictures(), base64=base64)
#end photo uploading code

@app.route('/comment/<picture_id>', methods=['GET', 'POST'])
@flask_login.login_required
def comment(picture_id):
	if flask_login.current_user.is_authenticated:   		
		name = getUserIdFromEmail(flask_login.current_user.id)
	else:
		name = -1
	if request.method == 'POST':
			comment=request.form.get('comment')
			insertComment(comment, picture_id)
			print(comment)
	return render_template('picturedetail.html', comments = GetComments(picture_id), tags = getTagsofPicture(picture_id), name=name, photo=getpicturedetail(picture_id), base64=base64)

#gets picture details except comments and tags
def getpicturedetail(photo):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, user_id, picture_id, caption, album FROM pictures WHERE picture_id = '{0}'".format(photo))
	photo_details = cursor.fetchone()

	#gets album name
	cursor.execute("SELECT title FROM Albums WHERE album_id = '{0}'".format(photo_details[4]))
	album_title = cursor.fetchone()

	#gets name
	cursor.execute("SELECT firstname, lastname FROM Users WHERE user_id = '{0}'".format(photo_details[1]))
	name = cursor.fetchone()

	numlikes = NumberofLikes(photo)

	return photo_details + album_title + name + numlikes


#picture details
@app.route('/picturedetail/<photo>') 
def picturedetail(photo):
	if flask_login.current_user.is_authenticated:   		
		name = getUserIdFromEmail(flask_login.current_user.id)
	else:
		name = -1
	return render_template('picturedetail.html',  comments = GetComments(photo), tags = getTagsofPicture(photo), name=name, photo=getpicturedetail(photo), base64=base64)

#liking a photo
@app.route('/like/<photo>', methods=['GET','POST']) 
@flask_login.login_required
def like(photo):
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'GET':
		cursor = conn.cursor()
		cursor.execute("INSERT INTO Likes (picture_id, user_id) VALUES ('{0}', '{1}')".format(photo, uid))
		return render_template('picturedetail.html',  comments = GetComments(photo), message = "Liked the picture!", photo=getpicturedetail(photo), base64=base64)

@app.route('/mypictures') 
@flask_login.login_required
def mypictures():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	return render_template('browsepictures.html', photos = getUsersPhotos(uid), base64=base64)


@app.route('/myalbums/<uid>')
@flask_login.login_required
def myalbums(uid):
	albums = getAllAlbumsofUser(uid)
	return render_template('browsealbums.html', myalbums = getFirstPic(albums), base64=base64)


@app.route('/browsealbums')
@flask_login.login_required
def browsealbums():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    return render_template('browsealbums.html', allalbums = getFirstPic(getAllAlbums()), base64=base64)

@app.route('/viewalbum/<albumid>,<title>')
@flask_login.login_required
def viewalbum(albumid,title):
	if flask_login.current_user.is_authenticated:
		user_id = getUserIdFromEmail(flask_login.current_user.id)
	else:
		user_id = -1
	pictures = getallpicturesfromalbum(albumid)
	return render_template('viewalbum.html', albumid = albumid, pictures = pictures, title = title, uid = user_id, base64=base64)

#deletealbum also makes use of deletepicture
@app.route('/deletealbum/<albumid>')
def deletealbum(albumid):
    # Delete all pictures in the album
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT picture_id FROM Pictures WHERE album = %s", (albumid))
	picture_ids = [r[0] for r in cursor.fetchall()]
	for picture_id in picture_ids:
		deletepicture(user_id, picture_id)
		
	cursor.execute("DELETE FROM Albums WHERE album_id = %s", (albumid))
	conn.commit()
	return render_template('hello.html', name=flask_login.current_user.id, message='Album deleted!', base64=base64)

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
	
def getUsersAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Albums WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getAllAlbumsofUser(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT album_id FROM Albums WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall()

def getAllAlbums():
	cursor = conn.cursor()
	cursor.execute("SELECT album_id FROM Albums")
	return cursor.fetchall()



#gets a list of tuples of albumID and first picture along with album title and imgdata
#(album_ID, title, picture_ID, imgdata)
def getFirstPic(albums):
    cursor = conn.cursor()
    allalbums = []
    for album in albums:
        cursor.execute("SELECT album_id, title, picture_id, imgdata FROM Pictures JOIN Albums ON Pictures.album = Albums.album_id WHERE album_id = %s LIMIT 1", album)
        result = cursor.fetchone()
        if result:
            allalbums.append(result)
    return allalbums

#returns the number of likes on a picture
def NumberofLikes(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(picture_id) FROM Likes WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchone()



@app.route("/tags/<singleword>")
@flask_login.login_required
def tags(singleword):
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	pictures = getallpictureswithtag(str(singleword))
	return render_template('tag.html', pictures=pictures, singleword=singleword, base64=base64)

#checks if tag already exists
def isTagUnique(tag, picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Tags WHERE singleword = '{0}' And picture_id = '{1}'".format(tag, picture_id))
	if cursor.fetchone():
		return False
	else:
		return True
	
def addTag(listoftags, picture_id):
	for t in list(set(listoftags)):
		if t != "" and isTagUnique(t, picture_id):
			cursor = conn.cursor()
			cursor.execute("INSERT INTO Tags (singleword, picture_id) VALUES ('{0}', '{1}')".format(t, picture_id))
			conn.commit()
		   
def getallpictureswithtag(singleword):
    cursor = conn.cursor()
    cursor.execute("SELECT picture_id FROM Tags WHERE singleword = '{0}'".format(singleword))
    P = cursor.fetchall()
    picture_ids = [(int(item[0])) for item in P]
    pictures = []
    for picture_id in picture_ids:
        cursor.execute("SELECT imgdata FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
        R = cursor.fetchall()
        C = [item[0] for item in R]
        if C:
            pictures.append((picture_id, C[0]))
    return pictures


def getTagsofPicture(picture_id):
	cursor.execute("SELECT singleword FROM Tags WHERE picture_id = '{0}'".format(picture_id))
	conn.commit()
	tags = cursor.fetchall()
	return tags

def getUserTags(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT T.singleword FROM Tags T, Pictures P WHERE P.user_id='{0}' AND T.picture_id = P.picture_id".format(uid))
	tags = cursor.fetchall()
	return list(set(tags))

def deleteTags(tag, picture_id):
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Tags WHERE singleword = '{0}' AND picture_id='{1}'".format(tag, picture_id))
	conn.commit()


def isCommentUnique(uid, picture_id):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Pictures WHERE user_id = '{0}' AND picture_id='{1}'".format(uid, picture_id)):
		return False
	else:
		return True

def insertComment(comment, picture_id):
	if flask_login.current_user.is_authenticated:
		user_id = getUserIdFromEmail(flask_login.current_user.id)
	else:
		user_id = -1
	date_created= current_datetime = str(datetime.datetime.now().year) + "-" + str(datetime.datetime.now().month) + "-" + str(datetime.datetime.now().day)
	cursor = conn.cursor()
	cursor.execute("INSERT INTO Comments(comment_text, user_id, date_created, picture_id) VALUES (%s, %s, %s, %s)", (comment, user_id, date_created, picture_id))
	conn.commit()

def GetComments(picture_id):
	if flask_login.current_user.is_authenticated:
		uid = getUserIdFromEmail(flask_login.current_user.id)
	else:
		uid = -1
	cursor = conn.cursor()
	cursor.execute("SELECT C.comment_text, C.picture_id, U.firstname, U.lastname FROM Comments C, Users U, Pictures P WHERE C.picture_id = '{0}' AND C.picture_id = P.picture_id AND C.user_id = U.user_id".format(picture_id))
	commentlist = [[comment[0], comment[1], comment[2], comment[3]] for comment in cursor.fetchall()]
	return commentlist

def getContribution():
    cursor = conn.cursor()
    contribution = """
        SELECT U.email, U.firstname, U.lastname, 
        COUNT(DISTINCT P.picture_id) + COUNT(DISTINCT C.comment_id) as contribution
        FROM Users U
        LEFT JOIN Pictures P ON P.user_id = U.user_id
        LEFT JOIN Comments C ON C.user_id = U.user_id AND C.picture_id NOT IN (SELECT picture_id FROM Pictures WHERE user_id = U.user_id)
        WHERE U.user_id != -1
        GROUP BY U.user_id
        ORDER BY contribution DESC
        LIMIT 10
    """
    cursor.execute(contribution)
    return cursor.fetchall()
#default page
@app.route("/", methods=['GET'])
def hello():
	if flask_login.current_user.is_authenticated:
		uid = getUserIdFromEmail(flask_login.current_user.id)
	else:
		uid = -1
	return render_template('hello.html', uid = uid, message='Welcome to Photoshare', TopUsers=getContribution())


@app.route('/recommendphotos', methods=['GET', 'POST'])
@flask_login.login_required
def recommendPhotos():
	uid=getUserIdFromEmail(flask_login.current_user.id)
	return render_template('recommendPhotos.html')



if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)