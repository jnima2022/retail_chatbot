import string
from fastapi import FastAPI, HTTPException
import sqlite3
import spacy
import re
import random
from fastapi.middleware.cors import CORSMiddleware
import difflib  # For fuzzy matching

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

app = FastAPI()

# Allow requests from the React frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Function to connect to the database
def get_db_connection():
    conn = sqlite3.connect("retail_chatbot.db")
    conn.row_factory = sqlite3.Row  # Enables column name access
    return conn

def classify_intent(user_input: str):
    """Classify the user's intent based on keywords."""
    user_input = user_input.lower()

    # Remove punctuation (like "?")
    user_input = user_input.translate(str.maketrans("", "", string.punctuation))

    # Greetings
    if re.search(r"\b(hi|hello|hey|good morning|good afternoon)\b", user_input):
        return "greeting", None

    # Goodbyes
    if re.search(r"\b(bye|thank you|thanks|thankyou|goodbye|see you|take care)\b", user_input):
        return "goodbye", None

    # Product Inquiry
    product_keywords = ["price", "cost", "available", "in stock", "have", "sell", "info"]
    if any(word in user_input for word in product_keywords):
        # Extract potential product name by removing known words
        cleaned_query = re.sub(r"\b(what|whats|do|you|is|the|of|a|an|how|much|does|cost|price|for|in stock|available|sell|have|info)\b", "", user_input)
        cleaned_query = cleaned_query.strip()
        return "product", cleaned_query

    # Product Recommendations
    if "recommend" in user_input or "suggest" in user_input:
        return "recommendation", user_input

    # Order Tracking
    if re.search(r"\b(order|track|shipment|status)\b", user_input):
        order_id_match = re.search(r"\b[a-fA-F0-9]{8}\b", user_input)  # Updated regex to match lowercase hex IDs
        return "order", order_id_match.group() if order_id_match else None

    # General FAQs
    faq_keywords = ["return", "policy", "store hours", "open", "close", "refund", "exchange"]
    if any(word in user_input for word in faq_keywords):
        return "faq", user_input
    
    # Product Detail Inquiry
    detail_keywords = ["tell me about","details of","detail of", "features of", "how is", "describe", "what is", "info on"]
    if any(word in user_input for word in detail_keywords):
        cleaned_query = re.sub(r"\b(tell me about|the|detail of|details of|features of|how is|describe|what is|info on)\b", "", user_input).strip()
        return "product_detail", cleaned_query

    return "unknown", user_input  # Default to unknown intent

@app.get("/product/{product_name}")
async def check_product(product_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE name LIKE ?", (f"%{product_name}%",))
    product = cursor.fetchone()
    conn.close()

    if product:
        return {
            "name": product["name"],
            "price": product["price"],
            "stock": product["stock"],
            "availability": "In Stock" if product["stock"] > 0 else "Out of Stock"
        }
    else:
        raise HTTPException(status_code=404, detail="Product not found")

@app.get("/order/{order_id}")
async def check_order(order_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()

    if order:
        return {
            "order_id": order["order_id"],
            "product_name": order["product_name"],
            "status": order["status"]
        }
    else:
        raise HTTPException(status_code=404, detail="Order not found")

@app.get("/chat")
async def chat(query: str):
    intent, data = classify_intent(query)

    if intent == "greeting":
        return {"response": "Hello! How can I assist you today?"}

    if intent == "goodbye":
        return {"response": "Goodbye! Have a great day!"}

    if intent == "product":
        conn = get_db_connection()
        cursor = conn.cursor()
        print(f"User query extracted: {data}")  # Debugging line

        cursor.execute("SELECT * FROM products WHERE LOWER(name) LIKE ?", (f"%{data.lower()}%",))
        product = cursor.fetchone()
        conn.close()

        if product:
            return {
                "response": f"{product['name']} is available for ${product['price']}. Stock: {product['stock']} units."
            }
        else:
            return {"response": "Sorry, we couldn't find the product you're looking for."}

    if intent == "recommendation":
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch all product names and categories
        cursor.execute("SELECT name, category FROM products")
        all_categories = [row["category"].lower() for row in cursor.fetchall()]

        words = query.lower().split()
        category = None

        # Try to match query words with available categories
        for word in words:
            matches = difflib.get_close_matches(word, all_categories, n=1, cutoff=0.7)  # Fuzzy match
            if matches:
                category = matches[0]  # Take the best-matched category
                break

        if category:
            # Recommend products from the matched category
            cursor.execute("SELECT name FROM products WHERE LOWER(category) = ? ORDER BY RANDOM() LIMIT 3", (category,))
            similar_products = cursor.fetchall()
        else:
            # Fallback to random recommendations if no category is found
            cursor.execute("SELECT name FROM products ORDER BY RANDOM() LIMIT 3")
            similar_products = cursor.fetchall()

        conn.close()

        if similar_products:
            recommended_products = ", ".join([product["name"] for product in similar_products])
            return {"response": f"Here are some recommendations: {recommended_products}."}
        else:
            return {"response": "Sorry, I couldn't find any relevant recommendations at the moment."}
    
    if intent == "order":
        if not data:
            return {"response": "Sorry, we couldn't find your order with that ID."}  # Changed response

        # Check if order ID is in the correct format
        if not re.fullmatch(r"[a-fA-F0-9]{8}", data):  
            return {"response": "Sorry, we couldn't find your order with that ID."}

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (data,))
        order = cursor.fetchone()
        conn.close()

        if order:
            return {
                "response": f"Your order {order['order_id']} is currently {order['status']}."
            }
        else:
            return {"response": "Sorry, we couldn't find your order with that ID."}


    if intent == "faq":
        return {"response": "Our store is open from 9 AM to 9 PM. Return policy allows returns within 30 days with receipt."}
    
    if intent == "product_detail":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM products WHERE LOWER(name) LIKE ?", (f"%{data.lower()}%",))
        product = cursor.fetchone()
        conn.close()

        if product:
            return {"response": f"Here are the details for {data}: {product['description']}"}
        else:
            return {"response": "Sorry, I couldn't find details for that product."}
    

    return {"response": "I'm not sure how to help with that. Could you rephrase your question?"}

#uvicorn backend:app --reload
