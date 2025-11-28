from flask import Flask, render_template, request, jsonify
import json
import os
from werkzeug.utils import secure_filename
import random
from typing import Dict, List, Any
from src.meal_optimizer import MealOptimizer

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Load meal data from JSON file
def load_meal_data():
    try:
        with open('data/meals.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

SAMPLE_MEALS = load_meal_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ratings')
def ratings():
    return render_template('ratings.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.endswith('.json'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            with open(filepath, 'r') as f:
                meals_data = json.load(f)
            return jsonify({'message': 'File uploaded successfully', 'meals_count': len(meals_data)})
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON file'}), 400
    
    return jsonify({'error': 'Please upload a JSON file'}), 400

@app.route('/generate_meal_plan', methods=['POST'])
def generate_meal_plan():
    try:
        data = request.get_json()
        requirements = data.get('requirements', {})
        objective = data.get('objective', 'minimize_cost')  # Default to minimize cost
        meal_frequency = data.get('mealFrequency', 2)  # Default to 2 times per week
        
        # Initialize the meal optimizer
        optimizer = MealOptimizer()
        
        # Convert frontend requirements to optimization format
        optimization_result = run_optimization(optimizer, requirements, objective, meal_frequency)
        
        if optimization_result['status'] not in ['OPTIMAL', 'FEASIBLE']:
            return jsonify({
                'success': False,
                'error': f"Optimization failed: {optimization_result.get('message', 'No feasible solution found')}"
            }), 400
        
        # Convert optimization result to meal plan format
        meal_plan = convert_optimization_to_meal_plan(optimization_result)
        
        return jsonify({
            'success': True,
            'meal_plan': meal_plan,
            'optimization_results': {
                'status': optimization_result['status'],
                'total_cost': optimization_result['total_cost'],
                'num_meals': optimization_result['num_meals_selected'],
                'nutritional_summary': optimization_result['nutritional_summary']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_optimization(optimizer: MealOptimizer, requirements: Dict, objective: str = "minimize_cost", meal_frequency: int = 2) -> Dict:
    """
    Run optimization with custom nutritional requirements from frontend.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log received requirements for debugging
    logger.info(f"Received requirements: {requirements}")
    
    # Create a custom nutritional profile from frontend requirements
    custom_profile = {
        "calories": {
            "min": requirements.get('minCalories', 300),
            "max": requirements.get('maxCalories', 700)
        },
        "protein": {
            "min": requirements.get('minProtein', 20),
            "max": requirements.get('maxProtein', 35)
        },
        "carbs": {
            "min": requirements.get('minCarbs', 30),
            "max": requirements.get('maxCarbs', 90)
        },
        "fat": {
            "min": requirements.get('minFat', 10),
            "max": requirements.get('maxFat', 25)
        },
        "vitaminA": {
            "min": requirements.get('minVitaminA', 150),
            "max": requirements.get('maxVitaminA', 300)
        },
        "vitaminC": {
            "min": requirements.get('minVitaminC', 15),
            "max": requirements.get('maxVitaminC', 30)
        },
        "vitaminD": {
            "min": requirements.get('minVitaminD', 3),
            "max": requirements.get('maxVitaminD', 8)
        },
        "vitaminE": {
            "min": requirements.get('minVitaminE', 3),
            "max": requirements.get('maxVitaminE', 6)
        },
        "calcium": {
            "min": requirements.get('minCalcium', 200),
            "max": requirements.get('maxCalcium', 400)
        },
        "iron": {
            "min": requirements.get('minIron', 2),
            "max": requirements.get('maxIron', 4)
        },
        "magnesium": {
            "min": requirements.get('minMagnesium', 60),
            "max": requirements.get('maxMagnesium', 120)
        },
        "potassium": {
            "min": requirements.get('minPotassium', 600),
            "max": requirements.get('maxPotassium', 1000)
        },
        "sodium": {
            "min": requirements.get('minSodium', 200),
            "max": requirements.get('maxSodium', 400)
        }
    }
    
    # Log the custom profile being used
    logger.info(f"Custom profile created: {custom_profile}")
    
    # Temporarily add custom profile to optimizer
    optimizer.nutritional_profiles['custom'] = custom_profile
    
    # Run optimization with custom profile
    result = optimizer.solve(profile_name='custom', max_meals_per_meal=meal_frequency, objective=objective)
    
    # Remove custom profile
    del optimizer.nutritional_profiles['custom']
    
    return result

def convert_optimization_to_meal_plan(optimization_result: Dict) -> Dict:
    """
    Convert optimization result to the meal plan format expected by frontend.
    """
    meal_plan = {}
    
    # Initialize all days
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days:
        meal_plan[day] = []
    
    # Populate with selected meals
    for meal_info in optimization_result['selected_meals']:
        day = meal_info['day']
        meal = meal_info['meal']
        meal_plan[day].append(meal)
    
    return meal_plan

def generate_weekly_meal_plan(meals: List[Dict], requirements: Dict) -> Dict:
    """
    Simplified meal plan generation for dinners only, one week
    """
    # Create one week of days
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    meal_plan = {}
    
    for day in days:
        # Filter meals based on nutritional requirements
        suitable_meals = filter_meals_by_requirements(meals, requirements, {}, 'dinner')
        
        if suitable_meals:
            # Select 1-2 meals for dinner
            num_meals = min(2, len(suitable_meals))
            selected_meals = random.sample(suitable_meals, num_meals)
        else:
            # Fallback to random selection if no suitable meals found
            selected_meals = random.sample(meals, min(2, len(meals)))
        
        meal_plan[day] = selected_meals
    
    return meal_plan

def filter_meals_by_requirements(meals: List[Dict], requirements: Dict, current_nutrition: Dict, meal_type: str) -> List[Dict]:
    """
    Filter meals based on nutritional requirements
    """
    suitable_meals = []
    
    for meal in meals:
        # Check if adding this meal would exceed maximum limits
        would_exceed = False
        
        # Check calories
        if current_nutrition['calories'] + meal.get('calories', 0) > requirements.get('maxCalories', 9999):
            would_exceed = True
        
        # Check macros
        if 'macros' in meal:
            if current_nutrition['protein'] + meal['macros'].get('protein', 0) > requirements.get('maxProtein', 9999):
                would_exceed = True
            if current_nutrition['carbs'] + meal['macros'].get('carbs', 0) > requirements.get('maxCarbs', 9999):
                would_exceed = True
            if current_nutrition['fat'] + meal['macros'].get('fat', 0) > requirements.get('maxFat', 9999):
                would_exceed = True
        
        # Check micros
        if 'micros' in meal:
            if current_nutrition['sodium_mg'] + meal['micros'].get('sodium_mg', 0) > requirements.get('maxSodium', 9999):
                would_exceed = True
        
        if not would_exceed:
            suitable_meals.append(meal)
    
    return suitable_meals

@app.route('/get_sample_meals')
def get_sample_meals():
    return jsonify(SAMPLE_MEALS)

@app.route('/get_all_meals')
def get_all_meals():
    """Load and return all meals from meals.json"""
    try:
        meals = load_meal_data()
        return jsonify({
            'success': True,
            'meals': meals
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_sample_meal_plan')
def get_sample_meal_plan():
    """Load and return the sample weekly plan for visualization"""
    try:
        with open('sample_weekly_plan.json', 'r') as f:
            sample_plan = json.load(f)
        return jsonify({
            'success': True,
            'meal_plan': sample_plan
        })
    except FileNotFoundError:
        return jsonify({'error': 'Sample weekly plan file not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in sample weekly plan file'}), 400

@app.route('/get_nutritional_profiles')
def get_nutritional_profiles():
    """Load and return nutritional profiles"""
    try:
        with open('data/nutritional_profiles.json', 'r') as f:
            profiles = json.load(f)
        response = jsonify({
            'success': True,
            'profiles': profiles
        })
        # Add cache-busting headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except FileNotFoundError:
        return jsonify({'error': 'Nutritional profiles file not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in nutritional profiles file'}), 400

@app.route('/get_config')
def get_config():
    """Load and return application configuration"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return jsonify({
            'success': True,
            'config': config
        })
    except FileNotFoundError:
        return jsonify({'error': 'Config file not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in config file'}), 400

@app.route('/update_rating', methods=['POST'])
def update_rating():
    """Update user rating for a specific meal"""
    try:
        data = request.get_json()
        meal_title = data.get('meal_title')
        rating = data.get('rating')
        
        if not meal_title or rating is None:
            return jsonify({'error': 'Missing meal_title or rating'}), 400
        
        if not (1 <= rating <= 10):
            return jsonify({'error': 'Rating must be between 1 and 10'}), 400
        
        # Load meals data
        meals = load_meal_data()
        
        # Find and update the meal
        meal_found = False
        for meal in meals:
            if meal['title'] == meal_title:
                meal['user_rating'] = rating
                meal_found = True
                break
        
        if not meal_found:
            return jsonify({'error': 'Meal not found'}), 404
        
        # Save updated meals back to file
        with open('data/meals.json', 'w') as f:
            json.dump(meals, f, indent=2)
        
        return jsonify({'success': True, 'message': f'Rating updated to {rating}'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_meals_with_ratings')
def get_meals_with_ratings():
    """Get all meals with their ratings (default 5 if not set)"""
    try:
        meals = load_meal_data()
        
        # Add default rating of 5 if not present
        for meal in meals:
            if 'user_rating' not in meal:
                meal['user_rating'] = 5
        
        return jsonify({
            'success': True,
            'meals': meals
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset_ratings', methods=['POST'])
def reset_ratings():
    """Reset all meal ratings back to 5"""
    try:
        # Load meals data
        meals = load_meal_data()
        
        # Reset all ratings to 5
        for meal in meals:
            meal['user_rating'] = 5
        
        # Save updated meals back to file
        with open('data/meals.json', 'w') as f:
            json.dump(meals, f, indent=2)
        
        return jsonify({'success': True, 'message': 'All ratings reset to 5'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
