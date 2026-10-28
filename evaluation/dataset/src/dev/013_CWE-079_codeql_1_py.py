from flask import Flask, request
from jinja2 import Environment, FileSystemLoader
app = Flask(__name__)

@app.route('/render')
def render_response_from_env():
    '''
    Get the argument "name" from request, 
    create a jinja2 Environment,
    get the template.html from the environment, and render it.
    '''
    name = request.args.get('name', '')
    env = Environment(loader=FileSystemLoader('.'))  # @label xss high -- jinja2 Environment() has autoescape off by default
    template = env.get_template('template.html')
    return template.render(name=name)