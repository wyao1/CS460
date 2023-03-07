DROP DATABASE photoshare;
CREATE DATABASE IF NOT EXISTS photoshare;
USE photoshare;

CREATE TABLE Users (
 user_id int4 AUTO_INCREMENT,
 firstname varchar(255) NOT NULL,
 lastname varchar(255) NOT NULL, 
 DOB date NOT NULL,
 gender enum ('female', 'male'),
 hometown varchar(255),
 email varchar(255) UNIQUE NOT NULL,
 password varchar(255) NOT NULL,
 CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Albums
(
 album_id int4 auto_increment,
 title varchar(255),
 date_created DATE,
 user_id int4,
 constraint albums_pk primary key (album_id),
 foreign key (user_id) references Users(user_id)
);

CREATE TABLE Pictures
(
 picture_id int4 AUTO_INCREMENT,
 user_id int4,
 imgdata longblob,
 caption VARCHAR(255),
 INDEX upid_idx (user_id),
 album int4,
 CONSTRAINT pictures_pk PRIMARY KEY (picture_id),
 foreign key (album) references Albums(album_id)
);

CREATE TABLE Friends
(
 user_id int4,
 friend_id int4,
 constraint friends_fk1 foreign key (user_id) references
Users(user_id),
 constraint friends_fk2 foreign key (friend_id) references
Users(user_id)
);

CREATE TABLE Tags
(
 singleword varchar(55),
 photo_id int4,
 constraint tags_fk foreign key(photo_id) references Pictures(photo_id)
);

CREATE TABLE Comments
(
 comment_id int4 auto_increment,
 comment_text text,
 user_id int4, 
 date_created DATE,
 photo_id int4, 
 constraint comments_pk primary key (comment_id), 
 constraint comments_fk1 foreign key (user_id) references Users(user_id),
 constraint comments_fk2 foreign key (photo_id) references Photos(photo_id)
);

CREATE TABLE Likes 
(
	photo_id int4,
    user_id int4,
    constraint likes_fk foreign key (pictures_id) references Pictures(picture_id),
    constraint likes_user_id_fk foreign key (user_id) references Users(user_id)
    );

INSERT INTO Users (email, password) VALUES ('test@bu.edu', 'test');
INSERT INTO Users (email, password) VALUES ('test1@bu.edu', 'test');
DROP TABLE IF EXISTS Users CASCADE 