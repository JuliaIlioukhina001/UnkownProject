import json
import secrets
import random
import requests
import uuid
import os
from dotenv import load_dotenv
import hashlib
from deta import Deta

load_dotenv()

# Set the environment variables
CIRCLE_API_KEY = os.getenv("CIRCLE_API_KEY")
MASTER_WALLET_ID = os.getenv("MASTER_WALLET_ID")
DETA_PROJECT_KEY = os.getenv("DETA_PROJECT_KEY")

# Set the headers for the Circle API
HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {CIRCLE_API_KEY}"
}

# Initialize Deta
deta = Deta(DETA_PROJECT_KEY)


def check_username(username):
    """
    Check if a username already exists in the database.

    Args:
        username (str): The username to check.

    Returns:
        bool: True if the username exists, else False.
    """
    try:
        users_db = deta.Base("users")
        user = users_db.get(username)
        if user:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking username: {e}")
        return False


def create_wallet(username, password):
    """
    Create a wallet for a user.

    Args:
        username (str): The username of the user.
        password (str): The password of the user.

    Returns:
        tuple: A tuple containing username, wallet_id, and address if successful, else False.
    """
    try:
        url = "https://api-sandbox.circle.com/v1/wallets"
        payload = {
            "idempotencyKey": str(uuid.uuid4()),
            "description": username,
        }
        response = requests.post(url, json=payload, headers=HEADERS)
        wallet_data = response.json()
        wallet_id = wallet_data['data']['walletId']

        if wallet_id:
            salt = secrets.token_hex(16)
            hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
            address_payload = {
                "idempotencyKey": str(uuid.uuid4()),
                "currency": "USD",
                "chain": "FLOW",
            }
            address_url = f'https://api-sandbox.circle.com/v1/wallets/{wallet_id}/addresses'
            address_response = requests.post(address_url, json=address_payload, headers=HEADERS)
            address_data = address_response.json()
            users_db = deta.Base("users")
            users_db.put({
                "username": username,
                "password": hashed_password,
                "salt": salt,  # Store the salt in the database
                "wallet_id": wallet_id,
                "address": address_data['data']['address']
            }, key=username)
            user_data = {
                "username": username,
                "wallet_id": wallet_id,
                "address": address_data['data']['address']
            }
            return user_data
        else:
            return False
    except Exception as e:
        print(f"Error creating wallet: {e}")
        return False


def login_user(username, password):
    """
    Login a user

    Args:
        username (str): The username of the user.
        password (str): The password of the user.

    Returns:
        tuple: A tuple containing username, wallet_id, and address if successful, else False.
    """
    try:
        users_db = deta.Base("users")
        user = users_db.get(username)
        if user:
            salt = user['salt']
            hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
            if hashed_password == user['password']:
                user_data = {
                    "username": username,
                    "wallet_id": user['wallet_id'],
                    "address": user['address']
                }
                return user_data
            else:
                return False
        else:
            return False
    except Exception as e:
        print(f"Error logging in user: {e}")
        return False


def get_address(wallet_id):
    """
    Get the address associated with a wallet.

    Args:
        wallet_id (str): The wallet ID.

    Returns:
        str: The wallet address.
    """
    try:
        url = f'https://api-sandbox.circle.com/v1/wallets/{wallet_id}/addresses'
        response = requests.get(url, headers=HEADERS)
        address_data = response.json()
        return address_data['data'][0]['address']
    except Exception as e:
        print(f"Error getting wallet address: {e}")
        return None


def payout(wallet_id, amount):
    """
    Initiate a payout from the wallet.

    Args:
        wallet_id (str): The wallet ID.
        amount (float): The amount to be paid out.

    Returns:
        bool: True if successful, else False.
    """
    try:
        url = "https://api-sandbox.circle.com/v1/transfers"
        address = get_address(str(wallet_id))
        payload = {
            "idempotencyKey": str(uuid.uuid4()),
            "source": {"type": "wallet", "id": MASTER_WALLET_ID},
            "amount": {"amount": str(amount), "currency": "USD"},
            "destination": {"type": "blockchain", "address": address, "chain": "FLOW"}
        }
        requests.post(url, json=payload, headers=HEADERS)
        return True
    except Exception as e:
        print(f"Error initiating payout: {e}")
        return False


def get_balance(wallet_id):
    """
    Get the balance of a wallet.

    Args:
        wallet_id (str): The wallet ID.

    Returns:
        float: The wallet balance.
    """
    try:
        url = f'https://api-sandbox.circle.com/v1/wallets/{wallet_id}'
        response = requests.get(url, headers=HEADERS)
        balance_data = response.json()
        try:
            balance_data['data']['balances'][0]['amount']
            return balance_data['data']['balances'][0]['amount']
        except IndexError:
            return 0.00
    except Exception as e:
        print(f"Error getting wallet balance: {e}")
        return None


def add_goals(username, amount):
    """
    Add goals to the database for a specific user and amount. This will clear any existing goals for the user and set new ones.

    Args:
        username (str): The username of the user.
        amount (int): The total amount of goals to be added.

    Returns:
        bool: True if successful, else False.
    """
    with open("goals.json", "r") as f:
        goals = json.load(f)
    random.shuffle(goals)
    goals = goals[:amount]
    total_reward = 0
    for goal in goals:
        total_reward += float(goal['reward'])
    total_reward = round(total_reward, 2)
    rewards = {
        "value": total_reward,
        "amount": amount,
        "goals": goals
    }
    try:
        goal_db = deta.Base("goals")
        goal_db.put(rewards, key=username)
        return True
    except Exception as e:
        print(f"Error adding goals: {e}")
        return False


def remove_goal(username, goal_name):
    """
    Remove a goal from the database for a specific user and update the total reward and amount of goals.

    Args:
        username (str): The username of the user.
        goal_name (str): The name of the goal to be removed.

    Returns:
        bool: True if successful, else False.
    """
    goal_db = deta.Base("goals")
    goals = goal_db.get(username)['goals']
    for goal in goals:
        if goal['goal'] == goal_name:
            goals.remove(goal)
            break
    total_reward = 0
    for goal in goals:
        total_reward += float(goal['reward'])
    total_reward = round(total_reward, 2)
    rewards = {
        "value": total_reward,
        "amount": len(goals),
        "goals": goals
    }
    try:
        goal_db.put(rewards, key=username)
        return True
    except Exception as e:
        print(f"Error removing goal: {e}")
        return False


def get_goals(username):
    """
    Get the goals for a specific user.

    Args:
        username (str): The username of the user.

    Returns:
        dict: A dictionary containing the total reward, amount of goals, and the goals themselves.
    """
    try:
        goal_db = deta.Base("goals")
        goals = goal_db.get(username)
        return goals
    except Exception as e:
        print(f"Error getting goals: {e}")
        return None


def get_goal(username, goal_name):
    """
    Gets the details of a specific goal for a user.

    Args:
        username (str): The username of the user.
        goal_name (str): The name of the goal to be retrieved.

    Returns:
        dict: A dictionary containing the goal details.
    """

    goals = get_goals(username)['goals']
    for goal in goals:
        if goal['goal'] == goal_name:
            return goal
    return None


def add_image(image):
    """
    Add an image to the database.

    Args:
        image (bytes) The image to be added.

    Returns:
        bool: True if successful, else False.
    """
    try:
        image_db = deta.Drive("images")
        image_name = f"{random.randint(0, 1000000000)}.jpg"
        image_db.put(image, f"{image_name}.jpg")
        return image_name
    except Exception as e:
        print(f"Error adding image: {e}")
        return False


def complete_goal(username, goal_name, image):
    """
    Complete a goal for a user. This will remove the goal and payout the reward to the user. It will also update the
    total reward and amount of goals as well as adding the goal to the completed goals' database.


    Args:
        username (str): The username of the user.
        goal_name (str): The name of the goal to be completed.

    Returns:
        bool: True if successful, else False.
    """
    goal = get_goal(username, goal_name)
    if goal:
        remove_goal(username, goal_name)
        payout(username, goal['reward'])
        image_name = add_image(image)
        if not image_name:
            return False
        goal_db = deta.Base("completed_goals")
        goal_db.put({
            "username": username,
            "goal": goal_name,
            "reward": goal['reward'],
            "image": image_name

        })
        return True
    else:
        print("Possible payout theft detected!")
        return False
