import os
from datamodels import UserInDb
from fastapi import HTTPException
from mysql import connector as sql
from mysql.connector import errorcode

TABLES = {}

TABLES[
    "user"
] = """CREATE TABLE `user`(
`user_id`    INT(11) NOT NULL AUTO_INCREMENT,
`username`       VARCHAR(20) NOT NULL UNIQUE,
`password`   TEXT NOT NULL,
`dob`        DATE    NOT NULL,
`disabled`   BOOLEAN NOT NULL DEFAULT FALSE,
PRIMARY KEY (`user_id`)
) ENGINE=InnoDB"""

TABLES[
    "post"
] = """CREATE TABLE `post`(
`post_id`    INT(11) NOT NULL AUTO_INCREMENT,
`title`      TEXT NOT NULL,
`user_id`    INT(11) NOT NULL,
`created_on` DATETIME NOT NULL,
PRIMARY KEY (`post_id`),
FOREIGN KEY(`user_id`) REFERENCES user(`user_id`)
) ENGINE=InnoDB"""

TABLES[
    "comment"
] = """CREATE TABLE `comment`(
`comment_id` INT(11) NOT NULL AUTO_INCREMENT,
`user_id`    INT(11) NOT NULL,
`post_id`    INT(11) NOT NULL,
`comment`    TEXT NOT NULL,
`commented_on` DATETIME NOT NULL,
PRIMARY KEY(`comment_id`),
FOREIGN KEY(`user_id`) REFERENCES user(`user_id`),
FOREIGN KEY(`post_id`) REFERENCES post(`post_id`)
) ENGINE=InnoDB"""


DB_NAME = "DUMMY"


def create_db(cursor) -> None:
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    except sql.Error as err:
        print(f"Failed creating database: {err}")
        exit(1)


def init_db(cnx):
    cursor = cnx.cursor()
    try:
        cursor.execute(f"USE {DB_NAME}")
    except sql.Error as err:
        print(f"Database {DB_NAME} does not exists.")
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            create_db(cursor)
            print(f"Database {DB_NAME} created successfully!")
            cnx.database = DB_NAME
        else:
            print(err)
            exit(1)
    for table_name in TABLES:
        table_description = TABLES[table_name]
        try:
            print("Creating table {}: ".format(table_name), end="")
            cursor.execute(table_description)
        except sql.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")
    cursor.close()


cnx = sql.connect(
    host="localhost",
    user=os.environ.get("MYSQL_USER"),
    password=os.environ.get("MYSQL_PASSWORD"),
)


def fetch_user(username: str) -> UserInDb:
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT username, dob, password, disabled FROM user WHERE username=%s",
        (username,),
    )
    for username, dob, password, disabled in cursor:
        return UserInDb(
            username=username, hashed_password=password, dob=dob, disabled=disabled
        )
    raise HTTPException(status_code=404, detail="User not found!")
