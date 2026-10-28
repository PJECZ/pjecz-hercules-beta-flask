"""
Arrancar el servidor de la aplicación Flask

https://stackoverflow.com/questions/51395936/how-to-get-flask-app-running-with-gunicorn
"""

from pjecz_hercules_beta_flask.main import app

if __name__ == "__main__":
    # Running the server locally
    #     python3 appserver.py
    app.run()
else:
    # Run the server via Gunicorn
    #     gunicorn --bind 127.0.0.1:5000 appserver:gunicorn_app
    # You need to specify the module name and the variable name of the app for Gunicorn to access it.
    # Note that the variable should be a WSGI callable object for e.g a flask app object.
    gunicorn_app = app
