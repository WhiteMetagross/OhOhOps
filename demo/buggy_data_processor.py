import json

def process_data(data_string):
    """
    Parses a JSON string containing user data and calculates the average age.
    """
    data = json.loads(data_string)
    
    # Bug 1: The payload below uses "user_list", but this code looks for "users".
    # This will throw a KeyError. 
    users = data['response']['users']
    
    total_age = 0
    for user in users:
        # Bug 2: The age in the payload is a string (e.g. "25"), not an int.
        # This will throw a TypeError: unsupported operand type(s) for +=: 'int' and 'str'.
        # If the LLM only fixes Bug 1, the sandbox will execute, fail on Bug 2, 
        # and the graph will LOOP BACK for a second repair attempt.
        total_age += user['age']
        
    return total_age / len(users) if users else 0.0

if __name__ == "__main__":
    # Hardcoded payload to simulate an API response
    payload = '''
    {
        "status": "success",
        "response": {
            "user_list": [
                {"name": "Alice", "age": "25"},
                {"name": "Bob", "age": "30"},
                {"name": "Charlie", "age": "35"}
            ]
        }
    }
    '''
    
    print("Initializing data processor...")
    avg = process_data(payload)
    print(f"Calculated average age: {avg}")
