import sys
import os
from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)
current_location = os.path.dirname(os.path.abspath(__file__))


@app.route('/validate_user_details', methods=['POST'])
def validate_user_details():
    try:
        user_details = request.get_json()
        print()
        print("Client information successfully recieved.")
        if user_details['user_choice'] == '1':
            username = user_details['username']
            password = user_details['password']
            token = None
            user_data_file = os.path.join(current_location, 'userRecords.txt')
            with open(user_data_file, 'r') as file:
                for line in file:
                    if 'Username: ' + username in line and ' Password: ' + password in line:
                        token = line.split(', ')[-1].replace(' Token: ', '').strip()
                        print("Client has been logged in successfully.")
                        break
                    else:
                        print("Invalid login details recieved client not logged in")
                        break
            return jsonify({'token': token})
        elif user_details['user_choice'] == '2':
            print("User has been registered successfully")
            generated_authentication_token = str(uuid.uuid4())
            try:
                user_data_file = os.path.join(current_location, 'userRecords.txt')
                if not os.path.exists(user_data_file):
                    with open(user_data_file, 'w'): 
                        pass
                with open(user_data_file, 'a') as file:
                    file.write(f"Username: {user_details['username']}, Password: {user_details['password']}, Token: {generated_authentication_token}\n")
                print("User token has been generated and saved successfully.")
                return jsonify({'token': generated_authentication_token})
            except Exception as ex:
                print(f"Exception: {ex}")
        else:
            print("Invalid user choice recieved.")
            pass
    except Exception as ex:
        print(f"Exception: {ex}")


if __name__ == '__main__':
    host = "localhost"
    port = 50007
    try:
        if len(sys.argv) > 2:
            host = sys.argv[1]
            port = int(sys.argv[2])
    except Exception as ex:
        print(f"Exception: {ex}")
    app.run(host=host, port=port, debug=True)
