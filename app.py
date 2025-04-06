from flask import Flask
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from blueprints.auth import auth_bp
from blueprints.home import home_bp
from blueprints.acc import acc_bp
from services.models import User
from blueprints.analysis import analysis_bp 


app = Flask(__name__)
app.secret_key = 'chiave_per_session'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'local_login.login_page'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(acc_bp)
app.register_blueprint(analysis_bp)

if __name__ == '__main__':
    app.run(debug=True)
  