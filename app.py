from flask import Flask
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from blueprints.auth import auth_bp
from blueprints.home import home_bp
from blueprints.acc import acc_bp
from services.models import User 

app = Flask(__name__)
app.secret_key = 'chiave_per_session'

app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(acc_bp)

if __name__ == '__main__':
    app.run(debug=True)
  