import re
import sys
import os
import logging
from datetime import datetime, timedelta
import json
from flask import Flask, flash, abort,  render_template, request, redirect, url_for, jsonify
from flask import session
import secrets
import requests
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.permanent_session_lifetime = timedelta(minutes=5)
app.logger.propagate = False




############## USER SHOULD ONLY EDIT THE FOLLOWING###########################
config_file = 'config.json'
#############################################################################

def file_perm_check(file_name,is_json):
    if not os.path.exists(file_name):
        with open(file_name, 'w') as f:
            if is_json:
                json.dump({}, f)
            os.chmod(file_name, 0o600)
    elif os.stat(file_name).st_mode & 0o777 != 0o600:
        os.chmod(file_name, 0o600)
 
def load_config():
    file_perm_check(config_file,True)
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Unable to read the config file, missing config.json. Error={str(e)}")
        sys.exit(1)
    return config

config = load_config()

try:
    RESOURCE_INFO=config['RESOURCE_INFO']
    LAB_NAMES=list(config['RESOURCE_INFO'].keys())
    DB_FILE=config['DB_FILE']
    PORT=config['PORT']
    HOST=config['HOST']
    TITLE=config['TITLE']
    FOOTER_MESSAGE=config['FOOTER_MESSAGE']
    RESOURCE_NAME=config['RESOURCE_NAME']
    ALLOWED_DOMAINS=config['ALLOWED_DOMAINS']
    USER_DB=config['USER_DB']
    REGISTRATION_ALLOWED=config['REGISTRATION_ALLOWED']
    LOG_FILE=config['LOG_FILE']
    ADMIN_INFO=config['ADMIN_INFO']
    TZ=config['TZ']
except Exception as e:
    print(f"Unable to read the config data, {e}")
    sys.exit(2) 

if not os.path.exists(os.path.expanduser(ADMIN_INFO)):
    print(f"Error: Unable to locate the admin credential file. No file found at {ADMIN_INFO}")
    sys.exit(1)


#create and secure the DB file if needed
file_perm_check(os.path.expanduser(DB_FILE),True)

#create and secure the user db file if needed
file_perm_check(os.path.expanduser(USER_DB),True)

#create and secure the logs file if needed(this is not a JSON file)
file_perm_check(os.path.expanduser(LOG_FILE),False)


# Set up the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(os.path.expanduser(LOG_FILE), maxBytes=10000, backupCount=5)

handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)



try:
    with open(os.path.expanduser(DB_FILE), 'a') as f:
        pass # the file is created and immediately closed
    print(f"The file '{DB_FILE}' was created with 0o600 permission.")
    os.chmod(os.path.expanduser(DB_FILE), 0o600)

except IOError:
    print(f"An error occurred while creating the file '{DB_FILE}'.")



def overlaps(start_time1, end_time1, start_time2, end_time2):
    # convert time strings to datetime objects
    start1 = datetime.strptime(start_time1, '%Y-%m-%d %H:%M')
    end1 = datetime.strptime(end_time1, '%Y-%m-%d %H:%M')
    start2 = datetime.strptime(start_time2, '%Y-%m-%d %H:%M')
    end2 = datetime.strptime(end_time2, '%Y-%m-%d %H:%M')

    # check for overlap
    if start1 < end2 and start2 < end1:
        return True
    else:
        return False


def group_bookings(bookings):
    # Group bookings by lab name and date
    groups = {}
    for booking in bookings:
        lab_date = booking['lab_name'] + '|' + booking['start_date_time'][:10]
        if lab_date not in groups:
            groups[lab_date] = []
        groups[lab_date].append(booking)
    return groups

def format_time(time_str):
    # Format time string for display
    return datetime.strptime(time_str, '%Y-%m-%d %H:%M').strftime('%I:%M %p')


@app.route('/', methods=['GET', 'POST'])
def index():
    # Render index template with lab_names as context variable
    authenticated = session.get('authenticated', False)
    if session.get('user_type', 'user') == 'admin':
        admin = True
    else:
        admin = False
    return render_template('index.html',
               lab_names=LAB_NAMES,
               authenticated=authenticated,
               title=TITLE,
               footer_msg=FOOTER_MESSAGE,
               resource_name=RESOURCE_NAME,
               username=session.get('username'),
               admin=admin,
               reg_open=REGISTRATION_ALLOWED,
               tz=TZ)

'''
'''
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session:
        session.clear()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the user is an admin
        with open(os.path.expanduser(ADMIN_INFO)) as f:
            admins = json.load(f)
        if username in admins and admins[username] == password:
            session['authenticated'] = True
            session['user_type'] = 'admin'
            session['username'] = username
            flash(f'Warning: You have been logged in as Admin({username}), You may delete entries created by any user!')
            logger.info(f'Admin({username}) login now')
            return redirect(url_for('index', authenticated=True))

        # If the user is not an admin, check if they are a regular user
        with open(os.path.expanduser(USER_DB)) as f:
            users = json.load(f)
        
        if username in users and users[username]['password'] == password:
            session['authenticated'] = True
            session['user_type'] = 'user'
            session['username'] = username
            flash(f'Note: For any possible exception write an Email to the admin(see footer)')
            logger.info(f'User({username}) login now')
            return redirect(url_for('index',authenticated=True))

        # If the username and password are invalid, display an error message
        logger.error(f"Login failed for {request.form['username']}")
        flash('Invalid username or password')
        return render_template('login.html',reg_open=REGISTRATION_ALLOWED)
    else:
        return render_template('login.html',reg_open=REGISTRATION_ALLOWED)

@app.route('/logout')
def logout():
    logger.info(f"User({session.get('username')}) logged out now")
    session.pop('authenticated', None)
    session.clear()
    session.pop('username', None)  # clear the username session variable
    return redirect(url_for('index'))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if ('authenticated' in session and session['authenticated']):
            if session['user_type'] != 'admin':
                 if not REGISTRATION_ALLOWED:
                     logger.error(f"{session['username']} ot type {session['user_type']} cannot register a user when registrations are closed")
                     abort(403)
        else:
            if not REGISTRATION_ALLOWED:
                logger.error(f"Cannot register a user unless logged in as admin, registration admin override is needed")
                abort(403)

        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        username = email
        domain = re.search("@[\w.]+", email).group()[1:]
        if domain not in ALLOWED_DOMAINS:
            logger.error(f"Registration failed due to invalid domain, {first_name}, {last_name}, {email}")
            return render_template('registration.html', error=f'{domain} is not a valid domain for registering an Email ID.',
                       footer_msg=FOOTER_MESSAGE,
                       title=TITLE)

        # Check if passwords match
        if password != confirm_password:
            return render_template('registration.html', error='Passwords do not match',
                   footer_msg=FOOTER_MESSAGE,
                   title=TITLE)
        
        # Create dictionary for user data
        user_data = {'first_name': first_name, 'last_name': last_name, 'email': email,'username': username, 'password': password}

        # Check if file exists, create it if it doesn't
        if not os.path.exists(os.path.expanduser(USER_DB)):
            with open(os.path.expanduser(USER_DB), 'w') as f:
                json.dump({}, f)
                
        # Read data from file
        with open(os.path.expanduser(USER_DB)) as f:
            users = json.load(f)
        
        # Check if email is already registered
        if email in users:
            logger.error(f"Registration failed the user {email} is already registered")
            return render_template('registration.html', error='Email already registered',
                       footer_msg=FOOTER_MESSAGE,
                       title=TITLE)
        
        # Add new user data to dictionary
        users[email] = user_data
        
        # Write updated data to file
        with open(os.path.expanduser(USER_DB), 'w') as f:
            json.dump(users, f)
        logger.info(f"Registration completed for {email}")
        return redirect(url_for('login'))
        
    else:
        return render_template('registration.html',
                   footer_msg=FOOTER_MESSAGE,
                   title=TITLE)


@app.route("/delete_event",methods=['POST'])
def delete():
    if 'authenticated' in session and session['authenticated']:
        if session['user_type'] == 'admin':
            pass
    else:
        description=request.form['description']

        return 'You must be Logged in to delete an Entry!'

    if 'id' not in request.form or not request.form['id']:
            return jsonify({'error': 'Missing User ID...'}), 400
    
    if 'start' not in request.form or not request.form['start']:
            return jsonify({'error': 'Start time is not present..'}), 400
    
    if 'end' not in request.form or not request.form['end']:
            return jsonify({'error': 'End time is not present..'}), 400
    
    if 'description' not in request.form or not request.form['description']:
            return jsonify({'error': 'Description is not present..'}), 400

    dt_start = datetime.fromisoformat(request.form['start'])
    formatted_timestamp_start = dt_start.strftime("%Y-%m-%dT%H:%M")
    dt_end = datetime.fromisoformat(request.form['end'])
    formatted_timestamp_end = dt_end.strftime("%Y-%m-%dT%H:%M")
    description=request.form['description']

    current_user = session.get('username')
    
    try:
        with open(os.path.expanduser(DB_FILE)) as f:
            existing_data = json.load(f)
    except json.decoder.JSONDecodeError as e:
        print(f"FATAL: Unable to read the {DB_FILE}")
        sys.exist(1)

    
    new_data = []
    for item in existing_data:
        if item["description"] != description and item["end"] != formatted_timestamp_end and item["start"] != formatted_timestamp_start:
            previous_user = re.search('booked by\s+([^ ]+)',item["description"]).group(1)
            if not session.get('user_type') == 'admin':
                if current_user != previous_user:
                    logger.error(f"The earlier event was created by {previous_user}, current user({current_user}) does not have rights to delete it.")
                    return f"Error: The earlier event was created by {previous_user}, current user({current_user}) does not have rights to delete it."
            new_data.append(item)

    try:
        with open(os.path.expanduser(DB_FILE), 'w') as f:
            json.dump(new_data, f, indent=2)
    except json.decoder.JSONDecodeError as e:
        print(f"FATAL: Unable to read the {DB_FILE}")
        sys.exist(1)
    logger.info(f"Entry Deleted for '{description}'!")
    return f'Entry Deleted for "{description}"!'

@app.route('/bookings', methods=['GET', 'POST'])
def calendar():
    if 'authenticated' in session and session['authenticated']:
            pass
    else:
        return redirect(url_for('login', authenticated=False))
    try:
        with open(os.path.expanduser(DB_FILE), 'r') as f:
            bookings = json.load(f)
    except json.decoder.JSONDecodeError:
        bookings = []
    # Extract booking data from form
    if request.method == 'POST':
        print(request.form)
         # Check if user ID is present and not empty
        if 'user_id' not in request.form or not request.form['user_id']:
            return jsonify({'error': 'Missing User ID...'}), 400
        if 'lab_name' not in request.form or not request.form['lab_name']:
            return jsonify({'error': 'Missing Lab name...'}), 400
        if 'start_date_time' not in request.form or not request.form['start_date_time']:
            return jsonify({'error': 'Missing start_date_time...'}), 400
        if 'end_date_time' not in request.form or not request.form['end_date_time']:
            return jsonify({'error': 'Missing end_date_time...'}), 400

        if request.form.get('sharable') == 'yes':
            if request.form.get('shared_with') == '':
                return jsonify({'error': 'Missing shared_with, if no fixed persion then you may supply NA/Everyone etc.'}), 400

        user_id = request.form.get('user_id')
        lab_name = request.form.get('lab_name')
        start = request.form.get('start_date_time')
        end = request.form.get('end_date_time')
        
        # The title must have 'booked by' substring
        if request.form.get('sharable') == 'yes':
            title = f"{lab_name} booked by {user_id} and shared with {request.form.get('shared_with')}"
        else:
            title = f"{lab_name} booked by {user_id}" 
        p=re.compile(r'^.+(?= booked by)')

        # Check if required form data is present
        if not all([id, title, start, end]):
            return jsonify({'error': 'Missing form data'}), 400

        # Check if end time is earlier than start time
        if datetime.strptime(end, '%Y-%m-%d %H:%M') < datetime.strptime(start, '%Y-%m-%d %H:%M'):
            return jsonify({'error': 'End time is earlier than start time'}), 400


        for booking in bookings:
            result = p.search(booking['description'])
            lab_name_from_title = result.group(0)
            if lab_name_from_title == lab_name and overlaps(start, end, booking['start'], booking['end']):
                logger.error(f"Booking overlaps with an existing booking, {title}")
                return jsonify({'error': 'Booking overlaps with an existing booking'}), 400

        # Add new booking to list of bookings

        if not bookings:
            bookings = [{
                'id': user_id,
                'title': lab_name,
                'start': start,
                'end': end,
                'description': title,
                'color': RESOURCE_INFO[lab_name]
                }]
        else:
            bookings.append({
               'id': user_id,
               'title': lab_name,
               'start': start,
               'end': end,
               'description': title,
               'color': RESOURCE_INFO[lab_name]
              })

        # Write updated bookings to JSON file
        try:
            with open(os.path.expanduser(DB_FILE), 'w') as f:
                json.dump(bookings, f,sort_keys = True, indent = 4,
                    ensure_ascii = False)
        except json.decoder.JSONDecodeError as e:
            print(f"FATAL: Unable to write to the JSON file {e}")
        logger.info(f"Booking done for {title}, start time={start}, end time={end}")
    else:
        return jsonify(bookings)

    return redirect(url_for('index'))


@app.route('/get_users', methods=['GET'])
def get_users():
    if 'authenticated' in session and session['authenticated']:
        if session['user_type'] == 'admin':
            pass
        else:
            abort(403) # do not let any non-root user to delete any user
    else:
        abort(403)     #do not let any non-authenticated user to delete any user.

    with open(os.path.expanduser(USER_DB)) as f:
        users = json.load(f)
    print(f"hjhjhjhjh {users}")
    return jsonify(users)

@app.route('/delete_user_list')
def delete_user_list():
    return render_template('select_user.html',authenticated=session.get('authenticated', False))

@app.route('/delete_user/<email>', methods=['DELETE'])
def delete_user(email):
    logger.info(f"User deletion request made for {email}")
    if 'authenticated' in session and session['authenticated']:
        if session['user_type'] == 'admin':
            pass
        else:
            abort(403) # do not let any non-root user to delete any user
    else:
        abort(403)     #do not let any non-authenticated user to delete any user.

    # Load existing user data from JSON file
    with open(os.path.expanduser(USER_DB), 'r') as f:
        all_user_data = json.load(f)
    # Check if user with given email exists
    if email in all_user_data:
        # Delete user data
        del all_user_data[email]
        # Write updated user data to JSON file
        with open(os.path.expanduser(USER_DB), 'w') as f:
            json.dump(all_user_data, f)
        # Return success message
        logger.info(f"User {email} deleted!")
        return jsonify({'message': 'User deleted successfully'})
    else:
        # Return error message
        return jsonify({'error': 'User not found'})

if __name__ == '__main__':

    app.run(debug=True, host=HOST,port=PORT)

