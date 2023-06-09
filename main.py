from enum import unique
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date

from werkzeug import security
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterUserForm, LoginUserForm, CommentForm
from flask_gravatar import Gravatar

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)


##CONFIGURE TABLES

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    posts = db.relationship('BlogPost', back_populates='user')  # parent table of Post
    # ClassName must be EQAUL
    comments = db.relationship('Comment', back_populates='user')  # parent table of Comment


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    post_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # foreign key of parent User

    user = db.relationship('User', back_populates='posts')

    comments = db.relationship('Comment', back_populates='blog_post')  # parent Table of Comment Class


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)

    commentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # foreign key of parent User
    user = db.relationship('User', back_populates='comments')

    post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'))  # foreign key of parent Post
    blog_post = db.relationship('BlogPost', back_populates='comments')


# db.drop_all()
# db.create_all()
#
# new_user = User(
#     name="farhat",
#     email='farhxt.abbxs69@gmail.com',
#     password=generate_password_hash('12345', method='pbkdf2:sha256', salt_length=8)
# )
# db.session.add(new_user)
# db.session.commit()


@app.route('/')
def get_all_posts():
    # print(f'current users id: {current_user.get_id()}')
    # print(f'current users type: {type(current_user.get_id())}')

    posts = BlogPost.query.all()
    return render_template("index.html", posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterUserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.email.data).first()
        if user:
            flash('User Already Exists, Please Login!')
            return redirect(url_for('login'))
        else:
            hashed_pass = security.generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                password=hashed_pass
            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


def user_name(user_id):
    return User.query.get(user_id).name


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginUserForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        comment = form.body.data
        new_comment = Comment(
            body=comment,
            commentor_id=current_user.id,
            post_id=post_id,
        )
        db.session.add(new_comment)
        db.session.commit()
    requested_post = BlogPost.query.get(post_id)

    return render_template("post.html", post=requested_post, form=form)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


def admin_only(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        print(f'current user id: {current_user.id}')
        if int(current_user.get_id()) != 1:
            return abort(403)
        else:
            return func(*args, **kwargs)

    return decorated_func


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y"),
            post_user_id=int(current_user.get_id())
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)

#
#
# class Post(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(100))
#     content = db.Column(db.Text)

#
#     def __repr__(self):
#         return f'<Post "{self.title}">'
#
#
# class Comment(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     content = db.Column(db.Text)
#     post_id = db.Column(db.Integer, db.ForeignKey('post.id')) # foreign key of parent Post
#     commentor_id = db.Column(db.Integer, db.ForeignKey('user.id')) # foreign key of parent User
#
#     def __repr__(self):
#         return f'<Comment "{self.content[:20]}...">'
