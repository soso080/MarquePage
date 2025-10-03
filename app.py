import os
from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "super_secret_key"  # change ça par un vrai secret

# --- Connexion Mongo ---
client_db = MongoClient(
    "mongodb+srv://soso:soso@cluster0.ggd13ry.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)

db = client_db["marquepage"]
users_col = db["users"]
all_col = db["all"]

# --- Config upload ---
UPLOAD_FOLDER = "static/uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = users_col.find_one({"_id": ObjectId(user_id)})

    query = {}
    search = request.args.get("q")
    if search:
        query["titre"] = {"$regex": search, "$options": "i"}  # insensitive (A/a)

    if not user.get("is_admin"):
        query["user_id"] = user_id

    products = all_col.find(query)

    return render_template("index.html", products=products, user=user, search=search)



# --- Inscription ---
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        if users_col.find_one({"username": username}):
            return "Nom d’utilisateur déjà pris"

        users_col.insert_one({"username": username, "password": password, "is_admin": False})
        return redirect(url_for("login"))

    return render_template("register.html")

# --- Connexion ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_col.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            return redirect(url_for("index"))

        return "Identifiants incorrects"

    return render_template("login.html")

# --- Déconnexion ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Ajouter une œuvre ---
@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        titre = request.form["titre"]
        ep = request.form["ep"]

        img_url = request.form.get("img")  # URL si fourni
        img_file = request.files.get("img_file")  # Fichier si upload

        if img_file and allowed_file(img_file.filename):
            filename = secure_filename(img_file.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            img_file.save(path)
            img = f"/static/uploads/{filename}"
        elif img_url:
            img = img_url
        else:
            img = "/static/default.png"  # image par défaut si rien

        all_col.insert_one({
            "titre": titre,
            "img": img,
            "ep": ep,
            "user_id": session["user_id"]
        })
        return redirect(url_for("index"))

    return render_template("add.html")


# --- Modifier progression ---
@app.route("/update/<id>", methods=["POST"])
def update(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    ep = request.form["ep"]
    all_col.update_one({"_id": ObjectId(id)}, {"$set": {"ep": ep}})
    return redirect(url_for("index"))


@app.route("/delete/<id>", methods=["POST"])
def delete(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    all_col.delete_one({"_id": ObjectId(id)})
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
