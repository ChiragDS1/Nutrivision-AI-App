# nutrivision_app.py
import streamlit as st
import sqlite3
from openai import OpenAI
from PIL import Image
from io import BytesIO
import base64

# Setup OpenAI API Key
client = OpenAI(api_key=st.secrets["openai_api_key"])

# --- DB SETUP ---
conn = sqlite3.connect('nutrivision_users2.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER, gender TEXT, body_type TEXT, activity_level TEXT, bmi REAL, goal TEXT, weight_loss_rate TEXT, workout_type TEXT, gym_focus TEXT)''')
conn.commit()

# --- AUTH ---
def signup(username, password):
    c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    conn.commit()

def login(username, password):
    c.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
    return c.fetchone()

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Nutrivision AI", layout="wide")
    st.title("Nutrivision AI")

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    if not st.session_state['logged_in']:
        menu = ["Login", "Sign Up"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Sign Up":
            st.subheader("Create New Account")
            new_user = st.text_input("Username")
            new_pass = st.text_input("Password", type='password')
            if st.button("Sign Up"):
                signup(new_user, new_pass)
                st.success("Account created successfully! You can now log in.")

        elif choice == "Login":
            st.subheader("Login to Your Account")
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                user = login(username, password)
                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = user[0]
                    st.success(f"Welcome {username}!")
                    st.experimental_rerun()
                    return
                else:
                    st.warning("Incorrect Username/Password")
        return

    page = st.sidebar.selectbox("Go to", ["User Profile", "Diet Plan", "Workout Plan", "Freshness Checker", "Dish Identifier", "Logout"])

    if page == "User Profile":
        profile_page(st.session_state['user_id'])
    elif page == "Diet Plan":
        show_diet_plan(st.session_state['user_id'])
    elif page == "Workout Plan":
        show_workout_plan(st.session_state['user_id'])
    elif page == "Freshness Checker":
        analyze_freshness()
    elif page == "Dish Identifier":
        identify_dish()
    elif page == "Logout":
        st.session_state.clear()
        st.experimental_rerun()

# --- PROFILE & SURVEY ---
def profile_page(user_id):
    st.header("User Fitness Profile")

    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    body_type = st.selectbox("Body Type", ["Ectomorph : Lean Body", "Mesomorph : Average Body", "Endomorph : Bulky or Fat"])
    activity = st.selectbox("Physical Activity Level", ["Low: 1-2 days a week", "Moderate: 3-5 days a week", "High: Almost Everyday"])
    height = st.number_input("Height (m)")
    weight = st.number_input("Weight (kg)")
    goal = st.selectbox("Fitness Goal", ["Lose Fat", "Gain Muscle", "Maintain"])

    weight_loss_rate = ""
    if goal == "Lose Fat":
        weight_loss_rate = st.selectbox("How fast do you want to lose weight?", ["0.5 kg/week", "0.8 kg/week", "1.0 kg/week"])

    workout_type = st.selectbox("Do you workout in a gym or do you prefer bodyweight exercises?", ["Gym", "Bodyweight"])
    gym_focus = ""
    if workout_type == "Gym":
        gym_focus = st.selectbox("What kind of workout do you prefer at the gym?", ["Cardio Heavy", "Strength Training Focused", "Mix of Both"])

    if height and weight:
        bmi = round(weight / (height ** 2), 2)
        st.write(f"Calculated BMI: {bmi}")

    if st.button("Save Profile"):
        c.execute('INSERT INTO profiles (user_id, gender, body_type, activity_level, bmi, goal, weight_loss_rate, workout_type, gym_focus) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                  (user_id, gender, body_type, activity, bmi, goal, weight_loss_rate, workout_type, gym_focus))
        conn.commit()
        st.success("Profile saved successfully!")

# --- DIET PLAN PAGE ---
def show_diet_plan(user_id):
    st.header("Personalised Diet Plan")

    c.execute('SELECT gender, body_type, activity_level, bmi, goal, weight_loss_rate FROM profiles WHERE user_id=? ORDER BY rowid DESC LIMIT 1', (user_id,))
    row = c.fetchone()

    if row:
        gender, body_type, activity, bmi, goal, weight_loss_rate = row
        extra_note = f" The user wishes to lose weight at a rate of {weight_loss_rate}." if goal == "Lose Fat" and weight_loss_rate else ""
        prompt = f"""
        Create a personalized weekly diet plan for a {gender} {body_type} with {activity} activity level, BMI of {bmi}, and a goal to {goal.lower()}.
        {extra_note}
        Format it clearly with daily meal breakdowns.
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a Nutrition Specialist AI assistant that is designed to create diet plans."},
                {"role": "user", "content": prompt}
            ]
        )
        plan = response.choices[0].message.content
        st.markdown(plan)
    else:
        st.warning("No profile data found. Please fill out your profile first.")

# --- WORKOUT PLAN PAGE ---
def show_workout_plan(user_id):
    st.header("Personalised Workout Plan")

    c.execute('SELECT gender, activity_level, goal, workout_type, gym_focus FROM profiles WHERE user_id=? ORDER BY rowid DESC LIMIT 1', (user_id,))
    row = c.fetchone()

    if row:
        gender, activity, goal, workout_type, gym_focus = row
        gym_note = f"The user works out at a gym with a preference for {gym_focus.lower()} training." if workout_type == "Gym" else "The user does bodyweight workouts."
        prompt = f"""
        Create a personalized weekly workout plan for a {gender} individual who does {workout_type.lower()} workouts with an activity level of {activity} and a fitness goal to {goal.lower()}.
        {gym_note}
        Ensure the plan covers all major muscle groups over the week with appropriate recovery.
        """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional fitness coach. Design personalized weekly workout plans."},
                {"role": "user", "content": prompt}
            ]
        )
        workout_plan = response.choices[0].message.content
        st.markdown(workout_plan)
    else:
        st.warning("No profile data found. Please fill out your profile first.")
# --- IMAGE FRESHNESS ANALYSIS ---
def analyze_freshness():
    st.header("Check Freshness of Fruits/Vegetables")
    uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        image = image.convert("RGB")
        st.image(image, caption='Uploaded Image', use_column_width=True)
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        img_bytes = base64.b64encode(buffer.getvalue()).decode()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a fruit and vegetable quality inspector. You analyze images of produce to determine their freshness based on color, texture, mold presence, bruises, and overall condition."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Is this fruit or vegetable fresh? Give reasons."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_bytes}"}}
                ]}
            ]
        )
        st.markdown(response.choices[0].message.content)

# --- DISH IDENTIFICATION ---
def identify_dish():
    st.header("Identify Dish and Nutritional Value")
    uploaded_file = st.file_uploader("Upload Dish Image", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        image = image.convert("RGB")
        st.image(image, caption='Dish Image', use_column_width=True)
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        img_bytes = base64.b64encode(buffer.getvalue()).decode()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional food analyst. Your job is to identify dishes from images and estimate their nutritional information including calories, protein, carbs, fat, and sugar content."},
                {"role": "user", "content": [
                    {"type": "text", "text": "Identify the dish and provide its approximate nutritional value (calories, protein, carbs, fat, sugar)."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_bytes}"}}
                ]}
            ]
        )
        st.markdown(response.choices[0].message.content)

if __name__ == '__main__':
    main()
