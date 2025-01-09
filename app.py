# CRUD API for users to input an image and add the comments on the image
from typing import Annotated
from datetime import timedelta
from database import init_db, cnx
from mysql import connector as sql
from contextlib import asynccontextmanager
from fastapi.security import OAuth2PasswordRequestForm
from datamodels import User, Token, UserInfo, Post, Comment
from fastapi import FastAPI, HTTPException, Depends, status
from authenticate import authenticate_user, create_access_token
from authenticate import hash_password, get_current_active_user

ACCESS_TOKEN_EXPIRE_MINUTES = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("starting app...")
    init_db(cnx)
    yield
    print("shutting app down...")


app = FastAPI(lifespan=lifespan)


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/")
async def index():
    return {"msg": "Hello, World!"}


@app.get("/users/me", response_model=User)
async def get_user(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user


@app.get("/comments")
async def get_user_comments(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    cursor = cnx.cursor()
    cursor.execute(
        f"SELECT username, comment, title FROM user U JOIN comment C ON U.user_id=C.user_id JOIN post P ON C.post_id=P.post_id WHERE U.username={current_user.username}"
    )
    username = current_user.username
    comments = []
    for username, comment, title in cursor:
        comments.append({"comment": comment, "on": title})
    if not comments:
        return {"msg": "No comments yet!"}
    return {"username": username, "comments": comments}


@app.get("/posts")
async def get_user_posts(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT post_id, title FROM post NATURAL JOIN user WHERE username=%s",
        (current_user.username,),
    )
    posts = []
    for post in cursor:
        posts.append({"post_id": post[0], "post_title": post[1]})
    if not posts:
        return {"msg": "No posts yet!"}
    return {"username": current_user.username, "posts": posts}


@app.post("/users")
async def create_user(user: UserInfo):
    try:
        cursor = cnx.cursor()
        cursor.execute(
            "INSERT INTO user(username, dob, password) VALUES (%s, %s, %s)",
            (user.username, user.dob, hash_password(user.password)),
        )
        cnx.commit()
        return {"msg": "User created successfully!"}
    except sql.Error as err:
        print(f"Failed inserting user: {err}")
        raise HTTPException(status_code=409, detail="Username already taken!")


@app.put("/users/me")
async def update_current_user(
    current_user: Annotated[User, Depends(get_current_active_user)], user_info: UserInfo
):
    cursor = cnx.cursor()
    cursor.execute(
        "UPDATE user SET dob=%s, password=%s WHERE username=%s",
        (user_info.dob, hash_password(user_info.password), current_user.username),
    )
    cnx.commit()
    return {"msg": "User updated."}


@app.delete("/users/me")
async def delete_user(current_user: Annotated[User, Depends(get_current_active_user)]):
    cursor = cnx.cursor()
    cursor.execute(f"DELETE FROM user WHERE username={current_user.username}")
    cnx.commit()
    return {"msg": "User deleted."}


@app.get("/posts/{post_id}/comments")
async def get_post_comments(post_id: int):
    cursor = cnx.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM post WHERE post_id={post_id}")
    for (count,) in cursor:
        if count < 1:
            cursor.close()
            raise HTTPException(status_code=404, detail="Post not found!")
    cursor.execute(
        f"SELECT title, comment, username FROM user U JOIN comment C ON U.user_id=C.user_id JOIN post P ON C.post_id=P.post_id WHERE P.post_id={post_id}"
    )
    comments = []
    title = None
    for title, comment, username in cursor:
        comments.append({"comment": comment, "by": username})
    if title is None:
        return {"msg": "No comments yet!"}
    return {
        "title": title,
        "comments": comments,
    }


@app.post("/posts")
async def create_post(
    current_user: Annotated[User, Depends(get_current_active_user)], post: Post
):
    cursor = cnx.cursor()
    try:
        cursor.execute(
            "INSERT INTO post(title, user_id, created_on) SELECT %s, user_id, %s FROM user WHERE username=%s",
            (post.title, post.created_on, current_user.username),
        )
        cnx.commit()
        return {"msg": "Post created successfully!"}
    except sql.Error as err:
        print(f"Failed to create post: {err}")
        raise HTTPException(status_code=409, detail="Failed to create post!")


@app.put("/posts/{post_id}")
async def update_post(
    current_user: Annotated[User, Depends(get_current_active_user)],
    post_id: int,
    post: Post,
):
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM post NATURAL JOIN user WHERE post_id=%s AND username=%s",
        (post_id, current_user.username),
    )
    for (count,) in cursor:
        if count < 1:
            cursor.close()
            raise HTTPException(status_code=404, detail="Post not found!")
    cursor.execute(
        "UPDATE post SET title=%s, user_id=%s, created_on=%s WHERE post_id=%s",
        (post.title, post.user_id, post.created_on, post_id),
    )
    cnx.commit()
    return {"msg": f"Post updated by {current_user.username}."}


@app.delete("/posts/{post_id}")
async def delete_post(
    current_user: Annotated[User, Depends(get_current_active_user)], post_id: int
):
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM post NATURAL JOIN user WHERE post_id=%s AND username=%s",
        (post_id, current_user.username),
    )
    for (count,) in cursor:
        if count < 1:
            raise HTTPException(status_code=404, detail="Post not found!")
    cursor.execute(f"DELETE FROM post WHERE post_id={post_id}")
    cnx.commit()
    return {"msg": "Post deleted."}


@app.get("/comments/{comment_id}")
async def get_comments(comment_id: int):
    cursor = cnx.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM comment WHERE comment_id={comment_id}")
    for (count,) in cursor:
        if count < 1:
            raise HTTPException(status_code=404, detail="Post not found!")
    cursor.execute(
        "SELECT username, commented_on, comment "
        f"FROM comment NATURAL JOIN post NATURAL JOIN user WHERE comment_id={comment_id}"
    )
    for username, commented_on, comment in cursor:
        return {"username": username, "commented_on": commented_on, "comment": comment}


@app.post("/posts/{post_id}/comments")
async def create_post_comment(
    current_user: Annotated[User, Depends(get_current_active_user)],
    post_id: int,
    comment: Comment,
):
    cursor = cnx.cursor()
    try:
        print(comment)
        cursor.execute(
            "INSERT INTO comment(user_id, post_id, commented_on, comment)"
            "SELECT user_id, %s, %s, %s FROM user WHERE username=%s",
            (post_id, comment.commented_on, comment.comment, current_user.username),
        )
        cnx.commit()
    except sql.Error as err:
        print(f"Failed creating comment: {err}")
        raise HTTPException(status_code=409, detail="Failed to create comment!")
    return {"msg": "comment created successfully!"}


@app.put("/comment/{comment_id}")
async def update_comment(
    current_user: Annotated[User, Depends(get_current_active_user)],
    comment_id: int,
    comment: Comment,
):
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM comment NATURAL JOIN user WHERE comment_id=%s AND username=%s",
        (comment_id, current_user.username),
    )
    for (count,) in cursor:
        if count < 1:
            raise HTTPException(status_code=404, detail="Comment not found!")
    cursor.execute(
        "UPDATE comment SET post_id=%s, commented_on=%s, comment=%s WHERE comment_id=%s",
        (comment.post_id, comment.commented_on, comment.comment, comment_id),
    )
    cnx.commit()
    return {"msg": "Comment updated."}


@app.delete("/comment/{comment_id}")
async def delete_comment(
    current_user: Annotated[User, Depends(get_current_active_user)], comment_id: int
):
    cursor = cnx.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM comment NATURAL JOIN user WHERE comment_id=%s and username=%s",
        (comment_id, current_user.username),
    )
    for (count,) in cursor:
        if count < 1:
            raise HTTPException(status_code=404, detail="Comment not found!")
    cursor.execute(f"DELETE FROM comment WHERE comment_id={comment_id}")
    cnx.commit()
    return {"msg": "Comment deleted."}
