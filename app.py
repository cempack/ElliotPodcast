# app.py

from app import create_app

app = create_app()
print("Flask app instance created")


if __name__ == '__main__':
    app.run()
