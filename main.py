import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_ckeditor import CKEditor
from flask_bootstrap import Bootstrap4
import smtplib
from datetime import datetime
from flask_login import UserMixin, LoginManager, login_required, login_user, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, NoResultFound
from functools import wraps
from flask_migrate import Migrate
from flask_gravatar import Gravatar


MY_EMAIL = 'fahuayaro@gmail.com'
MY_PASSWORD = os.getenv("EMAIL_PASSWORD")

# initialize flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# connect to database
db = SQLAlchemy()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blogs.db"
db.init_app(app)

# migrate database
# migrate = Migrate(app, db)


# setup flask login manager
login_manager = LoginManager()
login_manager.init_app(app)


# setup ckeditor
ckeditor = CKEditor()
ckeditor.init_app(app)

# bootstrap for render form
bootstrap = Bootstrap4()
bootstrap.init_app(app)

# initialize gravatar
gravatar = Gravatar(app,
                    size=50,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


# configure user table
class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    # create relationship db
    posts = db.relationship("BlogPost", back_populates="author")
    comments_by_author = db.relationship("Comment", back_populates="comment_writer")


# configure database table
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # linked user id in blog post with FK
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = db.relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    comments = db.relationship("Comment", back_populates="post")


# comment table
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text)
    comment_writer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comment_writer = db.relationship("User", back_populates="comments_by_author")
    date = db.Column(db.String(250))
    blog_post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    post = db.relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    try:
        cur_user = db.session.execute(db.select(User).filter_by(id=int(user_id))).scalar_one()
    except NoResultFound:
        cur_user = None
    return cur_user


# admin only wrapper function
def admin_only(func):
    @wraps(func)
    def decorator_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return func(*args, **kwargs)
    return decorator_function


@app.route('/')
def home():
    posts = list(db.session.query(BlogPost).order_by(BlogPost.id).all())
    return render_template('index.html', all_post=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit():
        new_user = User(
            name=register_form.name.data,
            email=register_form.email.data,
            password=generate_password_hash(register_form.password.data, method='pbkdf2:sha256', salt_length=8)
        )
        db.session.add(new_user)
        try:
            db.session.commit()
        except IntegrityError:
            flash("Email is already registered.")
            return redirect(url_for('register'))
        login_user(new_user)
        session['name'] = register_form.name.data
        return redirect(url_for('home'))
    return render_template('register.html', form=register_form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user_email = login_form.email.data
        user_password = login_form.password.data
        try:
            user = db.session.execute(db.select(User).filter_by(email=user_email)).scalar_one()
        except NoResultFound:
            flash("Email not registered", category="error")
            return redirect(url_for('login'))
        if check_password_hash(user.password, user_password):
            login_user(user)
            session['name'] = user.name
            return redirect(url_for('home'))
        else:
            flash("Wrong password.", category="error")
            return redirect(url_for('login'))
    return render_template('login.html', form=login_form)


@app.route('/logout')
def logout():
    logout_user()
    flash('Logged out success.')
    return redirect(url_for('home'))


@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login to comment.")
            return redirect(url_for('login'))
        elif comment_form.comment.data:
            new_comment = Comment(
                comment=comment_form.comment.data,
                comment_writer=current_user,
                comment_writer_id=current_user.id,
                date=datetime.today().strftime("%B %d %Y"),
                blog_post_id=post_id
            )
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
    return render_template("post.html", post=requested_post, form=comment_form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
@login_required
def create_post():
    create_blog_post = CreatePostForm()
    if create_blog_post.validate_on_submit():
        now = datetime.now()
        new_post = {field: value for field, value in create_blog_post.data.items() if field != 'submit' and field != 'csrf_token'}
        new_post['date'] = now.strftime("%B %d, %Y")
        new_post['author'] = current_user
        new_post['author_id'] = int(current_user.id)
        new_post = BlogPost(**new_post)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("create_post.html", form=create_blog_post, to_edit=False)


@app.route('/edit-post/int:<post_id>', methods=['GET', 'POST'])
@admin_only
@login_required
def edit_post(post_id):
    post_to_edit = db.get_or_404(BlogPost, post_id)
    # This pre-populates the form to be rendered.
    edit_blog_form = CreatePostForm(
        title=post_to_edit.title,
        subtitle=post_to_edit.subtitle,
        date=post_to_edit.date,
        body=post_to_edit.body,
        img_url=post_to_edit.img_url
    )
    if edit_blog_form.validate_on_submit():
        post_to_edit.title = edit_blog_form.title.data
        post_to_edit.subtitle = edit_blog_form.subtitle.data
        post_to_edit.body = edit_blog_form.body.data
        post_to_edit.img_url = edit_blog_form.img_url.data
        db.session.commit()
        return redirect(url_for('show_post', post_id=post_id))
    return render_template("create_post.html", form=edit_blog_form, id=post_id)


@app.route("/delete/<int:post_id>")
@login_required
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=["POST", "GET"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]
        with smtplib.SMTP("smtp.gmail.com") as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=MY_PASSWORD)
            connection.sendmail(from_addr=email,
                                to_addrs=MY_EMAIL,
                                msg=f"Subject:New message\n\nName: {name}\nEmail:{email}\nPhone: {phone}\nMessage: {message}")
        print(f"{name}\n{email}\n{phone}\n{message}")
        return render_template('contact.html', submit=True)
    else:
        return render_template('contact.html')


if __name__ == "__main__":
    app.run(debug=True)
