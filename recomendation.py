import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
import pickle
import random

# === Bagian 1: Persiapan Data ===

# Load dan filter data
data = pd.read_csv('tkpi.csv')
df_cleaned = data.drop([0])  # Menghapus baris header tambahan
df_cleaned = df_cleaned.dropna(subset=['KODE'])  # Menghapus baris dengan KODE yang NaN
df_cleaned = df_cleaned[df_cleaned['KODE'].str.match(r'^[A-Ha-h]')]  # Menyaring berdasarkan KODE
df_cleaned = df_cleaned[~df_cleaned['NAMA BAHAN'].str.contains(r'anak|babi|darah', case=False, na=False)]  # Menghapus bahan tertentu

# Pilih kolom yang relevan
desired_columns = ['KODE', 'NAMA BAHAN', 'SUMBER', 'ENERGI', 'PROTEIN', 'LEMAK', 'KH', 'SERAT']
df_final = df_cleaned[desired_columns]

df_final.loc[:, 'PROTEIN'] = df_final['PROTEIN'].astype(str).str.replace(',', '.').astype(float)
df_final.loc[:, 'LEMAK'] = df_final['LEMAK'].astype(str).str.replace(',', '.').astype(float)
df_final.loc[:, 'KH'] = df_final['KH'].astype(str).str.replace(',', '.').astype(float)
df_final.loc[:, 'SERAT'] = df_final['SERAT'].astype(str).str.replace(',', '.').astype(float)



# Simpan hasil filter
df_final.to_csv('tkpi_filtered.csv', index=False)

# === Bagian 2: Clustering Data ===

# Muat data terfilter
filtered_data = pd.read_csv('tkpi_filtered.csv')
numeric_columns = ['ENERGI', 'PROTEIN', 'LEMAK', 'KH', 'SERAT']
df_numeric = filtered_data[numeric_columns].apply(pd.to_numeric, errors='coerce')
df_numeric = df_numeric.fillna(df_numeric.mean())  # Mengisi NaN dengan nilai rata-rata

# Normalisasi dan clustering
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df_numeric)
kmeans = KMeans(n_clusters=3, random_state=0)
filtered_data['Cluster'] = kmeans.fit_predict(df_scaled)

# Simpan data ber-cluster
filtered_data.to_csv('tkpi_filtered.csv', index=False)

# === Bagian 3: Melatih dan Menyimpan Model ===

# Pisahkan fitur dan target
X = filtered_data[['PROTEIN', 'LEMAK', 'KH', 'SERAT']]
y = filtered_data['ENERGI']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


def train_random_forest(X_train, y_train):
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    return rf_model

rf_model = train_random_forest(X_train, y_train)

# Model Evaluation
def evaluate_model(model, X_test, y_test):
    y_pred = rf_model.predict(X_test)

    # Menghitung MSE, RMSE, MAE, dan R²
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Menampilkan hasil
    #print(f"Mean Squared Error (MSE): {mse}")
    #print(f"Root Mean Squared Error (RMSE): {rmse}")
    #print(f"Mean Absolute Error (MAE): {mae}")
    #print(f"R-squared (R²): {r2}")

    return mse

evaluate_model(rf_model, X_test, y_test)



# Simpan model ke file .pkl menggunakan pickle
with open(r'C:\Users\USER\dietrecomendation\rf_model.pkl', 'rb') as model_file:
    rf_model = pickle.load(model_file)
    print("Model berhasil dimuat")


# === Bagian 4: Fungsi Rekomendasi Makanan ===

def calculate_bmr(gender, age, weight, height, activity):
    if gender == 'pria':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    
    # Adjust BMR berdasarkan aktivitas
    activity_multiplier = {
        'sedentary': 1.3,
        'lowactive': 1.5,
        'active': 1.7,
        'veryactive': 2
    }
    return bmr * activity_multiplier.get(activity, 1.2)

def adjust_bmr_for_goal(bmr, goal):
    if goal == 'lose':
        return bmr * 0.8
    elif goal == 'gain':
        return bmr * 1.2
    else:
        return bmr

def recommend_foods_by_meal(calorie_target, data, model, category_prefix, max_items=5):
    selected_foods = pd.DataFrame()
    total_calories = 0

    # Filter makanan sesuai kategori
    category_foods = data[data['KODE'].str.startswith(tuple(category_prefix))]

    # Sample sejumlah makanan sekaligus
    sampled_foods = category_foods.sample(n=min(max_items, len(category_foods)))

    for _, sample_food in sampled_foods.iterrows():
        X_sample = sample_food[['PROTEIN', 'LEMAK', 'KH', 'SERAT']]
        predicted_calories = model.predict([X_sample])[0]
        total_calories += predicted_calories

        print(f"Predicted calories: {predicted_calories}, Total calories so far: {total_calories}")

        if total_calories <= calorie_target:
            selected_foods = pd.concat([selected_foods, sample_food])

    print(f"Finished selection, Total calories: {total_calories}")
    return selected_foods

def find_foods_by_category(target_calories, data, category_prefix, max_items=5):
    total_calories = 0
    selected_foods = pd.DataFrame()

    # Filter data berdasar kategori
    category_data = data[data['KODE'].str.startswith(tuple(category_prefix))]

    if category_data.empty:
        print(f"No data available for categories {category_prefix}")
        return selected_foods  # Return an empty DataFrame if no data is available

    # looping untuk mencari kombinasi makanan agar mencapai terget kalori
    while total_calories < target_calories and len(selected_foods) < max_items:
        # Randomly sample foods from the dataset in the specific category
        possible_food = category_data.sample(n=1, replace=False)
        selected_foods = pd.concat([selected_foods, possible_food])
        total_calories = selected_foods['ENERGI'].sum()

        # Stop when we exceed the target calories
        if total_calories >= target_calories:
            break

    return selected_foods

def find_single_food_by_category(data):
    if not data.empty:
        return data.sample(n=1)  # Randomly select one item
    return pd.DataFrame()  # Return empty if no item matches

def recommend_balanced_meals(bmr, data, model, protein_threshold=15, carb_threshold=20, fat_threshold=20, fiber_threshold=20):
    # Define calorie allocations for each meal
    breakfast_calories = bmr * 0.25
    lunch_calories = bmr * 0.35
    dinner_calories = bmr * 0.3
    snack_calories = bmr * 0.1  

    # Define category-specific calorie proportions for each meal
    category_ratios = {
        "protein": 0.3,
        "nabati": 0.2,
        "sayur": 0.3,
        "karbo": 0.2
    }

    # Pre-filter data for each category to avoid repeated filtering in loops
    high_protein_low_carb = data[
        (data['PROTEIN'] >= protein_threshold) & 
        (data['KH'] <= carb_threshold) & 
        (data['LEMAK'] <= fat_threshold) & 
        (data['SERAT'] <= fiber_threshold)
    ]
    karbo_data = data[data['KODE'].str.startswith(('A', 'B'))]
    sayur_data = data[data['KODE'].str.startswith('D')]
    nabati_data = high_protein_low_carb[high_protein_low_carb['KODE'].str.startswith('C')]
    protein_data = high_protein_low_carb[high_protein_low_carb['KODE'].str.startswith(('F', 'G', 'H'))]

    def select_foods_for_meal(total_calories, protein_data, nabati_data, sayur_data, karbo_data):
        selected_foods = []

        # Allocate calories to each category based on ratios
        calories_per_category = {
            "protein": total_calories * category_ratios["protein"],
            "nabati": total_calories * category_ratios["nabati"],
            "sayur": total_calories * category_ratios["sayur"],
            "karbo": total_calories * category_ratios["karbo"]
        }

        # Ensure each category has at least one item
        selected_foods.append(find_single_food_by_category(protein_data))
        selected_foods.append(find_single_food_by_category(nabati_data))
        selected_foods.append(find_single_food_by_category(sayur_data))
        selected_foods.append(find_single_food_by_category(karbo_data))

        # Combine initial items to meal
        meal_foods = pd.concat(selected_foods)
        current_calories = meal_foods['ENERGI'].sum()

        # Add items to meet the total calorie target
        while current_calories < total_calories:
            if current_calories < calories_per_category["sayur"]:
                additional_sayur = find_single_food_by_category(sayur_data)
                selected_foods.append(additional_sayur)
            elif current_calories < calories_per_category["nabati"]:
                additional_nabati = find_single_food_by_category(nabati_data)
                selected_foods.append(additional_nabati)

            meal_foods = pd.concat(selected_foods)
            current_calories = meal_foods['ENERGI'].sum()
            if current_calories >= total_calories:
                break  # Stop if we meet or exceed the desired calorie goal
        
        return meal_foods

    # Generate meals
    breakfast_foods = select_foods_for_meal(breakfast_calories, protein_data, nabati_data, sayur_data, karbo_data)
    lunch_foods = select_foods_for_meal(lunch_calories, protein_data, nabati_data, sayur_data, karbo_data)
    dinner_foods = select_foods_for_meal(dinner_calories, protein_data, nabati_data, sayur_data, karbo_data)
    
    # Snacks - Limit to max 2 fruits and ensure calorie alignment
    snack_foods = []
    current_snack_calories = 0
    fruit_data = data[data['KODE'].str.startswith('ER')]
    while current_snack_calories < snack_calories and len(snack_foods) < 2:
        fruit_snack = find_single_food_by_category(fruit_data)
        snack_foods.append(fruit_snack)
        current_snack_calories += fruit_snack['ENERGI'].sum()
    snack_foods = pd.concat(snack_foods)

    # Calculate total energy and check if it's within ±100 of BMR
    total_calories = (breakfast_foods['ENERGI'].sum() +
                      lunch_foods['ENERGI'].sum() +
                      dinner_foods['ENERGI'].sum() +
                      snack_foods['ENERGI'].sum())

    # Adjust meals if total calories are not within ±100 of BMR
    calorie_gap = bmr - total_calories
    while abs(calorie_gap) > 100:
        if calorie_gap > 0:
            additional_item = find_single_food_by_category(sayur_data) or find_single_food_by_category(nabati_data)
            if not additional_item.empty:
                breakfast_foods = pd.concat([breakfast_foods, additional_item])
                total_calories += additional_item['ENERGI'].sum()
        else:
            if not breakfast_foods[breakfast_foods['KODE'].str.startswith(('D', 'C'))].empty:
                item_to_remove = breakfast_foods[breakfast_foods['KODE'].str.startswith(('D', 'C'))].sample(n=1)
                breakfast_foods = breakfast_foods.drop(item_to_remove.index)
                total_calories -= item_to_remove['ENERGI'].sum()
        
        calorie_gap = bmr - total_calories

    print(f"Total Calories from Meals: {total_calories:.2f} vs Adjusted BMR: {bmr:.2f}")

    return breakfast_foods, lunch_foods, dinner_foods, snack_foods

# === Bagian 5: Menghitung BMR dan Menampilkan Rekomendasi Makanan ===

# Load model
with open(r'C:\Users\USER\dietrecomendation\rf_model.pkl', 'rb') as model_file:
    rf_model = pickle.load(model_file)



