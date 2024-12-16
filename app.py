import random

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, jsonify, json
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Connect to the database
db = SQL("sqlite:///chefchoice.db")

# based on pset9 from CS50x
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


#register route based on what I developed for pset9 of CS50X
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        #Validations
        if not request.form.get("username"):
            return render_template("register.html", message="Error! Must provide username.")

        elif not request.form.get("password"):
            return render_template("register.html", message="Error! Must provide password.")

        elif not request.form.get("confirmation"):
            return render_template("register.html", message="Error! Must provide password confirmation.")

        elif request.form.get("password") != request.form.get("confirmation"):
            return render_template("register.html", message="Error! Passwords do not match.")
        #Register with hash
        else:
            username = request.form.get("username")
            hash = generate_password_hash(request.form.get(
                "password"), method='scrypt', salt_length=16)
            #check if user already exists
            try:
                db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
            except:
                return render_template("register.html", message="Error! Username already exists.")
            return redirect("/login")
    else:
        return render_template("register.html")

#login route based on what I developed for pset9 of CS50X
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", message="Error! Must provide username.")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", message="Error! Must provide password.")

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", (request.form.get("username"))
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return render_template("login.html", message="Error! Invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

#logout route based on what I developed for pset9 of CS50X
@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


#render Homepage with instructions
@app.route("/")
@login_required
def index():
    return render_template("index.html")


#based on what I developed for pset9 of CS50X for changing passwords
@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    if request.method == "POST":
        #Validation
        pwhash = db.execute("SELECT hash FROM users WHERE id = ?",
                            session.get("user_id"))[0]["hash"]
        if not request.form.get("old"):
            return render_template("change.html", message="Error! Must provide old password.")

        elif not request.form.get("password"):
            return render_template("change.html", message="Error! Must provide password.")

        elif not request.form.get("confirmation"):
            return render_template("change.html", message="Error! Must provide password confirmation.")

        elif request.form.get("password") != request.form.get("confirmation"):
            return render_template("change.html", message="Error! Passwords do not match")

        elif request.form.get("password") == request.form.get("old"):
            return render_template("change.html", message="Error! New password is equal to old password.")

        elif not check_password_hash(pwhash, request.form.get("old")):
            return render_template("change.html", message="Error! Old password is not correct.")
        #change the password
        else:
            hash = generate_password_hash(request.form.get(
                "password"), method='scrypt', salt_length=16)
            db.execute("UPDATE users SET hash = ? WHERE id = ?", hash, session.get("user_id"))
            return redirect("/login")
    else:
        return render_template("change.html")


#route to add recipes per user
@app.route("/addrecipe", methods=["GET", "POST"])
@login_required
def addrecipe():
    if request.method == "POST":
        #data is being dinamically fed by the user, using JSON to get the data (ingredients, quantity and unit for recipe)
        data = request.get_json()
        recipe_name = data.get("name").capitalize()
        ingredients = data.get("ingredients")
        if not recipe_name or not ingredients:
            #validation of data entry
            return jsonify({"message": "Invalid data provided."}), 400

        existing_recipe = db.execute("SELECT name from recipes WHERE name = ? AND user_id = ?", recipe_name, session.get("user_id"))
        if existing_recipe:
            return jsonify({"message": "Recipe Already Exists"}), 400

        # Insert recipe and ingredients into the database
        
        db.execute("INSERT INTO recipes (name, user_id) VALUES (?, ?)", recipe_name, session.get("user_id"))
        recipe_id = db.execute("SELECT id FROM recipes WHERE name = ?", recipe_name)[0]["id"]

        for ingredient in ingredients:
            ingredient_id = db.execute("SELECT id FROM ingredients WHERE name = ?", ingredient["ingredient"])[0]["id"]
            db.execute(
                "INSERT INTO recipe_ingredients (recipe_id, ingredient_id, quantity, unit) VALUES (?, ?, ?, ?)",
                recipe_id, ingredient_id, ingredient["quantity"], ingredient["unit"]
            )
        return jsonify({"message": f"Voilá! Recipe '{recipe_name}' saved successfully!"})

    #show list of available ingredients
    else:
        ingredients = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
        return render_template("/addrecipe.html", ingredients=ingredients)

#route to search for recipes and see or delete them
@app.route("/recipe", methods=["GET", "POST"])
@login_required
def recipe():
    if request.method == "POST":
        #show avaliable recipes
        recipe = request.form.get("dropdown")
        #validation
        if not recipe:
            return render_template("recipe.html", message = "You have to select a recipe!")
        recipe_result = db.execute("SELECT id FROM recipes WHERE name = ? AND user_id = ?", recipe, session.get("user_id"))
        recipe_id = recipe_result[0]["id"]
        action = request.form.get("action")
        #search parameter, to show ingredients of recipe
        if action == "query":
            data = db.execute("SELECT ingredient_id, quantity, unit FROM recipe_ingredients WHERE recipe_id = ?",
                      recipe_id)
            for item in data:
                ingredient_id = item["ingredient_id"]
                item["ingredient_name"] = db.execute("SELECT name FROM ingredients WHERE id = ?", ingredient_id)[0]["name"]
                #show quantity as null if unit is as needed
                if item["unit"] == "as needed":
                    item["quantity"] = ""
            data = sorted(data, key=lambda item: item['ingredient_name'])
            return render_template("reciped.html", data=data, recipe=recipe)
        #remove parameter, to delete recipe from database
        elif action == "remove":
            db.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", recipe_id)
            db.execute("DELETE FROM recipes WHERE name = ? AND user_id = ?", recipe, session.get("user_id"))
            rows = db.execute("SELECT name FROM recipes WHERE user_id = ?", session.get("user_id"))
            return render_template("recipe.html", options=rows, message="Recipe successfully removed!")

    else:
        #show recipes available
        rows = db.execute("SELECT name FROM recipes WHERE user_id = ?", session.get("user_id"))
        return render_template("recipe.html", options=rows)


#route to add ingredients to user's portfolio
@app.route("/ingredient", methods=["GET", "POST"])
@login_required
def ingredient():
    if request.method == "POST":
        ingredient = request.form.get("ingredient").capitalize()
        #validation of entry
        ing = db.execute("SELECT name FROM ingredients WHERE name = ? AND user_id = ?", ingredient, session.get("user_id"))
        if ing:
            rows = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
            return render_template("ingredient.html", message="Error! Ingredient already exists", options=rows)
        if not request.form.get("ingredient"):
            rows = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
            return render_template("ingredient.html", message="Error! Please input an ingredient", options=rows)
        
        db.execute("INSERT INTO ingredients (name, user_id) VALUES(?, ?)", ingredient, session.get("user_id"))
        rows = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
        return render_template("ingredient.html", message="Ingredient successfully added", options=rows)
        
        #show list of ingredients
    else:
        rows = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
        return render_template("ingredient.html", options=rows)

#route to remove ingredients from user's portfolio
@app.route("/remove", methods=["GET", "POST"])
@login_required
def remove():
    if request.method == "POST":
        ingredientr = request.form.get("dropdown")
        #validation
        if not request.form.get("dropdown"):
            rows = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
            return render_template("ingredient.html", message="Error! Please input an ingredient", options=rows)
        db.execute("DELETE FROM ingredients WHERE name = ? AND user_id = ?", ingredientr, session.get("user_id"))
        rows = db.execute("SELECT name FROM ingredients WHERE user_id = ?", session.get("user_id"))
        return render_template("ingredient.html", message="Ingredient successfully removed", options=rows)
    
    else:
         return render_template("ingredient.html")


#route for the randomizer
@app.route("/selector", methods=["GET", "POST"])
@login_required
def selector():
    #to create an excluded list of recipes for the session
    if "excluded" not in session:
        session["excluded"] = set()
    
    excluded = set(session["excluded"])  # Retrieve the excluded set
    #get the list of recipes
    recipes = db.execute("SELECT id FROM recipes WHERE user_id = ?", session.get("user_id"))
    leng = len(recipes)

    if request.method == "POST":
        #validation
        if leng == 0:
            return render_template("selector.html", message="You don't have any recipes!")
        
        recipe_rand = random.randint(0, leng-1)
        action = request.form.get("action")
        if action == "selector" or action == "another":
            # Handle exclusion logic
            if len(excluded) == leng:
                return render_template("selectord.html", message="You don't have any more recipes! Click here to start over.")
            #randomize between all available recipes
            while recipe_rand in excluded:
                recipe_rand = random.randint(0, leng-1)
            #add the recipe to the excluded list in case the person does not want that and presses "another"
            excluded.add(recipe_rand)
            session["excluded"] = list(excluded)  # Update the session
            recipe_id = recipes[recipe_rand]["id"]
            data = db.execute("SELECT ingredient_id, quantity, unit FROM recipe_ingredients WHERE recipe_id = ?", recipe_id)
            recipe = db.execute("SELECT name FROM recipes WHERE id = ?", recipe_id)[0]["name"]
            #generate recipe (ingredients, quantity etc for the selected recipe)
            for item in data:
                ingredient_id = item["ingredient_id"]
                item["ingredient_name"] = db.execute("SELECT name FROM ingredients WHERE id = ? and user_id = ?", ingredient_id, session.get("user_id"))[0]["name"]
            return render_template("selected.html", data=data, recipe=recipe)
                    
    else:
        #set excluded to zero whenever user enters again in the randomizer
        session["excluded"] = []
        return render_template("selector.html")

#route for the weekly planner
@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():
    #grab all recipes from the user
    recipes = db.execute("SELECT name FROM recipes WHERE user_id = ?", session.get("user_id"))
    leng = len(recipes)
    #validation
    if leng == 0:
        return render_template("planner.html", message="You don't have any recipes. Please create recipes for your portfolio first.")
    if request.method == "POST":
        action = request.form.get("action")
        if action == "selector":
            #guarantee the DB is empty to create new set of weekly plan
            db.execute("DELETE FROM list_items WHERE user_id = ?", session.get("user_id"))
            n = 0
            list = []
            grocery = {}
            #generate 14 random meals
            while n < 14:
                n = n + 1
                recipe_rand = random.randint(0, leng-1)
                recipe = recipes[recipe_rand]["name"]
                list.append(recipe)
            for recipe_name in list:
                #save the 14 random meals in a database
                db.execute("INSERT INTO list_items (user_id, item) VALUES (?, ?)", session.get("user_id"), recipe_name)
                #grab ingredients to make a grocery list of the 14 meals
                recipe_id = db.execute("SELECT id FROM recipes WHERE name = ?", recipe_name)[0]["id"]
                data = db.execute("SELECT ingredient_id, quantity, unit FROM recipe_ingredients WHERE recipe_id = ?", recipe_id)
                for ingredient in data:
                    ingredient_id = ingredient["ingredient_id"]
                    quantity = ingredient["quantity"]
                    unit = ingredient["unit"]
                    key = f"{ingredient_id}_{unit}"
                    #if there is no combination of ingredient and type of unit, create a new line
                    if key not in grocery:
                        grocery[key] = {"quantity": quantity, "unit": unit, "ingredient_name": db.execute("SELECT name FROM ingredients WHERE id = ?", ingredient_id)[0]["name"]}
                    #else, if there is, just sum the quantities
                    else:
                        grocery[key]["quantity"] += quantity
            #transform quantity in null for "as needed" ingredients            
            for key in grocery:
                if grocery[key]["unit"] == "as needed":
                    grocery[key]["quantity"] = ""
            #sort ingredients alphabetically
            grocery = sorted(grocery.items(), key=lambda item: item[1]['ingredient_name'])
            return render_template("planned.html", list = list, grocery=grocery)
            #save list
        if action == "save":
            updated_meals = request.form.get('updatedMeals')
            if updated_meals:
                updated_meals = json.loads(updated_meals)
            db.execute("DELETE FROM list_items WHERE user_id = ?", session.get("user_id"))
            print(updated_meals)
            for recipe_name in updated_meals:  # Iterate through the meal names
                db.execute("INSERT INTO list_items (user_id, item) VALUES (?, ?)", session.get("user_id"), recipe_name)
            rows = db.execute("SELECT item FROM list_items WHERE user_id = ?", session.get("user_id"))
            list = [row["item"] for row in rows]
            return render_template("plan.html", list=list)

        
        else:
            #grab list of meals and grocery for the session
            list = session.get("list", [])
            grocery = session.get("grocery", {})
            return render_template("planned.html", list=list, grocery=grocery)
        
    
    else:
        return render_template("planner.html")

#route to show the saved weekly plan
@app.route("/plan", methods=["GET", "POST"])
@login_required
def plan():
        #access database to show weekly plan
        rows = db.execute("SELECT item FROM list_items WHERE user_id = ?", session.get("user_id"))
        list = [row["item"] for row in rows]
        #validation if there is already a weekly plan made
        if len(list) == 0 :
            return render_template("planner.html", message = "Error! Plan your week first, please!")
        return render_template("plan.html", list=list)

if __name__ == "__main__":
    app.run(debug=True)