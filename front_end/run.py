#!../venv/bin/python

"""IMPORT FLASK INSTANCES FROM FOLDER FrontEnd"""
from FrontEnd import webapp as front


if __name__ == "__main__":
    front.run(host='0.0.0.0',
              port='5000',
              debug=True,
              use_reloader=False,
              use_debugger=False,
              threaded=True)
