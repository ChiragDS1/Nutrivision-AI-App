# === IMPORTS ===
import streamlit as st
import sqlite3
import hashlib
import base64
import uuid
import bcrypt
import time
import datetime
import pandas as pd
import re
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import plotly.express as px
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from openai import OpenAI

# === GLOBAL SETUP ===
conn = sqlite3.connect('nutrivision_users.db', check_same_thread=False)
c = conn.cursor()
client = OpenAI(api_key=st.secrets["openai_api_key"])
# --- DB SETUP ---
c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, 
    email TEXT UNIQUE, 
    username TEXT UNIQUE, 
    password TEXT,
    reset_token TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER,
    name TEXT,
    gender TEXT,
    body_type TEXT,
    activity_level TEXT,
    height REAL,
    weight REAL,
    bmi REAL,
    goal TEXT,
    weight_loss_rate TEXT,
    workout_type TEXT,
    gym_focus TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
c.execute('''CREATE TABLE IF NOT EXISTS diet_plans (
    user_id INTEGER,
    profile_hash TEXT,
    plan TEXT,
    diet_type TEXT,
    allergens TEXT,
    other_allergy TEXT,
    health_conditions TEXT,
    supplements TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
c.execute('''CREATE TABLE IF NOT EXISTS workout_plans (
    user_id INTEGER,
    plan TEXT,
    workout_time_pref TEXT,
    duration_pref TEXT,
    injuries TEXT,
    equipment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
c.execute('''CREATE TABLE IF NOT EXISTS diet_feedback (
    user_id INTEGER,
    plan TEXT,
    rating INTEGER,
    feedback TEXT,
    compliance TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
# --- HASHING UTILS ---
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- PAGE CONFIG FOR RESPONSIVENESS ---
st.set_page_config(page_title="Nutrivision AI", layout="centered")

# --- MOBILE FRIENDLY UI TIP ---
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stTextInput>div>input {
        font-size: 16px;
    }
    .stSelectbox>div>div {
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

def home():
    st.title("Welcome to Nutrivision AI 🥦💪")

    st.markdown("""
    ### 🧠 Project Vision
    Nutrivision AI is an innovative health and wellness assistant designed to empower individuals in making informed dietary and fitness choices. Using advanced AI, our platform personalizes meal plans, workout routines, and food quality analysis—all in one place.

    ### 👥 About the Team
    We are a group of passionate students and developers from University Of Illinois at Chicago working on Nutrivision AI as part of a research-driven capstone. Our goal is to use artificial intelligence to make nutrition accessible, personalized, and fun.

    ### 🚀 Why We Started
    We realized that many individuals struggle to maintain healthy habits due to a lack of guidance and clarity on what works for their body. We wanted to build a platform that bridges this gap through technology.

    ### 🎯 Our Approach
    - Personal health profiles
    - AI-generated diet and workout plans
    - Image-based food freshness & dish identification
    - Clean dashboard with visual health insights

    ### 🔐 Get Started
    Use the menu on the top-left to **Sign Up** or **Login** and begin your personalized journey toward better health!
    """)

# --- AUTH ---
def signup(email, username, password):
    if not email or not username or not password:
        st.warning("Email, username, and password cannot be empty.")
        return False
    if len(username) > 30:
        st.warning("Username too long (max 30 characters).")
        return False
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
        st.warning("Please enter a valid email address.")
        return False

    # --- Password strength validation ---
    if len(password) < 8:
        st.warning("Password must be at least 8 characters long.")
        return False
    if not re.search(r"[A-Z]", password):
        st.warning("Password must contain at least one uppercase letter.")
        return False
    if not re.search(r"[a-z]", password):
        st.warning("Password must contain at least one lowercase letter.")
        return False
    if not re.search(r"\d", password):
        st.warning("Password must contain at least one digit.")
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        st.warning("Password must contain at least one special character.")
        return False

    hashed_pw = hash_password(password)

    try:
        c.execute('INSERT INTO users (email, username, password) VALUES (?, ?, ?)', (email, username, hashed_pw))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        if "email" in str(e):
            st.warning("Email already exists. Please use a different one.")
        elif "username" in str(e):
            st.warning("Username already exists. Please choose another.")
        else:
            st.warning("An account already exists with the provided details.")
        return False
    except Exception as e:
        st.error("An unexpected error occurred during signup.")
        print(e)
        return False

def login(identifier, password):
    try:
        c.execute('SELECT * FROM users WHERE username=? OR email=?', (identifier, identifier))
        user = c.fetchone()
        if user and check_password(password, user[3]):
            return user
        else:
            return None
    except Exception as e:
        st.error("Login failed due to an unexpected error.")
        print(e)
        return None
# --- FORGOT PASSWORD ---
def initiate_password_reset(email):
    c.execute('SELECT id FROM users WHERE email=?', (email,))
    user = c.fetchone()
    if not user:
        st.warning("No user found with that email.")
        return
    token = str(uuid.uuid4())
    c.execute('UPDATE users SET reset_token=? WHERE email=?', (token, email))
    conn.commit()
    st.success(f"Reset token generated. Use this token to reset your password: {token}")

def reset_password_with_token(email, token, new_password):
    c.execute('SELECT reset_token FROM users WHERE email=?', (email,))
    row = c.fetchone()
    if not row or row[0] != token:
        st.error("Invalid token or email.")
        return False
    hashed_pw = hash_password(new_password)
    c.execute('UPDATE users SET password=?, reset_token=NULL WHERE email=?', (hashed_pw, email))
    conn.commit()
    st.success("Password successfully reset.")
    return True

# --- LOGIN EXTENSION: FORGOT PASSWORD ---
def forgot_password_ui():
    st.subheader("🔑 Forgot Password")
    email = st.text_input("Enter your registered email")
    if st.button("Generate Reset Token"):
        initiate_password_reset(email)

    with st.expander("Reset Password using Token"):
        reset_email = st.text_input("Email for password reset")
        token = st.text_input("Enter your reset token")
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm New Password", type="password")
        if st.button("Reset Password"):
            if new_pass != confirm_pass:
                st.warning("Passwords do not match.")
            else:
                reset_password_with_token(reset_email, token, new_pass)

# --- MAIN APP ---
def main():
    # --- Session Timeout Handling ---
    if 'last_active' in st.session_state and (time.time() - st.session_state['last_active'] > 1800):
        st.session_state.clear()
        st.warning("Session expired due to inactivity. Please log in again.")
        st.stop()

    st.session_state['last_active'] = time.time()
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None

    if not st.session_state['logged_in']:
        home()
        with st.sidebar:
            menu = st.radio("Navigate", ["Login", "Sign Up", "Forgot Password"])

            if menu == "Sign Up":
                st.subheader("Create New Account")
                email = st.text_input("Email")
                new_user = st.text_input("Username")
                new_pass = st.text_input("Password", type='password')
                if st.button("Sign Up"):
                    if signup(email, new_user, new_pass):
                        st.success("Account created successfully! You can now log in.")

            elif menu == "Login":
                st.subheader("Login to Your Account")
                identifier = st.text_input("Email or Username")
                password = st.text_input("Password", type='password')
                if st.button("Login"):
                    user = login(identifier, password)
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user[0]
                        st.success(f"Welcome {user[2]}! Redirecting to Dashboard...")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.warning("Incorrect Username/Email or Password")

            elif menu == "Forgot Password":
                forgot_password_ui()

        return

    page = st.sidebar.selectbox("Go to", [
        "Dashboard",
        "User Profile",
        "Diet Plan",
        "Past Diet Plans",
        "Workout Plan",
        "Past Workout Plans",
        "Freshness Checker",
        "Dish Identifier",
        "Rate Diet Plan",
        "Logout"])

    if page == "Dashboard":
        dashboard(st.session_state['user_id'])
    elif page == "User Profile":
        profile_page(st.session_state['user_id'])
    elif page == "Diet Plan":
        show_diet_plan(st.session_state['user_id'])
    elif page == "Past Diet Plans":
        view_past_diet_plans(st.session_state['user_id'])
    elif page == "Workout Plan":
        show_workout_plan(st.session_state['user_id'])
    elif page == "Past Workout Plans":
        view_past_workout_plans(st.session_state['user_id'])
    elif page == "Freshness Checker":
        analyze_freshness()
    elif page == "Dish Identifier":
        identify_dish()
    elif page == "Rate Diet Plan":
        rate_diet_plan(st.session_state['user_id'])
    elif page == "Logout":
        if st.button("Confirm Logout"):
            st.session_state.clear()
            st.success("You have been logged out.")
            time.sleep(1.2)
            st.rerun()
# --- DASHBOARD ---
def dashboard(user_id):
    global c
    st.header("User Summary Dashboard")
    c.execute('SELECT * FROM profiles WHERE user_id=? ORDER BY rowid DESC LIMIT 1', (user_id,))
    row = c.fetchone()

    if row:
        labels = ["Name", "Gender", "Body Type", "Activity Level", "Height", "Weight", "BMI", "Goal", "Weight Loss Rate", "Workout Type", "Gym Focus"]
        st.subheader("📋 Latest Profile Information")
        for i, label in enumerate(labels):
            value = row[i + 1] if row[i + 1] is not None else "N/A"
            st.markdown(f"**{label}:** {value}")

        # --- BMI Trend Chart ---
        c.execute('SELECT created_at, bmi FROM profiles WHERE user_id=? AND bmi IS NOT NULL ORDER BY created_at', (user_id,))
        data = c.fetchall()
        if data:
            dates, bmis = zip(*data)
            df = pd.DataFrame({"Date": pd.to_datetime(dates), "BMI": bmis})
            st.subheader("📈 BMI Trend Over Time")
            fig = px.line(df, x='Date', y='BMI', markers=True, title='BMI Trend Over Time', template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)

        # --- Activity Level Summary Chart ---
        c.execute('SELECT activity_level, COUNT(*) FROM profiles WHERE user_id=? GROUP BY activity_level', (user_id,))
        activity_data = c.fetchall()
        if activity_data:
            levels, counts = zip(*activity_data)
            st.subheader("🏃‍♂️ Activity Level Distribution")
            fig = px.bar(x=levels, y=counts, title="Activity Frequency by Level", labels={'x': 'Activity Level', 'y': 'Count'}, template='plotly_dark')
            st.plotly_chart(fig, use_container_width=True)

        # --- Summary Cards ---
        st.subheader("📊 Quick Stats")
        col1, col2 = st.columns(2)
        c.execute('SELECT COUNT(*) FROM diet_plans WHERE user_id=?', (user_id,))
        diet_count = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM workout_plans WHERE user_id=?', (user_id,))
        workout_count = c.fetchone()[0]
        with col1:
            st.metric(label="Diet Plans Generated", value=diet_count)
        with col2:
            st.metric(label="Workout Plans Generated", value=workout_count)

    else:
        st.warning("No profile data available. Please fill out your profile.")
# --- PROFILE & SURVEY ---
def get_profile_defaults(profile):
    if not profile:
        return {
            'name': "",
            'gender': "Male",
            'body_type': "Ectomorph : Lean Body",
            'activity': "Low: 1-2 days a week",
            'height': 0.0,
            'weight': 0.0,
            'goal': "Lose Fat",
            'weight_loss_rate': "0.5 kg/week",
            'workout_type': "Gym",
            'gym_focus': "Cardio Heavy"
        }

    return {
        'name': profile[1],
        'gender': profile[2] if profile[2] in ["Male", "Female", "Other"] else "Male",
        'body_type': profile[3] if profile[3] in ["Ectomorph : Lean Body", "Mesomorph : Average Body", "Endomorph : Bulky or Fat"] else "Ectomorph : Lean Body",
        'activity': profile[4] if profile[4] in ["Low: 1-2 days a week", "Moderate: 3-5 days a week", "High: Almost Everyday"] else "Low: 1-2 days a week",
        'height': profile[5] if profile[5] else 0.0,
        'weight': profile[6] if profile[6] else 0.0,
        'goal': profile[8] if profile[8] in ["Lose Fat", "Gain Muscle", "Maintain"] else "Lose Fat",
        'weight_loss_rate': profile[9] if profile[9] else "0.5 kg/week",
        'workout_type': profile[10] if profile[10] in ["Gym", "Bodyweight"] else "Gym",
        'gym_focus': profile[11] if profile[11] in ["Cardio Heavy", "Strength Training Focused", "Mix of Both"] else "Cardio Heavy"
    }
def profile_page(user_id):
    st.header("User Fitness Profile")

    c.execute('SELECT * FROM profiles WHERE user_id=? ORDER BY rowid DESC LIMIT 1', (user_id,))
    prev_profile = c.fetchone()
    defaults = get_profile_defaults(prev_profile)

    name = st.text_input("Full Name", value=defaults['name'])
    gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(defaults['gender']))
    body_type = st.selectbox("Body Type", ["Ectomorph : Lean Body", "Mesomorph : Average Body", "Endomorph : Bulky or Fat"],
                             index=["Ectomorph : Lean Body", "Mesomorph : Average Body", "Endomorph : Bulky or Fat"].index(defaults['body_type']))
    activity = st.selectbox("Physical Activity Level", ["Low: 1-2 days a week", "Moderate: 3-5 days a week", "High: Almost Everyday"],
                            index=["Low: 1-2 days a week", "Moderate: 3-5 days a week", "High: Almost Everyday"].index(defaults['activity']))

    height = st.number_input("Height (in meters)", min_value=0.0, max_value=3.0, step=0.01, value=defaults['height'])
    weight = st.number_input("Weight (in kg)", min_value=0.0, max_value=300.0, step=0.5, value=defaults['weight'])

    goal = st.selectbox("Fitness Goal", ["Lose Fat", "Gain Muscle", "Maintain"],
                        index=["Lose Fat", "Gain Muscle", "Maintain"].index(defaults['goal']))

    weight_loss_rate = ""
    if goal == "Lose Fat":
        weight_loss_rate = st.selectbox("How fast do you want to lose weight?", ["0.5 kg/week", "0.8 kg/week", "1.0 kg/week"],
                                        index=["0.5 kg/week", "0.8 kg/week", "1.0 kg/week"].index(defaults['weight_loss_rate']))

    workout_type = st.selectbox("Preferred Workout Mode", ["Gym", "Bodyweight"],
                                index=["Gym", "Bodyweight"].index(defaults['workout_type']))
    gym_focus = ""
    if workout_type == "Gym":
        gym_focus = st.selectbox("Gym Focus", ["Cardio Heavy", "Strength Training Focused", "Mix of Both"],
                                 index=["Cardio Heavy", "Strength Training Focused", "Mix of Both"].index(defaults['gym_focus']))

    if height > 0 and weight > 0:
        bmi = round(weight / (height ** 2), 2)
        st.success(f"Calculated BMI: {bmi}")
    else:
        bmi = 0
        st.warning("Enter valid height and weight to calculate BMI.")

    if st.button("Save Profile"):
        if not all([name, gender, body_type, activity, goal, workout_type]) or (goal == "Lose Fat" and not weight_loss_rate) or (workout_type == "Gym" and not gym_focus):
            st.error("Please fill out all required fields.")
        elif height <= 0 or weight <= 0:
            st.error("Height and Weight must be greater than 0.")
        else:
            try:
                c.execute('''
                    INSERT INTO profiles (
                        user_id, name, gender, body_type, activity_level,
                        height, weight, bmi, goal, weight_loss_rate,
                        workout_type, gym_focus
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, name, gender, body_type, activity, height, weight, bmi, goal, weight_loss_rate, workout_type, gym_focus))
                conn.commit()
                st.success("Profile saved successfully!")
            except Exception as e:
                st.error("Failed to save profile.")
                print("Profile DB error:", e)

# --- DIET PLAN PAGE ---
def show_diet_plan(user_id):
    st.header("Personalised Diet Plan")

    st.subheader("📝 Tell us a bit more about your dietary habits")

    diet_type = st.selectbox("What is your dietary type?", ["", "Vegetarian", "Eggetarian", "Non-Vegetarian", "Vegan"])

    common_allergens = ["Dairy", "Gluten", "Peanuts", "Tree nuts", "Soy", "Shellfish", "Eggs", "None"]
    allergens = st.multiselect("Do you have any food allergies?", options=common_allergens)
    other_allergy = st.text_input("Any other allergies not listed above? (Optional)")

    health_conditions = st.multiselect(
        "Do you have any health conditions that require a specific diet?",
        options=["Diabetes", "Thyroid", "Hypertension", "Celiac Disease", "PCOS", "High Cholesterol", "Gout", "None"]
    )

    supplements = st.multiselect(
        "Do you consume any of the following supplements?",
        options=["Protein Shakes", "Multivitamins", "Omega-3", "Creatine", "Iron Supplements", "None"]
    )

    if diet_type and (allergens or other_allergy) and health_conditions and supplements:
        regenerate = st.button("Generate / Regenerate Diet Plan")
    else:
        st.info("Please answer all the questions above to generate your personalized diet plan.")
        return

    c.execute('SELECT gender, body_type, activity_level, bmi, goal, weight_loss_rate FROM profiles WHERE user_id=? ORDER BY rowid DESC LIMIT 1', (user_id,))
    row = c.fetchone()

    if row:
        _, _, _, bmi, _, _ = row
        if not bmi or bmi < 10:
            st.warning("BMI value is too low or missing. Please update your profile with valid height and weight.")
            return

        profile_str = ''.join(map(str, row)) + diet_type + ''.join(allergens) + other_allergy + ''.join(health_conditions) + ''.join(supplements)
        profile_hash = hashlib.md5(profile_str.encode()).hexdigest()

        if not regenerate:
            c.execute('SELECT plan FROM diet_plans WHERE user_id=? AND profile_hash=?', (user_id, profile_hash))
            existing = c.fetchone()
            if existing:
                st.markdown(existing[0])
                st.download_button("Download Diet Plan", existing[0], file_name="diet_plan.txt")
                return

        gender, body_type, activity, bmi, goal, weight_loss_rate = row

        # Try to fetch last feedback
        c.execute('SELECT rating, feedback, compliance FROM diet_feedback WHERE user_id=? ORDER BY created_at DESC LIMIT 1', (user_id,))
        feedback_row = c.fetchone()
        feedback_note = f"User previously rated the plan {feedback_row[0]}/5, compliance: {feedback_row[2]}. Feedback: {feedback_row[1]}" if feedback_row else ""

        extra_note = f"The user wishes to lose weight at a rate of {weight_loss_rate}." if goal == "Lose Fat" and weight_loss_rate else ""

        prompt = f"""
        Create a personalized 7-day diet plan for a {diet_type} {gender} {body_type} individual with a physical activity level of {activity}, a BMI of {bmi}, and a goal to {goal.lower()}.
        {extra_note}
        {feedback_note}

        Additional considerations:
        - Allergies: {', '.join(allergens + [other_allergy]) if allergens or other_allergy else "None"}
        - Health Conditions: {', '.join(health_conditions) if health_conditions else "None"}
        - Supplements: {', '.join(supplements) if supplements else "None"}

        Follow this fixed structure strictly:
        1. Start with a header: "7-Day Diet Plan for [Gender] [Body Type]"
        2. Include "Daily Nutritional Goals" and macronutrient breakdown
        3. For each Day (Day 1 to Day 7), include the following sections:
           - **Breakfast**, **Morning Snack**, **Lunch**, **Evening Snack**, **Dinner**
           - Under each, include:
               - Food items with quantities
               - Macronutrients: Protein, Carbs, Fats
               - Calories
        4. End each day with:
           - **Daily Totals**: Total Protein, Carbs, Fats, Calories
        5. Use Markdown formatting (### Day X, **Meal Title**, etc.)

        Do not skip or reorder any parts. Always use consistent formatting, structure, and language across all days.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.5,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": "You are a certified dietitian and nutrition expert helping users make safe, balanced diet plans."},
                {"role": "user", "content": prompt}
            ]
        )

        plan = response.choices[0].message.content
        st.markdown(plan)
        st.download_button("Download Diet Plan", plan, file_name="diet_plan.txt")
        c.execute('INSERT INTO diet_plans (user_id, profile_hash, plan, diet_type, allergens, other_allergy, health_conditions, supplements, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
          (user_id, profile_hash, plan, diet_type, ','.join(allergens), other_allergy, ','.join(health_conditions), ','.join(supplements), datetime.datetime.now()))
        conn.commit()

def rate_diet_plan(user_id):
    st.header("Rate & Give Feedback on Your Diet Plan")

    c.execute('SELECT plan, created_at FROM diet_plans WHERE user_id=? ORDER BY created_at DESC LIMIT 1', (user_id,))
    row = c.fetchone()
    if not row:
        st.warning("No diet plan found. Please generate one first.")
        return

    st.subheader("📋 Your Current Plan")
    st.markdown(row[0])
    st.markdown("---")

    rating = st.slider("Rate this diet plan (1-5 stars):", 1, 5, 3)
    feedback = st.text_area("Additional feedback (optional):")
    compliance = st.selectbox("Were you able to follow this plan?", ["Yes", "Partially", "No"])

    if st.button("Submit Feedback"):
        c.execute('''CREATE TABLE IF NOT EXISTS diet_feedback (
                        user_id INTEGER,
                        plan TEXT,
                        rating INTEGER,
                        feedback TEXT,
                        compliance TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
        c.execute('INSERT INTO diet_feedback (user_id, plan, rating, feedback, compliance) VALUES (?, ?, ?, ?, ?)',
                  (user_id, row[0], rating, feedback, compliance))
        conn.commit()
        st.success("Thanks for your feedback! Future plans will consider your input.")

# --- Past Plans View with Download ---
def view_past_diet_plans(user_id):
    st.subheader("Past Diet Plans")
    c.execute('SELECT plan, created_at FROM diet_plans WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    rows = c.fetchall()
    for idx, (plan, date) in enumerate(rows):
        with st.expander(f"Diet Plan from {date}"):
            st.markdown(plan)
            st.download_button("Download Diet Plan", plan, file_name=f"diet_plan_{idx+1}.txt")
            
# --- WORKOUT PLAN PAGE ---
def show_workout_plan(user_id):
    st.header("Personalised Workout Plan")

    # --- Ask user for customization options ---
    st.subheader("🏋️ Customize Your Workout Preferences")

    time_pref = st.selectbox("When do you prefer to work out?", ["", "Morning", "Afternoon", "Evening", "Night"])

    duration_pref = st.selectbox("Preferred workout duration:", ["", "20 mins", "30 mins", "45 mins", "1 hour", "90 mins", "2 hours"])

    injuries = st.multiselect("Any physical limitations/injuries:",
                               ["Knee pain", "Back issues", "Shoulder injury", "Limited mobility", "None"])

    equipment = st.multiselect("🏋️ What equipment do you have access to?",
    [
        "No Equipment / Bodyweight",
        "Dumbbells",
        "Barbell",
        "Kettlebells",
        "Resistance Bands",
        "Treadmill",
        "Stationary Bike",
        "Rowing Machine",
        "Pull-Up Bar",
        "Jump Rope",
        "Yoga Mat / Blocks",
        "Foam Roller",
        "Bench / Box",
        "Cable Machine",
        "Smith Machine",
        "Leg Press Machine",
        "Medicine Ball / Slam Ball"
    ])

    if not time_pref or not duration_pref or not equipment:
        st.info("Please complete all workout preferences to proceed.")
        return

    regenerate = st.button("Generate / Regenerate Workout Plan")

    if not regenerate:
        c.execute('SELECT plan, created_at FROM workout_plans WHERE user_id=? ORDER BY created_at DESC LIMIT 1', (user_id,))
        existing = c.fetchone()
        if existing:
            created_date = datetime.datetime.strptime(existing[1], "%Y-%m-%d %H:%M:%S.%f")
            if (datetime.datetime.now() - created_date).days < 14:
                st.markdown(existing[0])
                st.download_button("Download Workout Plan", existing[0], file_name=f"workout_plan.txt")
                return

    c.execute('SELECT gender, activity_level, goal, workout_type, gym_focus, bmi FROM profiles WHERE user_id=? ORDER BY rowid DESC LIMIT 1', (user_id,))
    row = c.fetchone()

    if row:
        if not row[-1] or row[-1] < 10:
            st.warning("BMI value is too low or missing. Please update your profile with valid height and weight.")
            return

        gender, activity, goal, workout_type, gym_focus, _ = row
        gym_note = f"The user works out at a gym with a preference for {gym_focus.lower()} training." if workout_type == "Gym" else "The user does bodyweight workouts."

        prompt = f"""
        You are a professional fitness coach. Design a weekly workout plan in a structured format.

        User Details:
        - Gender: {gender}
        - Workout Type: {workout_type}
        - Goal: {goal}
        - Activity Level: {activity}
        - Preferred Workout Time: {time_pref}
        - Preferred Session Duration: {duration_pref}
        - Physical Limitations: {', '.join(injuries) if injuries else 'None'}
        - Equipment Available: {', '.join(equipment)}
        {gym_note}

        Follow this fixed structure strictly:
        Day 1: Muscle Group
        - Warm-up: ...
        - Exercise 1: Name — Sets x Reps
        - Exercise 2: ...
        - Cooldown: ...

        Repeat for Day 2 through Day 7. Clearly separate days. Add rest days as needed. Always end each day with a cooldown suggestion.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.5,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": "You are a professional fitness coach."},
                {"role": "user", "content": prompt}
            ]
        )

        plan = response.choices[0].message.content
        st.markdown(plan)
        st.download_button("Download Workout Plan", plan, file_name=f"workout_plan.txt")
        c.execute('INSERT INTO workout_plans (user_id, plan, created_at) VALUES (?, ?, ?)', (user_id, plan, datetime.datetime.now()))
        conn.commit()
    else:
        st.warning("No profile data found. Please fill out your profile first.")
def view_past_workout_plans(user_id):
    st.subheader("Past Workout Plans")
    c.execute('SELECT plan, created_at FROM workout_plans WHERE user_id=? ORDER BY created_at DESC', (user_id,))
    rows = c.fetchall()
    for idx, (plan, date) in enumerate(rows):
        with st.expander(f"Workout Plan from {date}"):
            st.markdown(plan)
            st.download_button("Download Workout Plan", plan, file_name=f"workout_plan_{idx+1}.txt")
            
# --- IMAGE VALIDATION ---
def validate_image(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        if image.size[0] < 100 or image.size[1] < 100:
            st.error("Image resolution too low. Please upload a higher quality image.")
            return None
        return image.convert("RGB")
    except UnidentifiedImageError:
        st.error("Invalid image file. Please upload a valid image.")
        return None
    
# --- IMAGE FRESHNESS ANALYSIS ---
def analyze_freshness():
    st.header("Check Freshness of Fruits/Vegetables")
    uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        image = validate_image(uploaded_file)
        if image is None:
            return
        st.image(image, caption='Uploaded Image', width=250)
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
        image = validate_image(uploaded_file)
        if image is None:
            return
        st.image(image, caption='Dish Image', width=250)
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
