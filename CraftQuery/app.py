from flask import Flask, request, jsonify, session, render_template
import psycopg2
import openai

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Configure OpenAI API
openai.api_key = 

# Database configuration
db_config = {
    'dbname': 'QueryCraft',
    'user': 'postgres',
    'password': 'Karthik@1234',
    'host': 'localhost',
    'port': 5432
}

# Utility to execute a database query
def execute_query(query):
    try:
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if query.strip().lower().startswith("select"):
                    return cursor.fetchall()
                conn.commit()
                return "Query executed successfully"
    except Exception as e:
        return str(e)

# Utility to call Gemini AI
def call_gemeni_ai(history_text, user_query):
    prompt = f"""{history_text}
    Give me the syntax for the following command in SQL so that the response can 
    directly be sent to PostgreSQL to receive the output. user input:{user_query}
    and also add another field prompt which should have the prompt that should be again sent back 
    to you for formatting the raw database response in the way user has asked in the user input.
    if you are directly giving the query that needs to be executed in the database then give response in below format:
    The response should be in JSON format with fields: 
    'option':1
    'query': query given by you
    'prompt': the prompt I need to send back with the raw db response to get result in required format
    and please do make sure that the query starts with select if it should return some
    content from the Postgres and don't use any \n
    If you want some additional information from the database so that you can review some data or 
    information sent back to you give response in below format:
    'option':2
    'query': query you want to give to db so that you can review the information
    'prompt': further prompt I need to give you so that you can give the actual query to send to db

    Else if you want any additional information from the user then choose:
    'option':3
    'prompt': further prompt I should give you
    take care that the query should be a single command such that the query given by you is directly executed in db"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant for SQL query generation."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

@app.route("/start_session", methods=["POST"])
def start_session():
    session['history'] = []
    return jsonify({"message": "Session started and history initialized."})

@app.route("/process_command", methods=["POST"])
def process_command():
    user_input = request.json.get("command")
    if not user_input:
        return jsonify({"error": "No command provided."}), 400

    history_text = "\n".join(session.get("history", []))
    ai_response = call_gemeni_ai(history_text, user_input)

    try:
        ai_response_json = eval(ai_response)  # Use with caution; ensure trusted input
    except Exception as e:
        return jsonify({"error": f"Failed to parse AI response: {e}"}), 500

    if ai_response_json.get("option") == 1:
        query = ai_response_json.get("query")
        prompt = ai_response_json.get("prompt")
        db_response = execute_query(query)
        formatted_response = call_gemeni_ai(history_text + f"\nDB Response: {db_response}", prompt)
        session['history'].append(f"User: {user_input}\nAI: {ai_response}\nDB: {db_response}\nFormatted: {formatted_response}")
        return jsonify({"formatted_response": formatted_response})

    elif ai_response_json.get("option") == 2:
        query = ai_response_json.get("query")
        prompt = ai_response_json.get("prompt")
        db_response = execute_query(query)
        ai_followup = call_gemeni_ai(history_text + f"\nDB Response: {db_response}", prompt)
        session['history'].append(f"User: {user_input}\nAI: {ai_response}\nDB: {db_response}\nAI Followup: {ai_followup}")
        return jsonify({"ai_followup": ai_followup})

    elif ai_response_json.get("option") == 3:
        prompt = ai_response_json.get("prompt")
        session['history'].append(f"User: {user_input}\nAI: {ai_response}\nPrompt: {prompt}")
        return jsonify({"additional_info_request": prompt})

    else:
        return jsonify({"error": "Invalid option from AI response."}), 500

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
