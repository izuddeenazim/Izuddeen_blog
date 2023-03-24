from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField
from wtforms.validators import InputRequired, URL, EqualTo
from flask_ckeditor import CKEditorField


# wtform create new post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[InputRequired()])
    subtitle = StringField("Subtitle", validators=[InputRequired()])
    img_url = StringField("Blog Image URL", validators=[InputRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[InputRequired()])
    submit = SubmitField("Submit Post")


# wtform register form
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[InputRequired()])
    email = EmailField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    confirm_password = PasswordField(label="Confirm Password",
                                     validators=[InputRequired(), EqualTo('password', message="Passwords not match")])
    submit = SubmitField("Sign Me Up")


# wtform login form
class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    submit = SubmitField("Log In")


# wtform comment form
class CommentForm(FlaskForm):
    comment = CKEditorField("Comment", validators=[InputRequired()])
    submit = SubmitField("Submit")
