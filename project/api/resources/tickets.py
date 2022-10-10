import pandas as pd
from flask import jsonify
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_restful import Resource, reqparse
from flask_user import current_user
from flask_login import login_required
from sqlalchemy.orm import load_only
from sqlalchemy.sql.expression import func

from project.config import Config
from project.database import db
from project.models import Text, Ticket, ActivityStreak


class GetTextPostTicket(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('text',
                        type=int,
                        required=True,
                        help='missing text ID'
                        ),
    parser.add_argument('emotion',
                        type=int,
                        required=True,
                        help='missing emotion ID'
                        ),
    parser.add_argument('user',
                        type=int,
                        required=True,
                        help='missing user ID'
                        ),
    parser.add_argument('secret',
                        type=str,
                        required=True,
                        help='missing secret'
                        )

    @login_required
    def get(self):
        """
        returns a dictionary with data which should be used to submit a ticket. the keys are: user, secret, text
        :user: ID of current_user (currently logged-in user which will be the author of the submitted ticket)
        :secret: generates a hash of the app's SECRET_KEY which is required to submit a ticket
        :text: a dictionary containing attributes of a Text object as its keys (id (int), text (str), file (int))
        """
        user_marked_texts = Ticket.query.filter_by(user=current_user.id)     # marked_texts.text.to_list()
        user_marked_text_ids_list = [i.text for i in user_marked_texts]

        # get texts not yet marked by user, based on marked texts
        user_unmarked_texts = Text.query.filter(Text.id.notin_(user_marked_text_ids_list))

        random_text = user_unmarked_texts.order_by(func.random()).first()  # get a random text out of on unmarked texts

        if random_text.text:  # if there is an unmarked text left
            secret = generate_password_hash(Config.SECRET_KEY)  # hash the SECRET_KEY

            # create a response dictionary and add text, user and secret keys
            response = dict(random_text.__dict__)  # convert the randomly selected Text object to type dict
            response.pop('_sa_instance_state')  # remove an unnecessary key from the Text dictionary
            # add user id to response dictionary and secret key converted to JSON
            response.update(user=current_user.id, secret=secret.decode('utf8').replace("'", '"'))
            return jsonify(response)

        else:  # if there are no unmarked texts, return False so the ticket view notifies the user accordingly
            return False

    @login_required
    def post(self):
        """
        adds a ticket to db based on current_user ID, received text ID and
        """

        data = GetTextPostTicket.parser.parse_args()
        if check_password_hash(data['secret'], Config.SECRET_KEY) and current_user.id == data['user']:
            net_ticket = Ticket(current_user.id, data['text'], data['emotion'] + 1)
            net_ticket.save_to_db()

            # create or update streak
            current_streak = ActivityStreak.query.filter_by(user=current_user.id, status=1).first()

            if current_streak and current_streak.update_streak():
                pass  # update_streak updates an active streak upon being called
            else:
                new_streak = ActivityStreak(current_user.id)
                db.session.add(new_streak)
                db.session.commit()

            return {'success': 'ticket added'}, 200

        else:  # if the secret is wrong (user didn't use the website to submit the ticket)
            return {'error': 'Secret_key is wrong. Use the website to send requests'}, 400
