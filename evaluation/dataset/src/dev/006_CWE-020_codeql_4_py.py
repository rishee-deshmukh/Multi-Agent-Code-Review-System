from flask import Flask, redirect, request

app = Flask(__name__)

@app.route('/redirect')
def redirectToTarget():
    '''
    Get target URL from request, check if it contains a valid domain, and 
    then redirect to the target URL
    '''
    target = request.args.get('target', '')
    if "example.com" in target:
        return redirect(target)  # @label open_redirect medium -- substring check is bypassable (evil.com/?example.com)
    else:
        return "Invalid target"