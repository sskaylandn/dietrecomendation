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
import joblib

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
rf_model = joblib.load('C:\\Users\\USER\\dietrecomendation\\rf_model.joblib')


# === Bagian 4: Fungsi Rekomendasi Makanan ===
def calculate_bmr(gender, age, weight, height):
    if gender == 'male':
        bmr = 88.362 + (13.397 * weight) + (4.799 * height) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight) + (3.098 * height) - (4.330 * age)
    return bmr

# Calculate TDEE using BMR and activity level
def calculate_tdee(bmr, activity_level):
    activity_multiplier = {
        'sedentary': 1.3,
        'lowactive': 1.5,
        'active': 1.7,
        'veryactive': 2.0
    }
    return bmr * activity_multiplier.get(activity_level, 1.2)

# Adjust calorie intake based on goal and TDEE/BMR relationship
def adjust_calories_for_goal(tdee, bmr, goal):
    if goal == 'lose':
        return max(bmr, tdee * 0.8)  # No lower than BMR, 20% below TDEE for weight loss
    elif goal == 'gain':
        return tdee * 1.2  # 20% above TDEE for weight gain
    else:
        return tdee  # Maintain weight

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

def find_single_food_by_category(data, category_prefix, num_samples=5):
    category_data = data[data['KODE'].str.startswith(tuple(category_prefix))]
    if not category_data.empty:
        return category_data.sample(n=min(num_samples, len(category_data)))  # Pre-sample items
    return pd.DataFrame()


def recommend_balanced_meals(tdee, bmr, goal, data):
    adjusted_calories = adjust_calories_for_goal(tdee, bmr, goal)

    # Define meal calorie allocation
    breakfast_calories = adjusted_calories * 0.25
    lunch_calories = adjusted_calories * 0.35
    dinner_calories = adjusted_calories * 0.3
    snack_calories = adjusted_calories * 0.1

    # Filter food categories
    karbo_data = data[data['KODE'].str.startswith(('A', 'B'))]
    sayur_data = data[data['KODE'].str.startswith('D')]
    nabati_data = data[data['KODE'].str.startswith('C')]
    protein_data = data[data['KODE'].str.startswith(('F', 'G', 'H'))]
    fruit_data = data[data['KODE'].str.startswith('ER')]

    def select_foods_for_meal(target_calories, protein_data, nabati_data, sayur_data, karbo_data):
        meal_foods = pd.DataFrame()
        current_calories = 0

        # Ensure one of each required item type
        items = {
            "protein": find_single_food_by_category(protein_data, ['F', 'G', 'H'], num_samples=1),
            "nabati": find_single_food_by_category(nabati_data, ['C'], num_samples=1),
            "sayur": find_single_food_by_category(sayur_data, ['D'], num_samples=1),
            "karbo": find_single_food_by_category(karbo_data, ['A', 'B'], num_samples=1)
        }
        
        # Combine and calculate initial calories
        for category, item_df in items.items():
            meal_foods = pd.concat([meal_foods, item_df], ignore_index=True)
        current_calories = meal_foods['ENERGI'].sum()

        # Add `sayur` items to reach closer to target calories if possible
        while current_calories < target_calories - 50:
            if len(meal_foods[meal_foods['KODE'].str.startswith('D')]) < 2:
                extra_sayur = find_single_food_by_category(sayur_data, ['D'], num_samples=1)
                if not extra_sayur.empty and current_calories + extra_sayur['ENERGI'].sum() <= target_calories:
                    meal_foods = pd.concat([meal_foods, extra_sayur], ignore_index=True)
                    current_calories += extra_sayur['ENERGI'].sum()
            else:
                break  # Stop if reaching the maximum of sayur items

        return meal_foods

    # Generate meals
    breakfast_foods = select_foods_for_meal(breakfast_calories, protein_data, nabati_data, sayur_data, karbo_data)
    lunch_foods = select_foods_for_meal(lunch_calories, protein_data, nabati_data, sayur_data, karbo_data)
    dinner_foods = select_foods_for_meal(dinner_calories, protein_data, nabati_data, sayur_data, karbo_data)
    snack_foods = find_single_food_by_category(fruit_data, ['ER'], num_samples=2)

    # Calculate total calories and make adjustments
    total_calories = (
        breakfast_foods['ENERGI'].sum() +
        lunch_foods['ENERGI'].sum() +
        dinner_foods['ENERGI'].sum() +
        snack_foods['ENERGI'].sum()
    )

    # Ensure total calories are aligned with the adjusted goal within ±100 kcal
    calorie_gap = adjusted_calories - total_calories
    if abs(calorie_gap) > 100:
        if calorie_gap > 0:
            # Try adding a low-calorie sayur item to breakfast to bridge the gap
            extra_sayur = find_single_food_by_category(sayur_data, ['D'], num_samples=1)
            if not extra_sayur.empty and total_calories + extra_sayur['ENERGI'].sum() <= adjusted_calories + 100:
                breakfast_foods = pd.concat([breakfast_foods, extra_sayur], ignore_index=True)
                total_calories += extra_sayur['ENERGI'].sum()
        elif calorie_gap < 0:
            # Remove a karbo item from breakfast if calories are high
            breakfast_foods = breakfast_foods[~breakfast_foods['KODE'].str.startswith(('A', 'B'))]
            total_calories = (
                breakfast_foods['ENERGI'].sum() +
                lunch_foods['ENERGI'].sum() +
                dinner_foods['ENERGI'].sum() +
                snack_foods['ENERGI'].sum()
            )

    print(f"Total Calories from Meals: {total_calories:.2f} vs Adjusted Calories: {adjusted_calories:.2f}")
    
    return breakfast_foods, lunch_foods, dinner_foods, snack_foods


# === Bagian 5: Menghitung BMR dan Menampilkan Rekomendasi Makanan ===

# Load model
rf_model = joblib.load('C:\\Users\\USER\\dietrecomendation\\rf_model.joblib')



