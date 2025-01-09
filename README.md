# FastAF

A web CRUD API for user post and comment management written in python using FastAPI with JWT based user authentication.

# Useful Data Models

- `User`: non-login user data (e.g., username, dob)
- `Post`: post data (e.g., title, created_on)
- `Comment`: comment data (e.g., comment, commented_on)

# Endpoints

- > `/token`
  >
  > - generting JWT authentication token based on login data received
- > `/users`
  >
  > - creating new users in the database
  > - accessing user data post login
- > `/posts`
  >
  > - accessing user posts
- > `/comments`
  >
  > - for accessing user comments on various posts
