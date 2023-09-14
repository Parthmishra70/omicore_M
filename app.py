from flask import Flask, render_template, request,redirect,jsonify
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant, ChatGrant
from twilio.rest import Client
from flask_sqlalchemy import SQLAlchemy 
from sqlalchemy import and_
from uuid import uuid4
from datetime import datetime
from flask_socketio import SocketIO,join_room
import random
import secrets
         

app = Flask(__name__)
socketio = SocketIO(app)


# Configure the database URI
# app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://u943641251_omegle:GHZzFZ?Gc8]@82.180.138.188:3306/u943641251_omegle'
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://username:password@port/database_name'

sec = secrets.token_hex(16)
app.config['SECRET_KEY'] = sec  # secret key

# Initialize the SQLAlchemy extension
db = SQLAlchemy(app)
 
twilio_account_sid = 'YOUR ACCOUNT API KEY'
twilio_api_key_sid = 'YOUR ACCOUNT API KEY SID'
twilio_api_key_secret = 'YOUR API KEY SECRET'
twilio_client = Client(twilio_api_key_sid, twilio_api_key_secret,
                       twilio_account_sid)


class Rooms(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room = db.Column(db.String(100), nullable=True)
    username1 = db.Column(db.String(20), nullable=True)
    username2 = db.Column(db.String(20), nullable=True)
    Tuser1 = db.Column(db.String(120), nullable=True)
    Tuser2 = db.Column(db.String(120), nullable=True)
    status1 = db.Column(db.String(120), nullable=True)
    status2 = db.Column(db.String(120), nullable=True)
    date = db.Column(db.String(12), nullable=True)


#### for the chat sys main twilio api for chat  ####
conversation = None

# here chat sys
# create chatroom inside video room
def get_chatroom(roomname):
    for conversation in twilio_client.conversations.v1.conversations.stream():
        if conversation.friendly_name == roomname:
            return conversation

    return twilio_client.conversations.v1.conversations.create(
        friendly_name=roomname)


# generate_twilio_token
def generate_twilio_token(room , identity):
    global conversation
    if identity != None:
        token = AccessToken(twilio_account_sid, twilio_api_key_sid,
                            twilio_api_key_secret, identity=identity)
        video_grant = VideoGrant()
        token.add_grant(video_grant)
        conversation = get_chatroom(room)
        conversation.participants.create(identity=identity)
        token.add_grant(ChatGrant(service_sid=conversation.chat_service_sid))
        
        conversation = conversation.sid
        return str(token.to_jwt())
    else:
        return None


# whether user1 or user 2
def whether():
        if (Rooms.query.filter_by(username2=None).all()):
            return 'get'
        return 'post'
    
#room provider
def roomC():
    u = str(uuid4())
    return u[0:15]


def cleaner():
        Null_room= Rooms.query.filter(and_(Rooms.username1.is_(None), Rooms.username2.is_(None))).first()
        # offline_room= Rooms.query.filter(and_(Rooms.status1.is_('offline'), Rooms.status2.is_('offline'))).first()
        user_offline1 = Rooms.query.filter(Rooms.status1 == 'offline').first()
        user_offline2 = Rooms.query.filter(Rooms.status2 == 'offline').first()
        dependonedy = Rooms.query.filter(Rooms.date < datetime.now).first()

        if(Null_room):
            db.session.delete(Null_room)
            db.session.commit()
        # if offline_room:
        #     db.session.delete(offline_room)
        #     db.session.commit()
        if user_offline1:
            user_offline1.status1 ,user_offline1.Tuser1 ,user_offline1.username1  = None,None,None
            db.session.commit()
        if user_offline2:
            user_offline2.status2 ,user_offline2.Tuser2 ,user_offline2.username2  = None,None,None
            db.session.commit()
        if dependonedy:
            db.session.delete(dependonedy)
            db.session.commit()





@app.route('/')
def index():
    user1or2 = whether()
    return render_template('index.html',user1or2 = user1or2)


@socketio.on('user_connect')
def handle_connect(roomName):
    user_id = request.sid  # Use a unique identifier for the user
    join_room(roomName)  # Join the user to the specified room
    socketio.emit('user_status', {'user_id': user_id, 'status': 'online'})
                

@socketio.on('user_join')
def user_join(roomName, user_token):
    try:
        entry = Rooms.query.filter_by(room=roomName).first()
        cleaner()
        if entry:
            if user_token == entry.Tuser1:
                entry.status1 = 'online'
                db.session.commit()
            else:
                entry.status2 = 'online'
                db.session.commit()
    except Exception as e:
        print("\n\n\n\n\n\n\n\n ", e, "\n\n\n\n\n\n\n\n\n\n")



@app.route('/next', methods=['GET', 'POST'])
def next():
    try:
        # Here For delete the data of user token and username in the room
        if request.method in ['GET', 'POST']:
            next_token = request.headers.get('next_token')
            next_room = request.headers.get('room')

            # Here For delete the data of user2 token in the room
            older_entry = Rooms.query.filter_by(room=next_room).first()
            # IMportnst
            Cuser1=f"Cuser1{random.randint(0,10000)}" 
            Cuser2 = f"Cuser2{random.randint(0,10000)}" 

    #  For the null room the both user is not there then
            cleaner()

        
            # the vlue is remove 
            if older_entry.Tuser2 == next_token:
                # Clear the user2 information
                older_entry.username2, older_entry.Tuser2,older_entry.status2 = None, None,'offline'
            elif older_entry.Tuser1 == next_token:
                # Clear the user1 information
                older_entry.username1, older_entry.Tuser1,older_entry.status1 = None, None,'offline'

            db.session.commit()



            # For the Username1 and Username2
            available_room_username1 = Rooms.query.filter(and_(Rooms.username1.is_(None), Rooms.room != older_entry.room)).first()
            available_room_username2 = Rooms.query.filter(and_(Rooms.username2.is_(None), Rooms.room != older_entry.room)).first()
            if available_room_username2:
                available_room_username2.username2 = Cuser2  # Assign a username
                available_room_username2.Tuser2 = generate_twilio_token(available_room_username2.room, Cuser2)
                available_room_username2.status2 = 'online'
                db.session.commit()

                return jsonify({'room_id': available_room_username2.room, 'token': available_room_username2.Tuser2, 'username': Cuser2, 'conversationsid': conversation})
            
            elif available_room_username1:
                available_room_username1.username1 = Cuser1  # Assign a username
                available_room_username1.Tuser1 = generate_twilio_token(available_room_username1.room, Cuser1)
                available_room_username1.status1 = 'online'

                db.session.commit()

                return jsonify({'room_id': available_room_username1.room, 'token': available_room_username1.Tuser1, 'username': Cuser1, 'conversationsid': conversation})
        
            else:
                # If no available room, create a new room
                new_room_id = str(roomC())
                new_token = generate_twilio_token(new_room_id, Cuser1)  # Assign a username or identifier
                date = datetime.now()  # 2014-07-05 14:34:14 syntax
                status1 = 'online'

                entry = Rooms(room=new_room_id, username1=Cuser1, Tuser1=new_token, date=date,status1=status1)  # Corrected username1
                db.session.add(entry)
                db.session.commit()

                return jsonify({'room_id': new_room_id, 'token': new_token, 'username': Cuser1, 'conversationsid': conversation})
            
        else:
            return jsonify({'error': 'Invalid request method'})

    except Exception as e:
        print("\n\n\n\n\n\n\n\n\n\n\n\n\n Here your Error:  ",e,"\n\n\n\n\n\n\n\n")




@socketio.on('user_join_offline')
def user_join_offline(roomName, user_token):
    try:
        entryO = Rooms.query.filter_by(room=roomName).first()
        cleaner()
        if entryO:
            if user_token == entryO.Tuser1:
                entryO.status1 = 'offline'
                db.session.commit()
            elif user_token == entryO.Tuser2:
                entryO.status2 = 'offline'
                db.session.commit()
                socketio.emit('user_status', {'user_id': user_token[0:10],'roomNameof' : roomName})

    except Exception as e:
        print("\n\n\n\n\n\n\n\n here the offline error ", e, "\n\n\n\n\n\n\n\n\n\n")

@socketio.on('disconnect')
def handle_disconnect():
    try:
        user_id = request.sid
        # Emit a 'user_status' event with the user's status and associated roomName
        socketio.emit('user_status', {'user_id': user_id, 'status': 'offline'})

    except Exception as e:
        print(f"\n\n\n\n\n\n\nError handling disconnect: {e}\n\n\n\n\n\n\n\n\n")


# user_comes
@app.route('/come', methods=['GET', 'POST'])
def come():
    cleaner()
    if request.method == 'POST':
        room = roomC()
        username1 = request.form.get('username')
        Tuser1 = generate_twilio_token(room,username1)
        date = datetime.now() 
        status1 = 'online'   #2014-07-05 14:34:14 syntax
        entry = Rooms(room=room, username1=username1, Tuser1=Tuser1,date=date,status1=status1)
        db.session.add(entry)
        db.session.commit()

        # Display a waiting page for user1
        return render_template('video_call.html', room_id=room,Token = Tuser1,username = username1,conversationsid=conversation)

    # If it's a GET request, the user2 is arriving
    username2 = request.args.get('username')
    if username2:
        matching_entry = Rooms.query.filter_by(username2=None).first()
        if matching_entry:
            room_id = matching_entry.room
            Tuser2 = generate_twilio_token(room_id,username2)
            matching_entry.status2 = 'online'
            matching_entry.username2 = username2
            matching_entry.Tuser2 = Tuser2
            db.session.commit()
            return render_template('video_call.html', room_id=room_id,token1=matching_entry.Tuser1,Token = Tuser2,username = username2,conversationsid=conversation)
        else:
            # Handle the case when no matching user is available
            return redirect('/')

    return render_template('index.html')


@app.route('/DisconnectT', methods=['GET', 'POST'])
def DisconnectT():     
    try:
        cleaner()
        if request.method in ['GET', 'POST']:
            Disconnect_token = request.headers.get('token')
            Disconnect_roomname = request.headers.get('room')

            # Find the entry for the specified room
            Disconnect_entry = Rooms.query.filter_by(room=Disconnect_roomname).first()

            if Disconnect_entry:
                if Disconnect_entry.Tuser1 == Disconnect_token:
                    # Clear the user1 information
                    Disconnect_entry.Tuser1, Disconnect_entry.username1,Disconnect_entry.status1 = None, None,None
                else:
                    # Clear the user2 information
                    Disconnect_entry.Tuser2, Disconnect_entry.username2,Disconnect_entry.status1 = None, None,None

                # Commit changes to the database
                db.session.commit()
                cleaner()
                # Return a JSON response indicating success
                return jsonify({"message": "Successfully disconnected"}), 200
            else:
                return jsonify({"message": "Room not found"}), 404

        else:
            return jsonify({"message": "Invalid request method"}), 405

    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "An error occurred"}), 500



if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
